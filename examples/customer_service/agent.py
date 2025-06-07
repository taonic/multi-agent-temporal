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


async def main():
    agent = Agent(
        name="Store Support Agent",
        model_name="gemini-2.0-flash",
        instruction="You are a store support API assistant to help with online orders.",
        functions = [greet, get_order_status]
    )
    
    message = """
        Agent started. Type 'exit' to quit.\
            
        You can check your order status by providing an order ID.
    """
    
    async with Runner(app_name="slack_agent_runner", agent=agent) as runner:
        await AgentConsole(runner).run(welcome_message=dedent(message))


if __name__ == "__main__":
    asyncio.run(main())
