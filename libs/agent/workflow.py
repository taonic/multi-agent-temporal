import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Dict, List, Optional, Any

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

import importlib
import inspect

with workflow.unsafe.imports_passed_through():
    import vertexai
    from vertexai.generative_models import (
        Content,
        FunctionDeclaration,
        GenerationConfig,
        GenerativeModel,
        GenerationResponse,
        Part,
        Tool,
    )

class LLM:
    def __init__(self, model: GenerativeModel, functions: List[callable]) -> None:
        self.model = model
        self.tools = Tool(function_declarations=list(map(FunctionDeclaration.from_func, functions)))

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

    @workflow.run
    async def run(self, prompt: str) -> str:
        """Run the workflow with the given prompt.

        Args:
            prompt: The user's prompt

        Returns:
            The LLM's final response
        """

        user_prompt_content = Content(
            role="user",
            parts=[Part.from_text(prompt)],
        )
        self.contents.append(user_prompt_content)

        while True:
            dict_content = [c.to_dict() for c in self.contents]
            raw_rsp = await workflow.execute_activity(
                LLM.call_llm,
                dict_content,
                start_to_close_timeout=timedelta(seconds=10),
            )

            candidate = GenerationResponse.from_dict(raw_rsp).candidates[0]

            if candidate.function_calls:
                self.contents.append(candidate.content)
                await self.handle_function_calls(candidate)
            elif candidate.finish_reason == 1:
                return candidate.content.text

    async def handle_function_calls(self, candidate) -> None:
        """Handle function calls from the LLM."""
        parts: List[Part] = []
        for func in candidate.function_calls:
            func_rsp = await workflow.execute_activity(
                func.name,
                args=func.args,
                start_to_close_timeout=timedelta(seconds=10),
            )
            response_part = Part.from_function_response(
                name=func.name,
                response={"content": func_rsp},
            )
            parts.append(response_part)
        self.contents.append(Content(role="user", parts=parts))
