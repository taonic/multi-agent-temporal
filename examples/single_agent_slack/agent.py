import logging
import secrets
import asyncio
from textwrap import dedent

from temporal.agent import Agent, Runner, Session, AgentConsole

from .tools import get_slack_channels, search_slack, get_thread_messages
from .sys_prompt import get_system_prompt

async def main():
    """Main interactive loop with Slack-enabled agent."""
    
    agent = Agent(
        name="Slack Research Agent",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction=get_system_prompt(),
        functions=[get_slack_channels, search_slack, get_thread_messages]
    )
        
    message = """
        🤖 Slack-enabled Agent started!
        I can help you to research topics on your Slack workspace.
        You can ask me questions like:
            • What are the new product features discussed in the last week?
            • Summarize thread: https://temporaltechnologies.slack.com/archives/ABCDEF/1234567890123456
        Type 'exit' to quit.

        Send your first message:
    """
    
    async with Runner(app_name="single_agent_slack", agent=agent) as runner:
        async with Session(client=runner.client, agent=agent) as session:
            await AgentConsole(session=session).run(welcome_message=dedent(message))

if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")