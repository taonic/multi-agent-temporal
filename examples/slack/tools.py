import os
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class GetChannelsRequest:
    """Request parameters for getting Slack channels"""
    include_archived: bool = False
    include_private: bool = False

@dataclass
class SlackSearchRequest:
    """Request parameters for searching Slack messages"""
    query: str
    channels: str = None
    sort: str = "timestamp"
    count: int = 40
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    token: Optional[str] = None

@dataclass
class SlackSearchResult:
    """Data class to hold Slack search results"""
    query: str
    total: int
    matches: List[Dict[str, Any]]
    pagination: Optional[Dict[str, Any]] = None
    has_more: bool = False

@dataclass
class ThreadInput:
    """
    Input object for `get_thread_messages`.

    Attributes
    ----------
    thread_url : str
        Full URL of the Slack thread, e.g.
        https://your-workspace.slack.com/archives/ABCDEF123/p1717518829123456
    """
    thread_url: str

def get_slack_channels(request: GetChannelsRequest) -> List[Dict[str, Any]]:
    """Get a list of Slack channels from the workspace.

    Args:
        request: GetChannelsRequest containing parameters for the channel request

    Returns:
        List of channel dictionaries with id, name, and other metadata

    Raises:
        ValueError: If SLACK_USER_TOKEN environment variable is not set
        SlackApiError: If the Slack API request fails
    """
    # Get API token from environment variable
    slack_token = os.getenv("SLACK_USER_TOKEN")
    if not slack_token:
        raise ValueError("SLACK_USER_TOKEN environment variable is required")

    # Initialize Slack client
    client = WebClient(token=slack_token)

    try:
        # Determine channel types to include
        channel_types = ["public_channel"]
        if request.include_private:
            channel_types.append("private_channel")

        # Make the API request
        response = client.conversations_list(
            exclude_archived=not request.include_archived,
            types=",".join(channel_types),
            limit=1000  # Maximum allowed by Slack API
        )

        channels = response.get("channels", [])

        # Log channel information for debugging
        logger.debug(f"Retrieved {len(channels)} channels from Slack workspace")
        for channel in channels:
            logger.debug(f"Channel: #{channel.get('name')} (ID: {channel.get('id')}, "
                        f"Members: {channel.get('num_members', 'N/A')}, "
                        f"Private: {channel.get('is_private', False)}, "
                        f"Archived: {channel.get('is_archived', False)})")

        # Return simplified channel data
        simplified_channels = []
        for channel in channels:
            simplified_channels.append({
                "name": channel.get("name"),
            })

        logger.debug(f"Returning {len(simplified_channels)} simplified channel records")
        return simplified_channels

    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving Slack channels: {str(e)}")
        raise

def search_slack(request: SlackSearchRequest) -> SlackSearchResult | str:
    """Search Slack messages across channels.

    Args:
        request: SlackSearchRequest containing all search parameters:

    Returns:
        SlackSearchResult returns formatted string as search results

    Raises:
        ValueError: If required parameters are missing or invalid
        SlackApiError: If the Slack API request fails
    """
    # Get API token
    slack_user_token = os.getenv("SLACK_USER_TOKEN")
    if not slack_user_token:
        return error_msg

    # Validate that it's a user token
    if not slack_user_token.startswith("xoxp-"):
        error_msg = f"Invalid token type. Search API requires a User Token starting with 'xoxp-', got token starting with '{slack_user_token[:5]}'"
        return error_msg

    # Validate parameters
    if not request.query or not request.query.strip():
        return "Query parameter is required and cannot be empty"

    if request.count < 1 or request.count > 100:
        return "Count must be between 1 and 100"

    if request.sort not in ["timestamp", "score"]:
        return "Sort must be either 'timestamp' or 'score'"

    # Initialize Slack client
    client = WebClient(token=slack_user_token)

    try:
        # Build the search query
        search_query = request.query.strip()

        # Add channel filters if specified
        if request.channels:
            # Convert comma separated channel list to array and format channels
            formatted_channels = []
            channel_list = request.channels.split(',')
            for channel in channel_list:
                channel = channel.strip()
                if not channel.startswith('#'):
                    formatted_channels.append(f"#{channel}")
                else:
                    formatted_channels.append(channel)

            # Add channel filter to query
            channel_filter = " ".join([f"in:{channel}" for channel in formatted_channels])
            search_query = f"{search_query} {channel_filter}"

        # Add time filters if specified (ISO format only)
        if request.start_time:
            try:
                # Parse ISO format and convert to date string
                dt = datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
                start_date = dt.strftime('%Y-%m-%d')
                search_query = f"{search_query} after:{start_date}"
            except ValueError as e:
                logger.warning(f"Invalid start_time ISO format: {request.start_time}, ignoring time filter")

        if request.end_time:
            try:
                # Parse ISO format and convert to date string
                dt = datetime.fromisoformat(request.end_time.replace('Z', '+00:00'))
                end_date = dt.strftime('%Y-%m-%d')
                search_query = f"{search_query} before:{end_date}"
            except ValueError as e:
                logger.warning(f"Invalid end_time ISO format: {request.end_time}, ignoring time filter")

        logger.debug(f"Executing Slack search with query: '{search_query}'")
        logger.debug(f"Search parameters - sort: {request.sort}, count: {request.count}")

        # Execute the search
        response = client.search_messages(
            query=search_query,
            sort=request.sort,
            count=request.count
        )

        # Extract results
        messages = response.get("messages", {})
        matches = messages.get("matches", [])
        total = messages.get("total", 0)
        pagination = messages.get("pagination", {})
        has_more = pagination.get("total_count", 0) > len(matches)

        logger.debug(f"Search completed - found {total} total results, returning {len(matches)} matches")
        logger.debug(f"Results preview: {[match.get('text', '')[:50] + '...' for match in matches[:3]]}")

        # Create structured result
        result = SlackSearchResult(
            query=search_query,
            total=total,
            matches=matches,
            pagination=pagination,
            has_more=has_more
        )

        # Return structured result
        return _format_search_results(result)

    except SlackApiError as e:
        logger.error(f"Slack API error during search: {e.response['error']}")
        return f"Slack API error: {e.response['error']}"
    except Exception as e:
        logger.error(f"Unexpected error during Slack search: {str(e)}")
        return f"Error searching Slack: {str(e)}"

