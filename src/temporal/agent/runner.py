import asyncio
import logging
import os
from functools import cached_property
from typing import List
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker
from temporalio import activity, workflow

with workflow.unsafe.imports_passed_through():
    import vertexai
    from temporal.agent import Agent
    from temporal.agent.llm_manager import LLMManager
    from temporal.agent.workflow import AgentWorkflow

class Runner:
    """
    Runner for executing agent workflows in Temporal.
    This class manages the connection to the Temporal server, starts the worker,
    and provides a session for workflow interaction.
    It supports asynchronous context management to ensure proper resource cleanup.
    """

    def __init__(
        self,
        app_name: str,
        agent: Agent,
        region: str = "us-central1",
        temporal_address: str = "localhost:7233",
        task_queue: str = "agent-task-queue"
    ):
        self.app_name = app_name
        self.agent = agent
        self.region = region
        self.temporal_address = temporal_address
        self.task_queue = task_queue
        self.gcp_project = os.getenv("GCP_PROJECT_ID")
        
        self.worker_task = None
        self.activities = self._functions_to_activities(agent)
        self.client = None
        
        # Initialize vertexai
        vertexai.init(project=self.gcp_project, location=self.region)
        
        logging.debug('Runner initialized with activities: %s', self.activities)
        
    def _functions_to_activities(self, agent: Agent) -> List[callable]:
        """Process the agent's functions and return them as a list."""
        functions = []

        for fn in agent.functions:
            if not hasattr(fn, "__temporal_activity_definition"):
                activity.defn(fn)
            functions.append(fn)

        for sub_agent in agent.sub_agents:
            functions.extend(self._functions_to_activities(sub_agent))

        return functions
    
    async def _connect(self) -> None:
        """Connect to the Temporal server."""
        if self.client is None:
            self.client = await Client.connect(self.temporal_address)    
    
    @cached_property
    async def worker(self) -> Worker:
        """Build the Temporal worker for the agent."""
        await self._connect()
        return Worker(
            self.client,
            task_queue=self.task_queue,
            workflows=[AgentWorkflow],
            activities=self.activities + [LLMManager(self.agent).call_llm],
            activity_executor=ThreadPoolExecutor(100),
        )
        
    async def run(self) -> None:
        """Run the temporal worker"""
        await self._connect()
        worker = await self.worker
        await worker.run()
        
    async def __aenter__(self):
        """Enter the async context manager."""
        await self._connect()
        worker = await self.worker
        self.worker_task = asyncio.create_task(worker.run())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        # Stop the worker
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass