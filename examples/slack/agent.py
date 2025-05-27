import sys
import os
import asyncio
import aioconsole

relative_path = os.path.join(os.path.dirname(__file__), '../../')
sys.path.append(relative_path)

from examples.slack.tools import get_slack_channels, search_slack, get_thread_messages
from examples.slack.sys_prompt import get_system_prompt
from libs.agent import Agent

async def main():
    """Main interactive loop with Slack-enabled agent."""
    async with Agent(
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction=get_system_prompt(),
        functions=[get_slack_channels, search_slack, get_thread_messages]
    ) as agent:
        print("🤖 Slack-enabled Agent started!")
        print("I can help you to research topics on your Slack workspace.")
        print("You can ask me questions like:")
        print("  • What are the new product features discussed in the last week?")
        print("  • Summarize thread: https://temporaltechnologies.slack.com/archives/ABCDEF/1234567890123456")
        print("Type 'exit' to quit.\n")
        print("Send your first message:")

        while True:
            try:
                user_input = await aioconsole.ainput("> ")

                if not user_input.strip():
                    continue  # Skip empty input

                if user_input.lower() in ["exit", "quit", "bye"]:
                    print("👋 Goodbye!")
                    break

                print("🤔 Agent is thinking...")
                result = await agent.prompt(user_input)
                await aioconsole.aprint(f"🤖 Agent: {result}\n")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start agent: {e}")
