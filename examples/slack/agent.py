import sys
import os
import asyncio
import aioconsole

relative_path = os.path.join(os.path.dirname(__file__), '../../')
sys.path.append(relative_path)

from examples.slack.tools import get_slack_channels, search_slack, get_thread_messages
from examples.slack.sys_prompt import get_system_prompt
from libs.agent import Agent

async def poll_agent_thoughts(agent):
    """Poll and display agent's thought process."""
    try:
        watermark = 0
        while True:
            thoughts = await agent.thoughts(watermark=watermark)
            if thoughts:
                for line in thoughts:
                    await aioconsole.aprint(f'🧠 {line}')
                watermark += len(thoughts)
            await asyncio.sleep(2)  # Poll every 2 seconds
    except asyncio.CancelledError:
        pass

async def process_user_input(agent, user_input):
    """Process user input and return agent's response."""
    if not user_input.strip():
        return None  # Skip empty input
        
    if user_input.lower() in ["exit", "quit", "bye"]:
        return "exit"
        
    print("🤔 Agent is thinking...")
    
    # Start polling task to monitor agent's thoughts
    polling_task = asyncio.create_task(poll_agent_thoughts(agent))
    
    try:
        result = await agent.prompt(user_input)
        await aioconsole.aprint(f"🤖 Agent: {result}\n")
    finally:
        # Always cancel the polling task when done
        polling_task.cancel()
        
    return result

def print_welcome_message():
    """Print welcome message and usage instructions."""
    print("🤖 Slack-enabled Agent started!")
    print("I can help you to research topics on your Slack workspace.")
    print("You can ask me questions like:")
    print("  • What are the new product features discussed in the last week?")
    print("  • Summarize thread: https://temporaltechnologies.slack.com/archives/ABCDEF/1234567890123456")
    print("Type 'exit' to quit.\n")
    print("Send your first message:")

async def main():
    """Main interactive loop with Slack-enabled agent."""
    try:
        async with Agent(
            model_name="models/gemini-2.5-pro-preview-05-06",
            instruction=get_system_prompt(),
            functions=[get_slack_channels, search_slack, get_thread_messages]
        ) as agent:
            print_welcome_message()
            
            while True:
                try:
                    user_input = await aioconsole.ainput("> ")
                    result = await process_user_input(agent, user_input)
                    
                    if result == "exit":
                        print("👋 Goodbye!")
                        break
                        
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Failed to start agent: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start agent: {e}")