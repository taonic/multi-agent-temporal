import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from temporal.agent.llm_manager import LLMManager, LLMCallInput
from temporal.agent.agent import Agent


@dataclass
class MockSchema:
    """Mock schema for testing sub-agents."""
    query: str
    optional_field: str = "default"


class TestLLMManager:
    """Test suite for the LLMManager class."""

    @pytest.fixture
    def sample_functions(self):
        """Sample functions for testing."""
        def test_function(param: str) -> str:
            """Test function."""
            return f"Result: {param}"
        
        def another_function(value: int) -> int:
            """Another test function."""
            return value * 2
        
        return [test_function, another_function]

    @pytest.fixture
    def mock_agent(self, sample_functions):
        """Create a mock agent for testing."""
        sub_agent = Agent(
            name="Sub Agent",
            model_name="gemini-2.0-flash",
            instruction="Test instruction",
            input_schema=MockSchema,
            functions=[sample_functions[1]],
            sub_agents=[]
        )
        
        root_agent = Agent(
            name="Root Agent",
            model_name="gemini-2.0-flash",
            instruction="Test instruction",
            input_schema=MockSchema,
            functions=[sample_functions[0]],
            sub_agents=[sub_agent]
        )
        
        return root_agent

    @patch('temporal.agent.llm_manager.GenerativeModel')
    @patch('temporal.agent.llm_manager.create_enhanced_tool')
    def test_llm_manager_initialization(self, mock_create_tool, mock_gen_model, mock_agent):
        """Test LLMManager initialization with agents."""
        # Setup mocks
        mock_tool = Mock()
        mock_create_tool.return_value = mock_tool
        
        mock_model = Mock()
        mock_gen_model.return_value = mock_model
        
        # Create LLMManager
        manager = LLMManager(root_agent=mock_agent)
        
        # Verify LLMs were created for both agents
        assert len(manager.llms) == 2
        assert "root-agent" in manager.llms
        assert "sub-agent" in manager.llms
        
        # Verify GenerativeModel was created with correct parameters
        mock_gen_model.assert_any_call(
            mock_agent.model_name,
            system_instruction=mock_agent.instruction
        )
        
        # Verify create_enhanced_tool was called
        mock_create_tool.assert_any_call(
            functions=mock_agent.functions,
            sub_agents={"sub-agent": MockSchema}
        )

    @patch('temporal.agent.llm_manager.Content')
    @patch('temporal.agent.llm_manager.GenerationConfig')
    def test_call_llm(self, mock_gen_config, mock_content, mock_agent):
        """Test the call_llm activity."""
        with patch('temporal.agent.llm_manager.GenerativeModel') as mock_gen_model, \
             patch('temporal.agent.llm_manager.create_enhanced_tool') as mock_create_tool:
            
            # Setup mocks
            mock_tool = Mock()
            mock_create_tool.return_value = mock_tool
            
            mock_model = Mock()
            mock_response = Mock()
            mock_response.to_dict.return_value = {"response": "test result"}
            mock_model.generate_content.return_value = mock_response
            mock_gen_model.return_value = mock_model
            
            mock_content_obj = Mock()
            mock_content.from_dict.return_value = mock_content_obj
            
            mock_config_obj = Mock()
            mock_gen_config.return_value = mock_config_obj
            
            # Create LLMManager
            manager = LLMManager(root_agent=mock_agent)
            
            # Test data
            test_contents = [
                {"role": "user", "parts": [{"text": "Hello"}]},
                {"role": "model", "parts": [{"text": "Hi there!"}]}
            ]
            
            call_input = LLMCallInput(
                agent_name="root-agent",
                contents=test_contents
            )
            
            # Call the method
            result = manager.call_llm(call_input)
            
            # Verify Content.from_dict was called for each content
            assert mock_content.from_dict.call_count == len(test_contents)
            
            # Verify GenerationConfig was created with temperature=0
            mock_gen_config.assert_called_once_with(temperature=0)
            
            # Verify generate_content was called with correct parameters
            mock_model.generate_content.assert_called_once()
            call_args = mock_model.generate_content.call_args
            
            assert call_args[1]['generation_config'] == mock_config_obj
            assert call_args[1]['tools'] == [mock_tool]
            
            # Verify result
            assert result == {"response": "test result"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])