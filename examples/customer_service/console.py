import asyncio
import secrets
from textwrap import dedent

from temporalio.client import Client

from temporal.agent import Session, AgentConsole

from .runner import agent


async def main():
    message = """
        Agent started. Type 'exit' to quit.\
            
        You can check your order status by providing an order ID.
    """
    client = await Client.connect("localhost:7233")
    async with Session(session_id=secrets.token_hex(3), client=client, agent=agent) as session:
        await AgentConsole(session=session).run(welcome_message=dedent(message))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
