# Slack Research Bot Example

This example demonstrates how to create an AI agent that can search and analyze Slack conversations using VertexAI.

## Prerequisites

- Python 3.8+
- Slack workspace with User Token
- Google Cloud Platform account for VertexAI

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

```bash
uv run examples/slack/agent.py
```

## Example Queries

- "Find me the new product released from the last week"
- "Summarize thread: https://yourworkspace.slack.com/archives/ABCDEF/1234567890123456"

## Troubleshooting

- **Invalid Token Error**: Ensure your SLACK_USER_TOKEN is correctly set and has the required permissions
- **VertexAI Access Issues**: Verify your GCP service account has the correct permissions
