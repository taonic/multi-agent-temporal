# GitHub Research Agent Example

This example demonstrates how to create a multi-agent system that can search and analyze GitHub repositories to answer technical questions about software implementations, architectures, and code patterns.

## Overview

This example creates a system of specialized agents that work together to help users research technical implementations in GitHub:

- **GitHub Research Agent**: The root agent that coordinates the research process
- **Repository Explorer**: Finds and explores GitHub repositories in organizations  
- **Code Search Specialist**: Searches for specific code implementations, functions, and patterns
- **Issue and PR Specialist**: Analyzes issues and pull requests for design discussions and context

## Features

- Search for repositories in specific organizations
- Find code implementations using targeted searches
- Analyze issues and PRs for design context
- Answer technical questions like:
  - "How does Temporal implement rate limiting on the server side?"
  - "How does Temporal's Go SDK implement workflow sleep?"

## Setup Instructions

### 1. GitHub Token (Optional but Recommended)

For higher API rate limits, set up a GitHub Personal Access Token:

1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Generate a new fine-grained personal access tokens: https://github.com/settings/personal-access-tokens (Only public repositories is required)
3. Set the environment variable:

```bash
export GITHUB_TOKEN=your_github_token_here
```

**Note**: Without a token, you'll be limited to 60 requests per hour. With a token, you get 5,000 requests per hour.

### 2. Google Cloud Platform Setup for VertexAI

1. Create a GCP project
2. Enable the VertexAI API:
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

3. Set up authentication:
   ```bash
   gcloud auth application-default login
   # OR set service account key
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
   ```

4. Set your project ID:
   ```bash
   export GCP_PROJECT_ID=your-gcp-project-id
   ```

## Running the Example

Install dependencies and start the agent:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run the agent
uv run python -m examples.multi_agent_github.agent
```

## Example Queries

Here are some example questions you can ask:

### Temporal-specific Questions
- "How does Temporal implement rate limiting on the server side?"
- "How does Temporal's Go SDK implement workflow sleep?"
- "What's the architecture of Temporal's worker polling mechanism?"
- "How does Temporal handle workflow state persistence?"

### Language-specific Searches
- "Show me rate limiting implementations in Go"
- "Find circuit breaker patterns in Java"
- "How is async/await implemented in Python?"

The agent automatically handles rate limiting by using proper headers and error handling.

```

## Dependencies

- Python 3.10+
- GitHub API access (public repositories)
- Google Cloud Platform account for VertexAI

## Troubleshooting

### Rate Limit Issues
- Set `GITHUB_TOKEN` for higher limits
- The agent will show rate limit errors if exceeded

### Authentication Issues
- Verify `GCP_PROJECT_ID` is set correctly
- Check VertexAI API is enabled
- Ensure proper GCP authentication is configured

### Search Quality
- Use specific technical terms in your queries
- Include organization names when looking for specific implementations
- The agent works best with concrete technical questions

## Example Session

```
🤖 GitHub Research Agent started!

> How does Temporal implement rate limiting on the server side?

🤖 Agent is thinking...
💭 I need to search for Temporal's rate limiting implementation. Let me start by exploring their repositories...
💭 Found the main temporal repository. Now searching for rate limiting code...
💭 Looking for rate limiter implementations in Go...

🤖 Agent: Based on my analysis of Temporal's codebase, here's how rate limiting is implemented on the server side:

## Summary
Temporal implements rate limiting using a token bucket algorithm with Redis as the backing store...

[Detailed technical explanation with code references]
```