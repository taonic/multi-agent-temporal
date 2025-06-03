import sys
import os
import asyncio
import aioconsole

relative_path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(relative_path)

from src.agent import Agent

async def greet(name: str) -> str:
    return f"hi {name}, how's your day been?"

def get_order_status(order_id: str):
    return {
        "order_id": order_id,
        "expected_delivery": "Tomorrow",
    }


async def main():
    async with Agent(
        model_name="gemini-2.0-flash",
        instruction="You are a store support API assistant to help with online orders.",
        functions = [greet, get_order_status]
    ) as agent:
        print("Agent started. Type 'exit' to quit.")
        print("Send your first message:")

        while True:
            user_input = await aioconsole.ainput("> ")

            if not user_input.strip():
                continue  # Skip empty input

            if user_input.lower() in ["exit", "quit"]:
                print("Exiting...")
                break

            print("Agent is thinking...")
            result = await agent.prompt(user_input)
            print(f"Agent: {result}")


if __name__ == "__main__":
    asyncio.run(main())
