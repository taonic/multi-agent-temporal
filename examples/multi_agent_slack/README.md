# Multiagent Slack Integration

A example that demonstrates a multiagent system for searching and analyzing Slack conversations.

## Overview

This example creates a system of specialized agents that work together to help users research topics in their Slack workspace:

- **Slack Research Agent**: The root agent that coordinates the sub-agents
- **Channel Explorer**: Helps find and navigate Slack channels
- **Search Specialist**: Searches Slack for relevant information
- **Thread Specialist**: Summarizes Slack conversation threads

## Setup Instructions

### 1. Slack User Token

This example requires a Slack User Token (starts with `xoxp-`) with the following permissions:

- `channels:read` - To list public channels
- `groups:read` - To access private channels
- `search:read` - To search messages
- `channels:history` - To access channel messages

To obtain a Slack User Token:

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Create a new app in your workspace
3. Go to "OAuth & Permissions"
4. Add the required scopes listed above
5. Install the app to your workspace
6. Copy the User OAuth Token (starts with `xoxp-`)

### 2. Environment Setup

Set the following environment variables:

```bash
# Slack User Token
export SLACK_USER_TOKEN=xoxp-your-user-token

# Google Cloud Project ID
export GCP_PROJECT_ID=your-gcp-project-id
```

### 3. Google Cloud Platform Setup for VertexAI

1. Create a GCP project
2. Enable the VertexAI API:
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

3. Create a service account with these roles:
   - `roles/aiplatform.serviceAgent`

4. Download the service account key JSON file
5. Set the environment variable:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
   ```

## Running the Example

Start the agent:

Install uv if you havn't
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```
uv run python -m examples.multiagent_slack.agent
```

The agent will start an interactive console where you can ask questions like:
- "What are the new product features discussed in the last week?"
- "Summarize thread: https://yourworkspace.slack.com/archives/ABCDEF/1234567890123456"

## Requirements

- Python 3.10+
- A Slack workspace with appropriate API permissions