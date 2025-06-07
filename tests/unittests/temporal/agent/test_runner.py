import pytest
import asyncio
import uuid
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import sys
import os
# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../src')))

from temporal.agent.runner import Runner
from temporal.agent.agent import Agent
from temporal.agent.workflow import AgentWorkflow, AgentWorkflowInput

        # Use standalone functions instead of methods
def sample_function(param: str) -> str:
    return f"Result: {param}"

# Use standalone functions instead of methods
def another_function(value: int) -> int:
    return value * 2

class TestRunner:
    """Test suite for the Runner class."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent for testing."""
        agent = Mock(spec=Agent)
        agent.name = "Test Agent"
        agent.functions = [sample_function]
        agent.sub_agents = []
        return agent

    @pytest.fixture
    def mock_sub_agent(self):
        """Create a mock sub-agent for testing."""
        sub_agent = Mock(spec=Agent)
        sub_agent.name = "Sub Agent"
        sub_agent.functions = [another_function]
        sub_agent.sub_agents = []
        return sub_agent
    
    @pytest.fixture
    def mock_sub_sub_agent(self):
        """Create a mock sub-agent for testing."""
        sub_agent = Mock(spec=Agent)
        sub_agent.name = "Sub Agent"
        sub_agent.functions = [another_function]
        sub_agent.sub_agents = []
        return sub_agent    

    @pytest.fixture
    def runner(self, mock_agent):
        """Create a Runner instance for testing."""
        return Runner(app_name="test-app", agent=mock_agent)

    def test_agent_hierarchy(self, mock_agent, mock_sub_agent, mock_sub_sub_agent):
        """Test _agent_hierarchy method."""
        mock_agent.sub_agents = [mock_sub_agent]
        mock_sub_agent.sub_agents = [mock_sub_sub_agent]
        runner = Runner(app_name="test-app", agent=mock_agent)
        
        expected_hierarchy = {
            mock_sub_agent.name: {
                mock_sub_sub_agent.name: {}
            }
        }
        
        assert runner.agent_hierarchy == expected_hierarchy

    def test_functions_to_activities(self, mock_agent, mock_sub_agent):
        """Test _functions_to_activities method."""
        mock_agent.sub_agents = [mock_sub_agent]
        runner = Runner(app_name="test-app", agent=mock_agent)
        
        activities = runner._functions_to_activities(mock_agent)
        
        assert len(activities) > 0
        assert callable(activities[0])

    @pytest.mark.asyncio
    async def test_connect(self, runner):
        """Test _connect method."""
        with patch('temporal.agent.runner.Client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.connect = AsyncMock(return_value=mock_client_instance)
            
            await runner._connect()
            
            mock_client.connect.assert_called_once_with(runner.temporal_address)
            assert runner.client == mock_client_instance

    @pytest.mark.asyncio
    async def test_thoughts(self, runner):
        """Test thoughts method."""
        # Setup mocks
        mock_client = AsyncMock()
        runner.client = mock_client
        runner.workflow_id = "test-workflow-id"
        
        # Create a mock handle that returns a proper AsyncMock for query
        mock_handle = AsyncMock()
        mock_handle.query = AsyncMock(return_value=["Thought 1", "Thought 2"])
        
        # Make get_workflow_handle return our mock handle
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        # Test with default watermark
        result = await runner.thoughts()
        
        mock_client.get_workflow_handle.assert_called_once_with(runner.workflow_id)
        mock_handle.query.assert_called_once_with(AgentWorkflow.get_model_content, 0)
        assert result == ["Thought 1", "Thought 2"]
        
        # Test with custom watermark
        mock_client.get_workflow_handle.reset_mock()
        mock_handle.query.reset_mock()
        mock_handle.query = AsyncMock(return_value=["Thought 3", "Thought 4"])
        
        result = await runner.thoughts(watermark=5)
        
        mock_client.get_workflow_handle.assert_called_once_with(runner.workflow_id)
        mock_handle.query.assert_called_once_with(AgentWorkflow.get_model_content, 5)
        assert result == ["Thought 3", "Thought 4"]

    @pytest.mark.asyncio
    async def test_prompt(self, runner):
        """Test prompt method."""
        # Setup mocks
        mock_client = AsyncMock()
        runner.client = mock_client
        runner.workflow_id = "test-workflow-id"
        
        # Create a mock handle that returns a proper AsyncMock for execute_update
        mock_handle = AsyncMock()
        mock_handle.execute_update = AsyncMock(return_value="Response from agent")
        
        # Make get_workflow_handle return our mock handle
        mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
        
        # Test with string prompt
        result = await runner.prompt("Hello agent")
        
        mock_client.get_workflow_handle.assert_called_once_with(runner.workflow_id)
        mock_handle.execute_update.assert_called_once_with(AgentWorkflow.prompt, "Hello agent")
        assert result == "Response from agent"
        
        # Test with dict prompt
        mock_client.get_workflow_handle.reset_mock()
        mock_handle.execute_update.reset_mock()
        mock_handle.execute_update = AsyncMock(return_value="Response from agent for dict")
        
        dict_prompt = {"query": "Hello agent", "context": "Some context"}
        result = await runner.prompt(dict_prompt)
        
        mock_client.get_workflow_handle.assert_called_once_with(runner.workflow_id)
        mock_handle.execute_update.assert_called_once_with(AgentWorkflow.prompt, dict_prompt)
        assert result == "Response from agent for dict"

if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])