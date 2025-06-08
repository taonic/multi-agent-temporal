import asyncio
import json
import secrets
from datetime import timedelta
from typing import List, Dict
from dataclasses import dataclass, field
from temporalio import workflow

from temporal.agent.llm_manager import LLMCallInput

with workflow.unsafe.imports_passed_through():
    from asyncio import Future
    from vertexai.generative_models import (
        Content,
        GenerationResponse,
        Part,
        Candidate,
        FunctionCall,
        FinishReason
    )
    
@dataclass
class AgentWorkflowInput:
    """Input for the agent workflow."""
    agent_name: str
    sub_agents: Dict = None
    prompt: str = ""
    contents: List[Dict] = field(default_factory=list)
    is_root_agent: bool = False

@workflow.defn
class AgentWorkflow:
    """
    Workflow that manages the conversation with the LLM.
    It handles the user's prompt and response (Update), LLM calls (Activity), and function calls (Activity).
    It also manages sub-agents and propagate model contents (Signal).
    """

    def __init__(self) -> None:
        self.agent_name: str
        self.is_root_agent: bool = False
        self.sub_agents: Dict[any] = None
        self.contents: List[Content] = []
        self.contents_starts_at: int = 0
        self.pending_respond: Future = None
        self.terminate: bool = False
        self.model_contents: Dict[str, List[str]] = {} # Stores agent and sub-agent's model contents

    @workflow.run
    async def run(self, agent_input: AgentWorkflowInput) -> List[Dict]:
        """Run the workflow with the given prompt.

        Args:
            prompt: The user's prompt

        Returns:
            The LLM's final response
        """
        
        self.agent_name = agent_input.agent_name
        self.contents = [Content.from_dict(c) for c in agent_input.contents]
        self.contents_starts_at = len(self.contents)
        self.model_contents[self.agent_name] = []
        self.sub_agents = agent_input.sub_agents
        self.is_root_agent = agent_input.is_root_agent
        
        # handle prompt
        prompt = agent_input.prompt
        if prompt == "":
            await self._wait_for_prompt()
        else:
            user_prompt_content = Content(
                role="user",
                parts=[Part.from_text(prompt)],
            )
            self.contents.append(user_prompt_content)

        # main loop to handle LLM responses
        while not self.terminate:
            candidate = await self._call_llm()
            if candidate.finish_reason == FinishReason.MALFORMED_FUNCTION_CALL:
                # handle malformed function call with a user prompt
                user_prompt_content = Content(
                    role="user",
                    parts=[Part.from_text(candidate.finish_message)],
                )
                self.contents.append(user_prompt_content)
                continue
                
            await self._store_content(candidate.content)
            if candidate.function_calls:
                await self._handle_function_calls(candidate)
            elif candidate.finish_reason == FinishReason.STOP:
                if self.is_root_agent:
                    # root agent respond the final response then wait for the next prompt
                    if self.pending_respond:
                        self.pending_respond.set_result(candidate.content.text)
                        await self._wait_for_prompt()
                else:
                    # sub-agent respond the new contents collected in the sub-agent
                    return [c.to_dict() for c in self.contents[self.contents_starts_at:]]

        if self.pending_respond:
            self.pending_respond.set_result("")
            
    async def _store_content(self, content: Content) -> None:
        """Store and propagate the content from the LLM."""
        self.contents.append(content)
        # store model contents separately for querying
        if content.role == "model":
            for part in content.parts:
                try:
                    if part.text:
                        self.model_contents[self.agent_name].append(part.text)
                        # propagate model content to the parent workflow
                        await self._propagate_model_content(part.text)
                except AttributeError:
                    pass # noop if part is not a text part
    
    async def _propagate_model_content(self, message) -> None:
        """ Propagate model contents to the parent workflow."""
        if self.is_root_agent:
            return
        parent_info = workflow.info().parent
        if parent_info:
            handle = workflow.get_external_workflow_handle(parent_info.workflow_id)
            await handle.signal(AgentWorkflow.add_model_content, message)
    
    async def _call_llm(self) -> Candidate:
        dict_content = [c.to_dict() for c in self.contents]
        llm_input = LLMCallInput(
            agent_name=self.agent_name,
            contents=dict_content,
        )
        raw_rsp = await workflow.execute_activity(
            "call_llm",
            llm_input,
            start_to_close_timeout=timedelta(seconds=60),
        )
        return GenerationResponse.from_dict(raw_rsp).candidates[0]

    async def _wait_for_prompt(self):
        count = len(self.contents)
        await workflow.wait_condition(lambda: len(self.contents) != count)

    async def _handle_function_calls(self, candidate: Candidate) -> None:
        """Handle function calls from the LLM."""
        parts: List[Part] = []
        for func in candidate.function_calls:
            workflow.logger.debug(f"Handling function call: {func}")
            response_part: Part
            
            if func.name in self.sub_agents.keys():
                response_part = await self._invoke_as_child_workflow(func)
            else:
                response_part = await self._invoke_as_activity(func)
            parts.append(response_part)

        self.contents.append(Content(role="user", parts=parts))
        
    async def _invoke_as_child_workflow(self, func: FunctionCall) -> None:
        prompt = json.dumps(func.args) # not sure if this is the right way to do it
        sub_agent_input = AgentWorkflowInput(
            agent_name=func.name,
            sub_agents=self.sub_agents[func.name],
            prompt=prompt,
            contents=[c.to_dict() for c in self.contents]
        )
        child_id = f"{workflow.info().workflow_id}/{func.name}-{secrets.token_hex(3)}"
        func_rsp = await workflow.execute_child_workflow(
            AgentWorkflow.run,
            sub_agent_input,
            id=child_id,
            task_queue="agent-task-queue",
        )
        
        return Part.from_function_response(
            name=func.name,
            response={"content": func_rsp},
        )
        
    async def _invoke_as_activity(self, func: FunctionCall) -> None:
        func_args = next(iter(func.args.values()), dict()), # only use the first dataclass typed arg,
        workflow.logger.debug(f"Calling function: {func.name} with args: {func_args}")
        func_rsp = await workflow.execute_activity(
            func.name,
            args=func_args,
            start_to_close_timeout=timedelta(seconds=60),
        )
        return Part.from_function_response(
            name=func.name,
            response={"content": func_rsp},
        )

    @workflow.update
    async def prompt(self, prompt: str) -> str:
        """Update the workflow with a new prompt."""
        workflow.logger.debug(f'prompt received: {prompt}')
        if prompt == "END":
            self.terminate = True

        new_content = Content(
            role="user",
            parts=[Part.from_text(prompt)],
        )
        self.contents.append(new_content)

        # wait for respond to be resolved
        self.pending_respond = asyncio.Future()
        await workflow.wait([self.pending_respond])
        return await self.pending_respond

    @workflow.query
    async def get_model_content(self, watermark: int) -> List[str]:
        """Get the model's content."""
        return self.model_contents[self.agent_name][watermark:]
    
    @workflow.signal
    async def add_model_content(self, message: str) -> None:
        """Signal to update the model's content."""
        self.model_contents[self.agent_name].append(message)