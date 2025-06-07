import inflection

from typing import List, Dict, Any

class Agent:
    """Agent class that manages the Temporal worker and workflow execution."""

    def __init__(
        self,
        name: str,
        model_name: str = "gemini-2.0-flash",
        instruction: str = "You are a store support API assistant to help with online orders.",
        functions: List[callable] = None,
        sub_agents: List['Agent'] = None,
        input_schema: Dict[str, Any] = {}
    ):
        """Initialize the agent.

        Args:
            name: Name of the agent
            model_name: Vertex AI model name
            instruction: System instruction for the LLM
            functions: List of functions available to the agent
            sub_agents: List of specialized sub-agents
            input_schema: JSON schema defining the expected input format
        """
        self.name = inflection.parameterize(name)
        self.model_name = model_name
        self.instruction = instruction
        self.functions = functions or []
        self.sub_agents = sub_agents or []
        self.input_schema = input_schema