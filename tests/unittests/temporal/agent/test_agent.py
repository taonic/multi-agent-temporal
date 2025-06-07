import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any

from temporal.agent.llm_manager import LLMManager
from temporal.agent.agent import Agent


@dataclass
class MockSchema:
    """Mock schema for testing sub-agents."""
    query: str
    optional_field: str = "default"


class TestLLM:
    """Test suite for the LLM class."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        agent = Mock(spec=Agent)
        agent.name = "Test Agent"
        agent.input_schema = MockSchema
        return agent

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
    def mock_generative_model(self):
        """Mock GenerativeModel for testing."""
        with patch('temporal.agent.llm.GenerativeModel') as mock_model:
            mock_instance = Mock()
            mock_model.return_value = mock_instance
            yield mock_model

    @pytest.fixture
    def mock_create_enhanced_tool(self):
        """Mock create_enhanced_tool function."""
        with patch('temporal.agent.llm_manager.create_enhanced_tool') as mock_tool:
            mock_tool.return_value = Mock()
            yield mock_tool

    def test_sub_agents(self, sample_functions):
        """Test LLM initialization with valid parameters."""
        model_name = "gemini-2.0-flash"
        instruction = "Test instruction"
        sub_agent_1=Agent(
            name="Sub Agent 1",
            model_name=model_name,
            instruction=instruction,
            input_schema=MockSchema,
            functions=sample_functions
        )
        
        manager = LLMManager(
            root_agent=Agent(
                name="Root Agent",
                model_name=model_name,
                instruction=instruction,
                input_schema=MockSchema,
                sub_agents=[sub_agent_1],
                functions=sample_functions
            )
        )
        
        gen_model = manager.llms['root-agent'][0]
        assert gen_model._model_name.endswith(model_name)
        assert gen_model._system_instruction == instruction
        
        tool = manager.llms['root-agent'][1]
        resolved_properties = tool._callable_functions['test_function'].to_dict()['parameters']['properties']
        assert resolved_properties == {'param': {'type': 'STRING', 'title': 'Param'}}
        
        gen_model = manager.llms['sub-agent-1'][0]
        assert gen_model._model_name.endswith(model_name)
        assert gen_model._system_instruction == instruction

        tool = manager.llms['sub-agent-1'][1]
        resolved_properties = tool._callable_functions['another_function'].to_dict()['parameters']['properties']
        assert resolved_properties == {'value': {'type': 'INTEGER', 'title': 'Value'}}
        

    def test_llm_initialization_empty_sub_agents(self, mock_create_enhanced_tool, sample_functions):
        """Test LLM initialization with empty sub_agents list."""
        model_name = "gemini-2.0-flash"
        instruction = "Test instruction"
        sub_agents = []
        
        manager = LLMManager(
            root_agent=Agent(
                name="Root Agent",
                model_name=model_name,
                instruction=instruction,
                input_schema=MockSchema,
                sub_agents=sub_agents,
                functions=sample_functions
            )
        )
        
        gen_model = manager.llms['root-agent'][0]
        assert gen_model is not None
        assert len(manager.llms) == 1  # Only root agent should be present


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])

#     def test_llm_initialization_complex_agent_names(self, mock_generative_model, mock_create_enhanced_tool, sample_functions):
#         """Test LLM initialization with complex agent names that need normalization."""
#         agent1 = Mock(spec=Agent)
#         agent1.name = "Channel Explorer Agent"
#         agent1.input_schema = MockSchema
        
#         agent2 = Mock(spec=Agent)
#         agent2.name = "Search-Specialist"
#         agent2.input_schema = MockSchema
        
#         agent3 = Mock(spec=Agent)
#         agent3.name = "Thread Analyzer"
#         agent3.input_schema = MockSchema
        
#         sub_agents = [agent1, agent2, agent3]
        
#         llm = LLM(
#             model_name="gemini-2.0-flash",
#             instruction="Test instruction",
#             sub_agents=sub_agents,
#             functions=sample_functions
#         )
        
#         # Verify sub_agents mapping with normalized names
#         mock_create_enhanced_tool.assert_called_once()
#         call_args = mock_create_enhanced_tool.call_args
#         expected_sub_agents = {
#             "channel_explorer_agent": MockSchema,
#             "search_specialist": MockSchema,
#             "thread_analyzer": MockSchema
#         }
#         assert call_args[1]['sub_agents'] == expected_sub_agents

#     @patch('temporal.agent.llm.Content')
#     @patch('temporal.agent.llm.GenerationConfig')
#     def test_call_llm_execution(self, mock_generation_config, mock_content, mock_generative_model, mock_create_enhanced_tool, sample_functions):
#         """Test the call_llm method execution."""
#         # Setup mocks
#         mock_content_instance = Mock()
#         mock_content.from_dict.return_value = mock_content_instance
        
#         mock_response = Mock()
#         mock_response.to_dict.return_value = {"response": "test"}
        
#         # Set up the mock instance for generate_content
#         mock_model_instance = Mock()
#         mock_model_instance.generate_content.return_value = mock_response
#         mock_generative_model.return_value = mock_model_instance
        
#         mock_generation_config_instance = Mock()
#         mock_generation_config.return_value = mock_generation_config_instance
        
#         # Create LLM instance
#         llm = LLM(
#             model_name="gemini-2.0-flash",
#             instruction="Test instruction",
#             sub_agents=[],
#             functions=sample_functions
#         )
        
#         # Test data
#         test_contents = [
#             {"role": "user", "parts": [{"text": "Hello"}]},
#             {"role": "model", "parts": [{"text": "Hi there!"}]}
#         ]
        
#         # Call the method
#         result = llm.call_llm(test_contents)
        
#         # Verify Content.from_dict was called for each content
#         assert mock_content.from_dict.call_count == len(test_contents)
#         mock_content.from_dict.assert_any_call(test_contents[0])
#         mock_content.from_dict.assert_any_call(test_contents[1])
        
#         # Verify GenerationConfig was created with temperature=0
#         mock_generation_config.assert_called_once_with(temperature=0)
        
#         # Verify generate_content was called with correct parameters
#         mock_model_instance = mock_generative_model.return_value
#         mock_model_instance.generate_content.assert_called_once()
#         call_args = mock_model_instance.generate_content.call_args
        
#         # Check that contents were passed as Content objects
#         assert len(call_args[1]['contents']) == 2
        
#         # Check generation_config and tools were passed
#         assert call_args[1]['generation_config'] == mock_generation_config_instance
#         assert call_args[1]['tools'] == [llm.tools]
        
#         # Verify result
#         assert result == {"response": "test"}

#     def test_call_llm_empty_contents(self, mock_generative_model, mock_create_enhanced_tool, sample_functions):
#         """Test call_llm with empty contents list."""
#         with patch('temporal.agent.llm.Content') as mock_content, \
#              patch('temporal.agent.llm.GenerationConfig') as mock_generation_config:
            
#             mock_response = Mock()
#             mock_response.to_dict.return_value = {"response": "empty"}
            
#             # Set up the mock instance for generate_content
#             mock_model_instance = Mock()
#             mock_model_instance.generate_content.return_value = mock_response
#             mock_generative_model.return_value = mock_model_instance
            
#             llm = LLM(
#                 model_name="gemini-2.0-flash",
#                 instruction="Test instruction",
#                 sub_agents=[],
#                 functions=sample_functions
#             )
            
#             result = llm.call_llm([])
            
#             # Verify no Content.from_dict calls
#             mock_content.from_dict.assert_not_called()
            
#             # Verify generate_content was still called with empty contents
#             mock_model_instance = mock_generative_model.return_value
#             mock_model_instance.generate_content.assert_called_once()
#             call_args = mock_model_instance.generate_content.call_args
#             assert call_args[1]['contents'] == []
            
#             assert result == {"response": "empty"}

#     def test_call_llm_with_activity_logger(self, mock_generative_model, mock_create_enhanced_tool, sample_functions):
#         """Test that call_llm uses activity logger for debugging."""
#         with patch('temporal.agent.llm.Content') as mock_content, \
#              patch('temporal.agent.llm.GenerationConfig'), \
#              patch('temporal.agent.llm.activity') as mock_activity:
            
#             # Setup activity logger mock
#             mock_logger = Mock()
#             mock_activity.logger = mock_logger
            
#             mock_response = Mock()
#             mock_response.to_dict.return_value = {"response": "test"}
#             mock_generative_model.generate_content.return_value = mock_response
            
#             llm = LLM(
#                 model_name="gemini-2.0-flash",
#                 instruction="Test instruction",
#                 sub_agents=[],
#                 functions=sample_functions
#             )
            
#             test_contents = [{"role": "user", "parts": [{"text": "Hello"}]}]
            
#             result = llm.call_llm(test_contents)
            
#             # Verify logger.debug was called
#             mock_logger.debug.assert_called_once()
#             log_call = mock_logger.debug.call_args[0][0]
#             assert "Generates content with toos" in log_call  # Note: typo is in original code
#             assert str(llm.tools) in log_call

#     @pytest.mark.asyncio
#     async def test_integration_with_real_functions(self, mock_generative_model, mock_create_enhanced_tool):
#         """Integration test with real function definitions."""
#         def greet(name: str) -> str:
#             """Greet someone by name."""
#             return f"Hello, {name}!"
        
#         def calculate(a: int, b: int) -> int:
#             """Calculate sum of two numbers."""
#             return a + b
        
#         real_functions = [greet, calculate]
        
#         llm = LLM(
#             model_name="gemini-2.0-flash",
#             instruction="You are a helpful assistant.",
#             sub_agents=[],
#             functions=real_functions
#         )
        
#         # Verify that functions were passed correctly
#         mock_create_enhanced_tool.assert_called_once()
#         call_args = mock_create_enhanced_tool.call_args
#         assert call_args[1]['functions'] == real_functions
#         assert call_args[1]['sub_agents'] == {}

#     def test_error_handling_in_initialization(self, mock_create_enhanced_tool):
#         """Test error handling during LLM initialization."""
#         with patch('temporal.agent.llm.GenerativeModel') as mock_model:
#             # Make GenerativeModel raise an exception
#             mock_model.side_effect = Exception("Model initialization failed")
            
#             with pytest.raises(Exception, match="Model initialization failed"):
#                 LLM(
#                     model_name="invalid-model",
#                     instruction="Test instruction",
#                     sub_agents=[],
#                     functions=[]
#                 )
#     @patch('temporal.agent.llm.create_enhanced_tool')
#     def test_tool_creation_error_handling(self, mock_tool, mock_generative_model):
#         """Test error handling when tool creation fails."""
#         mock_tool.side_effect = Exception("Tool creation failed")
        
#         with pytest.raises(Exception, match="Tool creation failed"):
#             LLM(
#                 model_name="gemini-2.0-flash",
#                 instruction="Test instruction",
#                 sub_agents=[],
#                 functions=[]
#             )


# if __name__ == "__main__":
#     # Run the tests
#     pytest.main([__file__, "-v"])