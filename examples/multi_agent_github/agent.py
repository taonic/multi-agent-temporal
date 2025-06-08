import os
import asyncio
import logging

from textwrap import dedent
from temporal.agent import Agent, Runner, AgentConsole

from .tools import get_repos, search_github_code, search_github_issues, download_github_file
from .sys_prompt import get_system_prompt
from .schemas import RepositorySchema, CodeSearchSchema, IssueSearchSchema, FileDownloadSchema

async def main():
    """Main interactive loop with GitHub-enabled agent."""

    repository_agent = Agent(
        name="Repository Explorer",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction="You help find and explore GitHub repositories in organizations. Use get_repos to retrieve repositories from specific organizations or users. Focus on discovering relevant repositories that likely contain the implementation or feature being asked about.",
        functions=[get_repos],
        input_schema=RepositorySchema
    )
    
    code_search_agent = Agent(
        name="Code Search Specialist",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction="You specialize in searching GitHub code to find specific implementations, functions, classes, and patterns. Use targeted searches to locate exact code that answers technical questions.",
        functions=[search_github_code],
        input_schema=CodeSearchSchema
    )
    
    issue_search_agent = Agent(
        name="Issue and PR Specialist",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction="You specialize in searching GitHub issues and pull requests to find design discussions, implementation details, and context around features and bugs.",
        functions=[search_github_issues],
        input_schema=IssueSearchSchema
    )

    file_download_agent = Agent(
        name="Source Code Analyst",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction="You specialize in downloading and analyzing specific source code files from GitHub repositories. Use this when you need to examine the complete implementation of a specific file, function, or module that was identified through code search.",
        functions=[download_github_file],
        input_schema=FileDownloadSchema
    )

    root_agent = Agent(
        name="GitHub Research Agent",
        model_name="models/gemini-2.5-pro-preview-05-06",
        instruction=get_system_prompt(),
        sub_agents=[repository_agent, code_search_agent, issue_search_agent, file_download_agent]
    )

    message = """
        🤖 GitHub Research Agent started!
        
        I can help you research technical implementations and code patterns in GitHub repositories.
        
        Example questions you can ask:
        • How does Temporal implement rate limiting on the server side?
        • How does Temporal's Go SDK implement workflow sleep?
        • How does Temporal implement workflow state persistence and event sourcing?
        • How does Temporal's worker polling mechanism work across different SDKs?
        • How does Temporal implement workflow determinism and replay safety?
        
        Note: Set GITHUB_TOKEN environment variable for higher API rate limits.
        
        Type 'exit' to quit.

        Send your first question:
    """

    async with Runner(app_name="github_research_agent", agent=root_agent) as runner:
        await AgentConsole(runner).run(welcome_message=dedent(message))


if __name__ == "__main__":
    try:
        logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")