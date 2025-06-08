import os
import asyncio
import logging

from textwrap import dedent
from temporal.agent import Agent, Runner, AgentConsole

from .tools import get_slack_channels, search_slack, get_thread_messages
from .sys_prompt import get_system_prompt
from .schemas import ChannelSchema, SearchSchema, ThreadSchema

async def main():
    """Main interactive loop with Slack-enabled agent."""

    channel_agent = Agent(
        name="Channel Explorer",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction="You help find and navigate Slack channels.",
        functions=[get_slack_channels],
        input_schema=ChannelSchema
    )

    search_agent = Agent(
        name="Search Specialist",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction="You specialize in searching Slack for relevant information.",
        functions=[search_slack],
        input_schema=SearchSchema
    )

    thread_summary_agent = Agent(
        name="Thread Specialist",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction="You specialize in summarizing Slack threads.",
        functions=[get_thread_messages],
        input_schema=ThreadSchema
    )

    root_agent = Agent(
        name="Slack Research Agent",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction=get_system_prompt(),
        sub_agents=[channel_agent, search_agent, thread_summary_agent]
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

    async with Runner(app_name="slack_agent_runner", agent=root_agent) as runner:
        await AgentConsole(runner).run(welcome_message=dedent(message))


if __name__ == "__main__":
    try:
        logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")