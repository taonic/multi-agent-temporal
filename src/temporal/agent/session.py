import logging
from typing import List, Dict, Union, Any

from temporalio.client import Client

from .workflow import AgentWorkflow, AgentWorkflowInput
from .agent import Agent
import secrets

class Session:
    """
    Session manages the lifecycle of an agent workflow.
    This class is responsible for starting workflows and providing
    methods to interact with them (thoughts, prompt).
    """

    def __init__(
        self,
        agent: Agent,
        client: Client,
        session_id: str = None,
        task_queue: str = "agent-task-queue"
    ):
        """Initialize the session.

        Args:
            session_id: Unique identifier for the session
            agent: The root agent for the workflow
            client: Connected Temporal client
            task_queue: Task queue name for the workflow
        """
        self.session_id = session_id if session_id else secrets.token_hex(3)
        self.agent = agent
        self.client = client
        self.task_queue = task_queue
        self.workflow_id = f'{self.agent.name}-{self.session_id}'
        self.agent_hierarchy = self._agent_hierarchy(agent)
        
        logging.debug('Session initialized with agent_hierarchy: %s', self.agent_hierarchy)

    def _agent_hierarchy(self, agent: Agent) -> Dict:
        """Generate a tree representation of the agent and its sub-agents."""
        return {sub_agent.name: self._agent_hierarchy(sub_agent) for sub_agent in agent.sub_agents}
        
    async def start(self) -> None:
        """Start the agent workflow."""
        await self.client.start_workflow(
            AgentWorkflow.run,
            AgentWorkflowInput(
                agent_name=self.agent.name,
                sub_agents=self.agent_hierarchy,
                is_root_agent=True
            ),
            id=self.workflow_id,
            task_queue=self.task_queue,
        )
        
        logging.debug('Started workflow with ID: %s', self.workflow_id)
    
    async def stop(self) -> None:
        """Stop the agent workflow."""
        if not self.workflow_id:
            raise RuntimeError("Session not started")

        handle = self.client.get_workflow_handle(self.workflow_id)
        await handle.terminate()

    async def thoughts(self, watermark: int = 0) -> List[str]:
        """Get the model responses from the workflow.
        
        Args:
            watermark: Position to start reading thoughts from
            
        Returns:
            List of thought strings from the workflow
        """
        if not self.workflow_id:
            raise RuntimeError("Session not started")
            
        handle = self.client.get_workflow_handle(self.workflow_id)
        result = await handle.query(AgentWorkflow.get_model_content, watermark)
        return result

    async def prompt(self, prompt: Union[str, Dict[str, Any]]) -> str:
        """Send a prompt to the agent workflow.

        Args:
            prompt: Prompt to send to the agent, either as a string or a structured input
                    matching the input_schema if defined

        Returns:
            The agent's response
        """
        if not self.workflow_id:
            raise RuntimeError("Session not started")

        handle = self.client.get_workflow_handle(self.workflow_id)
        result = await handle.execute_update(AgentWorkflow.prompt, prompt)
        return result

    async def __aenter__(self):
        """Async context manager enter - starts the workflow."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - stops the workflow."""
        await self.stop()