def _format_search_results(result: SlackSearchResult) -> str:
    """Internal helper to format search results as a string.

    Args:
        result: SlackSearchResult object to format

    Returns:
        Formatted string with search results
    """
    if result.total == 0:
        return f"No messages found for query: '{result.query}'"

    # Format results for LLM
    output_lines = [
        f"Found {result.total} messages for query: '{result.query}'",
        f"Showing top {len(result.matches)} results:\n"
    ]

    for i, match in enumerate(result.matches, 1):
        user = match.get('user', 'Unknown')
        channel = match.get('channel', {}).get('name', 'unknown-channel')
        text = match.get('text', '')[:200] + ('...' if len(match.get('text', '')) > 200 else '')
        timestamp = match.get('ts', '')
        permalink = match.get('permalink', '')

        # Format each result
        result_text = f"{i}. #{channel} - @{user}"
        if timestamp:
            try:
                dt = datetime.fromtimestamp(float(timestamp))
                result_text += f" ({dt.strftime('%Y-%m-%d %H:%M')})"
            except:
                pass

        result_text += f"\n   {text}"
        if permalink:
            result_text += f"\n   Link: {permalink}"

        output_lines.append(result_text + "\n")

    if result.has_more:
        output_lines.append(f"... and {result.total - len(result.matches)} more results")

    return "\n".join(output_lines)


def get_thread_messages(params: ThreadInput) -> List[Dict[str, Any]]:
    """Get all messages from a Slack thread given its URL.
    
    Args:
        thread_url: URL of the Slack thread to fetch messages from
        
    Returns:
        List of message dictionaries containing message text, user, timestamp etc.
        
    Raises:
        ValueError: If SLACK_USER_TOKEN environment variable is not set or URL is invalid
        SlackApiError: If the Slack API request fails
    """

    thread_url = params.thread_url 
    # Get API token from environment variable
    slack_token = os.getenv("SLACK_USER_TOKEN")
    if not slack_token:
        raise ValueError("SLACK_USER_TOKEN environment variable is required")

    # Validate that it's a user token
    if not slack_token.startswith("xoxp-"):
        raise ValueError("Invalid token type. API requires a User Token starting with 'xoxp-'")

    # Initialize Slack client
    client = WebClient(token=slack_token)

    try:
        # Extract channel ID and thread timestamp from URL
        # URLs are in format: https://xxx.slack.com/archives/CHANNEL_ID/p1234567890123456
        url_parts = thread_url.split('/')
        if len(url_parts) < 6:
            raise ValueError("Invalid Slack thread URL format")
            
        channel_id = url_parts[-2]
        thread_ts = url_parts[-1][1:10] + '.' + url_parts[-1][10:]

        # Get thread messages
        response = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts
        )

        messages = response.get("messages", [])
        
        # Log thread information
        logger.debug(f"Retrieved {len(messages)} messages from thread")
        
        # Return simplified message data
        thread_messages = []
        for msg in messages:
            thread_messages.append({
                "text": msg.get("text"),
                "user": msg.get("user"),
                "timestamp": msg.get("ts"),
                "reply_count": msg.get("reply_count", 0),
                "reply_users_count": msg.get("reply_users_count", 0)
            })

        logger.debug(f"Returning {len(thread_messages)} formatted messages")
        return thread_messages

    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving thread messages: {str(e)}")
        raise
