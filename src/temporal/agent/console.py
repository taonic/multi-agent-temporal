import asyncio
import json
import aioconsole
from temporal.agent.runner import Runner

class AgentConsole:
    """Console application to interact with the agent."""
    
    def __init__(self, runner: Runner):
        self.runner = runner

    async def run(self, welcome_message: str = "Welcome to the agent console! Type 'help' for commands.") -> None:
        """Run the agent in a console application."""
        print(welcome_message)
        while True:
            try:
                user_input = await aioconsole.ainput("> ")
                result = await self._process_user_input(user_input)
                
                if result == "exit":
                    print("👋 Goodbye!")
                    break
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
                
    async def _poll_agent_thoughts(self):
        """Poll and display agent's thought process."""
        try:
            watermark = 0
            while True:
                thoughts = await self.runner.thoughts(watermark=watermark)
                if thoughts:
                    for line in thoughts:
                        await aioconsole.aprint(f'🤖 {line}')
                    watermark += len(thoughts)
                await asyncio.sleep(2)  # Poll every 2 seconds
        except asyncio.CancelledError:
            pass

    async def _process_user_input(self, user_input: str):
        """Process user input and return agent's response."""
        if not user_input.strip():
            return None  # Skip empty input
            
        if user_input.lower() in ["exit", "quit", "bye"]:
            return "exit"
            
        print("🤖 Agent is thinking...")
        
        # Start polling task to monitor agent's thoughts
        polling_task = asyncio.create_task(self._poll_agent_thoughts())
        
        try:
            result = await self.runner.prompt(user_input)
            await aioconsole.aprint(f"🤖 Agent: {result}\n")
        finally:
            # Always cancel the polling task when done
            polling_task.cancel()
            
        return result