import asyncio
import json
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
        Candidate
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
    """Workflow that manages the conversation with the LLM."""

    def __init__(self) -> None:
        self.contents: List[Content] = []
        self.pending_respond: Future = None
        self.terminate: bool = False
        self.agent_name: str
        self.sub_agents: Dict[any] = None
        self.is_root_agent: bool = False

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
        self.contents_start = len(self.contents)
        self.sub_agents = agent_input.sub_agents[self.agent_name]
        self.is_root_agent = agent_input.is_root_agent
        
        prompt = agent_input.prompt
        if prompt == "":
            await self._wait_for_prompt()
        else:
            user_prompt_content = Content(
                role="user",
                parts=[Part.from_text(prompt)],
            )
            self.contents.append(user_prompt_content)
        while not self.terminate:
            candidate = await self._call_llm()
            if candidate.function_calls:
                await self._handle_function_calls(candidate)
            elif candidate.finish_reason == 1:
                if self.is_root_agent:
                    # root agent respond message by resolving the future
                    if self.pending_respond:
                        self.pending_respond.set_result(candidate.content.text)
                    await self._wait_for_prompt()
                else:
                    # sub-agent respond the new contents collected in the sub-agent
                    return [c.to_dict() for c in self.contents[self.contents_start:]]


        if self.pending_respond:
            self.pending_respond.set_result("")

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
        self.contents.append(candidate.content)

        parts: List[Part] = []
        for func in candidate.function_calls:
            workflow.logger.debug(f"Handling function call: {func}")
            func_name = func.name
            if func_name in self.sub_agents.keys():
                prompt = json.dumps(func.args) # not sure if this is the right way to do it
                sub_agent_input = AgentWorkflowInput(
                    agent_name=func_name,
                    sub_agents=self.sub_agents[func_name],
                    prompt=prompt,
                    contents=[c.to_dict() for c in self.contents]
                )
                func_rsp = await workflow.execute_child_workflow(
                    AgentWorkflow.run,
                    sub_agent_input,
                    id=f"{workflow.info().workflow_id}-{self.agent_name}-workflow",
                    task_queue="agent-task-queue",
                )
                response_part = Part.from_function_response(
                    name=func.name,
                    response={"content": func_rsp},
                )
                parts.append(response_part)
            else:
                func_args = next(iter(func.args.values()), dict()), # only use the first dataclass typed arg,
                workflow.logger.debug(f"Calling function: {func_name} with args: {func_args}")
                func_rsp = await workflow.execute_activity(
                    func_name,
                    args=func_args,
                    start_to_close_timeout=timedelta(seconds=60),
                )
                response_part = Part.from_function_response(
                    name=func.name,
                    response={"content": func_rsp},
                )
                parts.append(response_part)
        self.contents.append(Content(role="user", parts=parts))

    @workflow.update
    async def prompt(self, prompt: str) -> str:
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
    def get_model_content(self, watermark: int) -> List[str]:
        """Query to get only the text content from model responses.
        
        Args:
            watermark: Index to get content from
        
        Returns:
            List of text strings from model responses after watermark index
        """
        model_texts = []
        for content in self.contents:
            if content.role == "model":
                for part in content.parts:
                    try:
                        if part.text:
                            model_texts.append(part.text)
                    except AttributeError:
                        pass # noop if part is not a text part
        workflow.logger.info(f'get_model_content from watermark {watermark}: {model_texts}')               
        return model_texts[watermark:]