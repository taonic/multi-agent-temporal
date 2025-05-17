import asyncio
import uuid
from typing import List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

with workflow.unsafe.imports_passed_through():
    import vertexai
    from vertexai.generative_models import (
        GenerativeModel,
    )

from .workflow import AgentWorkflow, LLM
from ..helpers import load_functions


class Agent:
    """Agent class that manages the Temporal worker and workflow execution."""

    def __init__(
        self,
        temporal_address: str = "localhost:7233",
        task_queue: str = "agent",
        project_id: str = "",
        region: str = "us-central1",
        model_name: str = "gemini-2.0-flash",
        instruction: str = "You are a store support API assistant to help with online orders.",
        functions: List[callable] = None
    ):
        """Initialize the agent.

        Args:
            temporal_address: Address of the Temporal server
            task_queue: Task queue to use for workflows and activities
            project_id: Google Cloud project ID
            region: Google Cloud region
            model_name: Vertex AI model name
            instruction: System instruction for the LLM
        """
        # Temporal configs
        self.temporal_address = temporal_address
        self.task_queue = task_queue
        self.client = None
        self.worker = None

        # Vertex AI configuration
        self.project_id = project_id
        self.region = region
        self.model_name = model_name
        self.instruction = instruction
        self.functions = functions

        # Initialize vertexai
        vertexai.init(project=project_id, location=region)

        # Convert functions to activities
        for fn in self.functions:
            activity._Definition._apply_to_callable(fn=fn, activity_name=fn.__name__)


    async def connect(self) -> None:
        """Connect to the Temporal server."""
        self.client = await Client.connect(self.temporal_address)

    async def prompt(self, prompt: str, workflow_id: Optional[str] = None) -> str:
        """Execute the agent workflow with the given prompt.

        Args:
            prompt: Prompt to send to the agent
            workflow_id: Optional workflow ID to use

        Returns:
            The agent's response
        """
        if not self.client:
            await self.connect()

        # Generate a workflow ID if not provided
        if not workflow_id:
            workflow_id = str(uuid.uuid4())

        # Execute the workflow with model info
        result = await self.client.execute_workflow(
            AgentWorkflow.run,
            prompt,
            id=workflow_id,
            task_queue=self.task_queue,
        )

        return result

    async def __aenter__(self):
        """Enter the async context manager."""
        await self.connect()
        self.model = GenerativeModel(
            self.model_name,
            system_instruction=[self.instruction]
        )
        self.llm = LLM(self.model, self.functions)

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

        # Small delay to ensure worker is ready
        await asyncio.sleep(0.5)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        # Clean up any other resources
        self.worker = None
        self.client = None
