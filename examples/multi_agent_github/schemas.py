from typing import Optional
from dataclasses import dataclass

@dataclass
class RepositorySchema:
    """Schema for repository retrieval queries using get_repos."""
    organization: str
    type: str = "public"
    sort: str = "updated"  # created, updated, pushed, full_name
    direction: str = "desc"  # asc, desc
    
@dataclass
class CodeSearchSchema:
    """Schema for code search queries."""
    query: str = ""
    organization: Optional[str] = None
    repository: Optional[str] = None
    language: Optional[str] = None
    filename: Optional[str] = None
    path: Optional[str] = None
    
@dataclass
class IssueSearchSchema:
    """Schema for issue and PR search queries."""
    query: str
    organization: Optional[str] = None
    repository: Optional[str] = None
    state: str = "all"

@dataclass
class FileDownloadSchema:
    """Schema for downloading source code files from GitHub."""
    repository: str  # Format: "owner/repo" 
    file_path: str
    branch: str = "main"