import os
import asyncio
import inflection

from typing import List, Dict, Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    import vertexai
    from vertexai.generative_models import (
        GenerativeModel,
    )


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