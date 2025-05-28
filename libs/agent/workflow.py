import asyncio
from datetime import timedelta
from typing import Dict, List

from temporalio import activity, workflow

from .tool import create_enhanced_tool

with workflow.unsafe.imports_passed_through():
    from asyncio import Future
    from vertexai.generative_models import (
        Content,
        GenerationConfig,
        GenerativeModel,
        GenerationResponse,
        Part,
        Candidate
    )

class LLM:
    def __init__(self, model: GenerativeModel, functions: List[callable]) -> None:
        self.model = model
        # convert functions to vertexai tools
        self.tools = create_enhanced_tool(functions)

    @activity.defn
    def call_llm(self, contents: List[Dict]) -> Dict:
        """Activity to call the LLM with the given contents.

        Args:
            contents: List of content dictionaries to send to the LLM

        Returns:
            Dictionary with LLM response
        """

        # Convert dict to Content objects
        vertex_contents = [Content.from_dict(c) for c in contents]

        activity.logger.debug(f'Generates content with toos: {self.tools}')

        # Generate response
        return self.model.generate_content(
            contents=vertex_contents,
            generation_config=GenerationConfig(temperature=0),
            tools=[self.tools],
        ).to_dict()


@workflow.defn
class AgentWorkflow:
    """Workflow that manages the conversation with the LLM."""

    def __init__(self) -> None:
        self.contents: List[Content] = []
        self.respond: Future = None
        self.terminate: bool = False

    @workflow.run
    async def run(self, prompt: str) -> str:
        """Run the workflow with the given prompt.

        Args:
            prompt: The user's prompt

        Returns:
            The LLM's final response
        """

        if prompt == "":
            await self.wait_for_prompt()
        else:
            user_prompt_content = Content(
                role="user",
                parts=[Part.from_text(prompt)],
            )
            self.contents.append(user_prompt_content)

        while not self.terminate:
            dict_content = [c.to_dict() for c in self.contents]
            raw_rsp = await workflow.execute_activity(
                LLM.call_llm,
                dict_content,
                start_to_close_timeout=timedelta(seconds=60),
            )

            candidate = GenerationResponse.from_dict(raw_rsp).candidates[0]

            if candidate.function_calls:
                self.contents.append(candidate.content)
                await self.handle_function_calls(candidate)
            elif candidate.finish_reason == 1:
                # respond message by resolving the future
                if self.respond:
                    self.respond.set_result(candidate.content.text)

                await self.wait_for_prompt()

        if self.respond:
            self.respond.set_result("")

    async def wait_for_prompt(self):
        count = len(self.contents)
        await workflow.wait_condition(lambda: len(self.contents) != count)

    async def handle_function_calls(self, candidate: Candidate) -> None:
        """Handle function calls from the LLM."""
        parts: List[Part] = []
        for func in candidate.function_calls:
            arg = func.args
            func_rsp = await workflow.execute_activity(
                func.name,
                next(iter(func.args.values()), dict()), # only use the first dataclass typed arg
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
        self.respond = asyncio.Future()
        await workflow.wait([self.respond])
        return await self.respond

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