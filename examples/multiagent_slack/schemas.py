from pydantic import BaseModel
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class ChannelSchema:
    """Schema for channel exploration queries."""
    include_archived: bool = False
    #include_private: bool = False

@dataclass
class SearchSchema:
    """Schema for Slack search queries."""
    query: str
    channel: Optional[str] = None
    time_range: Optional[str] = None
    limit: Optional[int] = None

@dataclass
class ThreadSchema:
    """Schema for thread analysis queries."""
    thread_url: str
    thread_ts: Optional[str] = None
    channel_id: Optional[str] = None

@dataclass
class SlackQuerySchema:
    """Schema for main Slack agent queries."""
    query_type: str  # "search", "channel", or "thread"
    topic: Optional[str] = None
    time_range: Optional[str] = None
    channel: Optional[str] = None
    url: Optional[str] = None