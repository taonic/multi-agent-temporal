import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

from temporalio import activity
from vertexai.generative_models import GenerativeModel, Content, GenerationConfig, Tool

from .tools_util import create_enhanced_tool
from .agent import Agent

@dataclass
class LLMCallInput:
    """Input for the LLM call activity."""
    agent_name: str
    contents: List[Dict]

class LLMManager:
    """Manager for LLMs and tools.

    Attributes:
        llms: Dictionary of LLMs and tools
    """

    llms: Dict[str, Tuple[GenerativeModel, Tool]]
    
    def __init__(self, root_agent: Agent) -> None:
        """Initialize the LLM with the agent's model and tools.

        Args:
            agent: The Agent instance containing the model and tools
        """
        self.llms = {}
        self._build_llms(root_agent)
    
    def _build_llms(self, agent: Agent) -> None:
        """Recursively build tools for the agent and its sub-agents."""
        tool = create_enhanced_tool(
            functions=agent.functions,
            sub_agents={a.name: a.input_schema for a in agent.sub_agents}
        )
        logging.debug("tool: %s", tool)
        
        model = GenerativeModel(
            agent.model_name,
            system_instruction=agent.instruction
        )
        self.llms[agent.name] = [model, tool]
        
        for sub_agent in agent.sub_agents:
            self._build_llms(sub_agent)

    @activity.defn
    def call_llm(self, call_input: LLMCallInput) -> Dict:
        """Activity to call the LLM with the given input."""
        
        model = self.llms[call_input.agent_name][0]
        tool = self.llms[call_input.agent_name][1]

        # Convert dict to Content objects
        vertex_contents = [Content.from_dict(c) for c in call_input.contents]

        activity.logger.debug(f'Generates content with tool: {tool}')

        # Generate response
        return model.generate_content(
            contents=vertex_contents,
            generation_config=GenerationConfig(temperature=0),
            tools=[tool],
        ).to_dict()