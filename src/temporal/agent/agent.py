import os
import asyncio
import uuid
import logging
import inflection
import json
from typing import List, Optional, Dict, Any, Union
from concurrent.futures import ThreadPoolExecutor

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

with workflow.unsafe.imports_passed_through():
    import vertexai
    from vertexai.generative_models import (
        GenerativeModel,
    )

from .workflow import AgentWorkflow


class Agent:
    """Agent class that manages the Temporal worker and workflow execution."""

    def __init__(
        self,
        name: str,
        temporal_address: str = "localhost:7233",
        task_queue: str = "agent",
        gcp_project: str = None,
        region: str = "us-central1",
        model_name: str = "gemini-2.0-flash",
        instruction: str = "You are a store support API assistant to help with online orders.",
        functions: List[callable] = None,
        sub_agents: List['Agent'] = None,
        input_schema: Dict[str, Any] = {}
    ):
        """Initialize the agent.

        Args:
            name: Name of the agent
            temporal_address: Address of the Temporal server
            task_queue: Task queue to use for workflows and activities
            gcp_project: Google Cloud project ID
            region: Google Cloud region
            model_name: Vertex AI model name
            instruction: System instruction for the LLM
            functions: List of functions available to the agent
            sub_agents: List of specialized sub-agents
            input_schema: JSON schema defining the expected input format
        """
        self.name = inflection.parameterize(name)
        # Temporal configs
        self.temporal_address = temporal_address
        self.task_queue = task_queue
        self.client = None
        self.worker = None

        # Vertex AI configuration
        self.gcp_project = gcp_project or os.getenv("GCP_PROJECT_ID")
        self.region = region
        self.model_name = model_name
        self.instruction = instruction
        self.functions = functions or []
        self.sub_agents = sub_agents or []
        self.input_schema = input_schema

        self.worker_task = asyncio.Task
        self.workflow_id = None

        # Initialize vertexai
        vertexai.init(project=gcp_project, location=region)

        # Convert functions to activities
        for fn in self.functions:
            if not hasattr(fn, "__temporal_activity_definition"):
                activity._Definition._apply_to_callable(fn=fn, activity_name=fn.__name__)


    async def connect(self) -> None:
        """Connect to the Temporal server."""
        self.client = await Client.connect(self.temporal_address)
        
    async def thoughts(self, watermark: int = 0) -> List[str]:
        """Dump the current state of the agent workflow.
        
        Args:
            watermark: Position to start reading thoughts from
            
        Returns:
            List of thought strings from the workflow
        """
        if not self.client:
            await self.connect()
            
        handle = self.client.get_workflow_handle(self.workflow_id)
        result = await handle.query(AgentWorkflow.get_model_content, watermark)
        return result

    async def prompt(self, prompt: Union[str, Dict[str, Any]]) -> str:
        """Execute the agent workflow with the given prompt.

        Args:
            prompt: Prompt to send to the agent, either as a string or a structured input
                   matching the input_schema if defined

        Returns:
            The agent's response
        """
        if not self.client:
            await self.connect()

        handle = self.client.get_workflow_handle(self.workflow_id)
        result = await handle.execute_update(AgentWorkflow.prompt, prompt)
        return result

    async def __aenter__(self):
        """Enter the async context manager."""
        await self.connect()
        
        sub_agents = {a.name.lower().replace(" ", "_").replace("-", "_"): a.input_schema for a in self.sub_agents}
        
        self.model = GenerativeModel(
            self.model_name,
            system_instruction=[self.instruction]
        )
        
        self.llm = LLM(model=self.model, sub_agents=sub_agents, functions=self.functions)

        logging.basicConfig(level=logging.INFO)  # Change to DEBUG, WARNING, ERROR as needed

        # Create a worker that will run in the background during the context
        self.worker = Worker(
            self.client,
            task_queue=self.task_queue,
            workflows=[AgentWorkflow],
            activities=self.functions + [self.llm.call_llm],
            activity_executor=ThreadPoolExecutor(100),
        )

        # Start worker as background task
        self.worker_task = asyncio.create_task(self.worker.run())
        self.workflow_id = str(uuid.uuid4())

        # Execute the workflow with model info
        await self.client.start_workflow(
            AgentWorkflow.run,
            args=("", sub_agents.keys()),
            id=self.workflow_id,
            task_queue=self.task_queue,
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        # end the workflow
        await self.prompt("END")

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        # Clean up any other resources
        self.worker = None
        self.client = None