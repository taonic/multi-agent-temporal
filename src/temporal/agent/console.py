import asyncio
import aioconsole
from temporal.agent.session import Session
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from rich.console import Console
    from rich.markdown import Markdown

class AgentConsole:
    """Console application to interact with the agent."""
    
    def __init__(self, session: Session):
        self.session = session
        self.console = Console()
        self.watermark = 0  # Initialize watermark for polling thoughts

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
            while True:
                thoughts = await self.session.thoughts(watermark=self.watermark)
                if thoughts:
                    for line in thoughts:
                        await aioconsole.aprint(f'\n\033[90m💭 {line}\033[0m')
                    self.watermark += len(thoughts)
                await asyncio.sleep(2)  # Poll every 2 seconds
        except asyncio.CancelledError:
            pass

    def _format_markdown_for_terminal(self, text: str) -> str:
        """Format markdown text for better terminal display using Rich."""
        if not text:
            return text
        
        # Create a markdown object and render it to string with ANSI codes
        markdown = Markdown(text)
        
        # Use Rich's console to render markdown to a string with ANSI escape codes
        with self.console.capture() as capture:
            self.console.print(markdown)
        
        return capture.get().rstrip()  # Remove trailing whitespace

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
            result = await self.session.prompt(user_input)
            # Format the markdown response for better terminal display
            formatted_result = self._format_markdown_for_terminal(result)
            await aioconsole.aprint(f"\n🤖 Agent: {formatted_result}\n")
            self.watermark += 1  # Increment watermark after processing input
        finally:
            # Always cancel the polling task when done
            polling_task.cancel()
            
        return result