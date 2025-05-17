import sys
import os
import asyncio

relative_path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(relative_path)

from temporalio import activity
from libs.agent import Agent

async def greet(name: str) -> str:
    return f"hello {name}!"


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
        result = await agent.prompt("My name is Tao. What's the status of my order ID #1?")
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
