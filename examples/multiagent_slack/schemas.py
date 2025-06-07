from typing import Optional
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