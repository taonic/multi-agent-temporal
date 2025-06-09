import asyncio

from temporal.agent import Agent, Runner, AgentConsole
from textwrap import dedent

async def greet(name: str) -> str:
    return f"hi {name}, how's your day been?"

def get_order_status(order_id: str):
    return {
        "order_id": order_id,
        "expected_delivery": "Tomorrow",
    }

agent = Agent(
    name="Store Support Agent",
    model_name="gemini-2.0-flash",
    instruction="You are a store support API assistant to help with online orders.",
    functions = [greet, get_order_status]
)

async def main():
    """Starts agent runner."""
    runner = Runner(app_name="slack_agent_runner", agent=agent)
    print("Agent Runner started...")
    await runner.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
