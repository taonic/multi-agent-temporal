import sys
import os
import asyncio
import aioconsole
from typing import List, Dict, Optional
from datetime import datetime, timedelta

relative_path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(relative_path)

from src.agent import Agent

def get_slack_channels(include_archived: bool = False, include_private: bool = False) -> List[Dict[str, Any]]:
    """Get a list of Slack channels from the workspace.

    Args:
        include_archived: Whether to include archived channels (default: False)
        include_private: Whether to include private channels (default: False)

    Returns:
        List of channel dictionaries with id, name, and other metadata

    Raises:
        ValueError: If SLACK_BOT_TOKEN environment variable is not set
        SlackApiError: If the Slack API request fails
    """
    # Get API token from environment variable
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    if not slack_token:
        raise ValueError("SLACK_BOT_TOKEN environment variable is required")

    # Initialize Slack client
    client = WebClient(token=slack_token)

    try:
        # Determine channel types to include
        channel_types = ["public_channel"]
        if include_private:
            channel_types.append("private_channel")

        # Make the API request
        response = client.conversations_list(
            exclude_archived=not include_archived,
            types=",".join(channel_types),
            limit=1000  # Maximum allowed by Slack API
        )

        channels = response.get("channels", [])

        # Log channel information for debugging
        logger.info(f"Retrieved {len(channels)} channels from Slack workspace")
        for channel in channels:
            logger.debug(f"Channel: #{channel.get('name')} (ID: {channel.get('id')}, "
                        f"Members: {channel.get('num_members', 'N/A')}, "
                        f"Private: {channel.get('is_private', False)}, "
                        f"Archived: {channel.get('is_archived', False)})")

        # Return simplified channel data
        simplified_channels = []
        for channel in channels:
            simplified_channels.append({
                "id": channel.get("id"),
                "name": channel.get("name"),
                "is_private": channel.get("is_private", False),
                "is_archived": channel.get("is_archived", False),
                "is_member": channel.get("is_member", False),
                "num_members": channel.get("num_members", 0),
                "purpose": channel.get("purpose", {}).get("value", ""),
                "topic": channel.get("topic", {}).get("value", ""),
                "created": channel.get("created", 0),
                "creator": channel.get("creator", ""),
                "is_general": channel.get("is_general", False),
                "is_channel": channel.get("is_channel", True)
            })

        logger.info(f"Returning {len(simplified_channels)} simplified channel records")
        return simplified_channels

    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving Slack channels: {str(e)}")
        raise

def query_slack_workspace(channels: List[str], keywords: Optional[List[str]] = None,
                         hours_back: int = 24) -> Dict:
    """
    Query a Slack workspace for messages in specific channels with optional keyword filtering.

    Args:
        channels: List of channel names to search in
        keywords: Optional list of keywords to filter messages (case-insensitive)
        hours_back: Number of hours back to search (default: 24)

    Returns:
        Dictionary containing filtered messages organized by channel
    """
    # Calculate cutoff time
    cutoff_time = datetime.now() - timedelta(hours=hours_back)

    results = {}

    for channel in channels:
        if channel not in MOCK_SLACK_DATA:
            continue

        channel_messages = []

        for message in MOCK_SLACK_DATA[channel]:
            # Parse timestamp and check if within time range
            msg_time = datetime.fromisoformat(message["timestamp"].replace('Z', '+00:00'))
            if msg_time < cutoff_time:
                continue

            # Filter by keywords if provided
            if keywords:
                message_text = message["message"].lower()
                if not any(keyword.lower() in message_text for keyword in keywords):
                    continue

            channel_messages.append({
                "channel": channel,
                "user": message["user"],
                "timestamp": message["timestamp"],
                "message": message["message"],
                "thread_replies": message["thread_replies"]
            })

        if channel_messages:
            results[channel] = channel_messages

    return {
        "query_info": {
            "channels_searched": channels,
            "keywords_used": keywords or [],
            "hours_back": hours_back,
            "total_messages_found": sum(len(msgs) for msgs in results.values())
        },
        "messages": results
    }

def get_slack_channels() -> List[str]:
    """Get list of available Slack channels."""
    return list(MOCK_SLACK_DATA.keys())

async def main():
    """Main interactive loop with Slack-enabled agent."""
    async with Agent(
        model_name="gemini-2.0-flash",
        instruction="""You are a helpful assistant that can search Slack workspaces and provide customer support.

Available functions:
- query_slack_workspace: Search for messages in Slack channels with optional keyword filtering
- get_slack_channels: Get list of available channels
- greet: Greet users
- get_order_status: Get order status information

When users ask about Slack messages, use the query_slack_workspace function with appropriate channels and keywords.
Available channels are: general, engineering, product, support.

Be helpful and provide clear summaries of the information you find.""",
        functions=[query_slack_workspace, get_slack_channels, greet, get_order_status]
    ) as agent:

        print("🤖 Slack-enabled Agent started!")
        print("I can help you with:")
        print("  • Searching Slack messages across channels")
        print("  • Order status inquiries")
        print("  • General assistance")
        print("\nAvailable Slack channels: general, engineering, product, support")
        print("Type 'exit' to quit.\n")
        print("Send your first message:")

        while True:
            try:
                user_input = await aioconsole.ainput("> ")

                if not user_input.strip():
                    continue  # Skip empty input

                if user_input.lower() in ["exit", "quit", "bye"]:
                    print("👋 Goodbye!")
                    break

                print("🤔 Agent is thinking...")
                result = await agent.prompt(user_input)
                print(f"🤖 Agent: {result}\n")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Failed to start agent: {e}")
