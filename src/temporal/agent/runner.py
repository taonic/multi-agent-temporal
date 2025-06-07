import asyncio
import uuid
import logging
from typing import List, Dict, Union, Any
from temporalio.client import Client
from temporalio.worker import Worker
from concurrent.futures import ThreadPoolExecutor
from temporalio import activity

from temporal.agent import Agent
from temporal.agent.llm_manager import LLMManager
from temporal.agent.workflow import AgentWorkflow
from temporal.agent.workflow import AgentWorkflowInput


class Runner:
    """Runner class to execute the agent in an application context."""
    def __init__(self, app_name: str, agent: Agent, temporal_address: str = "localhost:7233"):
        self.app_name = app_name
        self.agent = agent
        self.task_queue = "agent-task-queue"
        self.temporal_address = temporal_address
        self.client = None
        self.worker = None
        self.worker_task = None
        self.workflow_id = None
        self.functions = self._process_functions(agent)
        logging.debug(f'functions: {self.functions}')
        self.agent_tree = self._agent_tree(agent)
        
    async def thoughts(self, watermark: int = 0) -> List[str]:
        """Dump the current state of the agent workflow.
        
        Args:
            watermark: Position to start reading thoughts from
            
        Returns:
            List of thought strings from the workflow
        """
        if not self.client:
            await self._connect()
            
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
            await self._connect()

        handle = self.client.get_workflow_handle(self.workflow_id)
        result = await handle.execute_update(AgentWorkflow.prompt, prompt)
        return result

        
    def _agent_tree(self, agent: Agent) -> Dict:
        """Generate a tree representation of the agent and its sub-agents."""
        tree = {
            agent.name: {sub_agent.name: self._agent_tree(sub_agent) for sub_agent in agent.sub_agents}
        }

        return tree
        
    def _process_functions(self, agent: Agent) -> List[callable]:
        """Process the agent's functions and return them as a list."""
        functions = []

        for fn in agent.functions:
            if not hasattr(fn, "__temporal_activity_definition"):
                activity._Definition._apply_to_callable(fn=fn, activity_name=fn.__name__)
            functions.append(fn)

        for sub_agent in agent.sub_agents:
            functions.extend(self._process_functions(sub_agent))

        return functions
        
    async def _connect(self) -> None:
        """Connect to the Temporal server."""
        self.client = await Client.connect(self.temporal_address)
        
    async def __aenter__(self):
        """Enter the async context manager."""
        await self._connect()
        
        llm_manager = LLMManager(self.agent)

        # Create a worker that will run in the background during the context
        self.worker = Worker(
            self.client,
            task_queue=self.task_queue,
            workflows=[AgentWorkflow],
            activities=self.functions + [llm_manager.call_llm],
            activity_executor=ThreadPoolExecutor(100),
        )

        # Start worker as background task
        self.worker_task = asyncio.create_task(self.worker.run())
        self.workflow_id = str(uuid.uuid4())

        # Execute the workflow with model info
        await self.client.start_workflow(
            AgentWorkflow.run,
            AgentWorkflowInput(agent_name=self.agent.name, sub_agents=self.agent_tree, is_root_agent=True),
            id=self.workflow_id,
            task_queue=self.task_queue,
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        # end the workflow
        # await self.prompt("END")

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        # Clean up any other resources
        self.worker = None
        self.client = None