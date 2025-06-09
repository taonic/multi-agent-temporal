import os
import logging
import base64
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

from github import Github, GithubException
from github.Repository import Repository
from github.ContentFile import ContentFile

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class GitHubRepoRequest:
    """Request parameters for getting GitHub repositories from an organization"""
    organization: str
    type: str = "public"
    sort: str = "updated"  # created, updated, pushed, full_name
    direction: str = "desc"  # asc, desc
    per_page: int = 30

@dataclass
class GitHubCodeSearchRequest:
    """Request parameters for searching code in GitHub repositories"""
    query: str
    organization: Optional[str] = None
    repository: Optional[str] = None
    language: Optional[str] = None
    filename: Optional[str] = None
    path: Optional[str] = None
    per_page: int = 30

def _get_github_client() -> Github:
    """Get authenticated GitHub client."""
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        return Github(github_token)
    else:
        # Use unauthenticated access (lower rate limits)
        return Github()

def get_repos(request: GitHubRepoRequest) -> str:
    """Get repositories from a GitHub organization using the organization's repos endpoint.

    Args:
        request: GitHubRepoRequest containing parameters for the repository request

    Returns:
        Formatted string with repository results
    """
    try:
        g = _get_github_client()
        
        logger.debug(f"Getting repositories for organization: '{request.organization}'")
        
        try:
            # Get the organization
            org = g.get_organization(request.organization)
            
            # Get repositories using the organization's get_repos method
            repositories = org.get_repos(
                type=request.type,
                sort=request.sort,
                direction=request.direction
            )
            
            # Get limited results safely
            repo_list = []
            count = 0
            try:
                for repo in repositories:
                    if count >= request.per_page:
                        break
                    repo_list.append(repo)
                    count += 1
            except Exception as iter_e:
                logger.warning(f"Error iterating repositories: {str(iter_e)}")
                # If we have some results, use them
                if not repo_list:
                    raise iter_e
            
            if not repo_list:
                return f"No repositories found for organization '{request.organization}'. The organization may not exist or have no accessible repositories."
            
            # Format results
            output_lines = [
                f"Found repositories for organization '{request.organization}'",
                f"Showing {len(repo_list)} repositories (sorted by {request.sort}, {request.direction}):\n"
            ]
            
            for i, repo in enumerate(repo_list, 1):
                try:
                    name = repo.name
                    full_name = repo.full_name
                    description = repo.description or "No description"
                    language = repo.language or "Unknown"
                    stars = repo.stargazers_count
                    forks = repo.forks_count
                    url = repo.html_url
                    updated = repo.updated_at.strftime('%Y-%m-%d') if repo.updated_at else 'Unknown'
                    
                    result_text = f"{i}. **{name}** ({full_name})"
                    result_text += f"\n   Language: {language} | Stars: {stars} | Forks: {forks}"
                    result_text += f"\n   Last Updated: {updated}"
                    result_text += f"\n   Description: {description[:150]}{'...' if len(description) > 150 else ''}"
                    result_text += f"\n   URL: {url}\n"
                    
                    output_lines.append(result_text)
                except Exception as repo_e:
                    logger.warning(f"Error processing repository {i}: {str(repo_e)}")
                    continue
            
            return "\n".join(output_lines)
            
        except GithubException as org_e:
            if org_e.status == 404:
                # Try as a user instead of organization
                try:
                    logger.debug(f"Organization not found, trying as user: '{request.organization}'")
                    user = g.get_user(request.organization)
                    
                    # Get repositories using the user's get_repos method
                    repositories = user.get_repos(
                        type=request.type,
                        sort=request.sort,
                        direction=request.direction
                    )
                    
                    # Get limited results safely
                    repo_list = []
                    count = 0
                    try:
                        for repo in repositories:
                            if count >= request.per_page:
                                break
                            repo_list.append(repo)
                            count += 1
                    except Exception as iter_e:
                        logger.warning(f"Error iterating user repositories: {str(iter_e)}")
                        if not repo_list:
                            raise iter_e
                    
                    if not repo_list:
                        return f"No repositories found for user '{request.organization}'. The user may not exist or have no accessible repositories."
                    
                    # Format results
                    output_lines = [
                        f"Found repositories for user '{request.organization}'",
                        f"Showing {len(repo_list)} repositories (sorted by {request.sort}, {request.direction}):\n"
                    ]
                    
                    for i, repo in enumerate(repo_list, 1):
                        try:
                            name = repo.name
                            full_name = repo.full_name
                            description = repo.description or "No description"
                            language = repo.language or "Unknown"
                            stars = repo.stargazers_count
                            forks = repo.forks_count
                            url = repo.html_url
                            updated = repo.updated_at.strftime('%Y-%m-%d') if repo.updated_at else 'Unknown'
                            
                            result_text = f"{i}. **{name}** ({full_name})"
                            result_text += f"\n   Language: {language} | Stars: {stars} | Forks: {forks}"
                            result_text += f"\n   Last Updated: {updated}"
                            result_text += f"\n   Description: {description[:150]}{'...' if len(description) > 150 else ''}"
                            result_text += f"\n   URL: {url}\n"
                            
                            output_lines.append(result_text)
                        except Exception as repo_e:
                            logger.warning(f"Error processing repository {i}: {str(repo_e)}")
                            continue
                    
                    return "\n".join(output_lines)
                    
                except GithubException as user_e:
                    if user_e.status == 404:
                        return f"Neither organization nor user '{request.organization}' found on GitHub. Please verify the name."
                    else:
                        raise user_e
            else:
                raise org_e
        
    except GithubException as e:
        logger.error(f"GitHub API error during repository retrieval: {e.status} - {getattr(e, 'data', {})}")
        if e.status == 403:
            return f"GitHub API rate limit exceeded. Without a GITHUB_TOKEN, you're limited to 60 requests/hour. Please add a GITHUB_TOKEN environment variable for 5,000 requests/hour, or try again later."
        elif e.status == 401:
            return "GitHub API authentication failed. Please check your GITHUB_TOKEN."
        else:
            return f"GitHub API error: {getattr(e, 'data', {}).get('message', str(e))}"
    except Exception as e:
        logger.error(f"Unexpected error during repository retrieval: {str(e)}")
        return f"Error retrieving repositories: {str(e)}"

def search_github_code(request: GitHubCodeSearchRequest) -> str:
    """Search for code in GitHub repositories.

    Args:
        request: GitHubCodeSearchRequest containing search parameters

    Returns:
        Formatted string with code search results
    """
    try:
        g = _get_github_client()
        
        # Build search query
        query_parts = [request.query]
        
        if request.organization:
            query_parts.append(f"org:{request.organization}")
        
        if request.repository:
            query_parts.append(f"repo:{request.organization}/{request.repository}")
        
        if request.language:
            query_parts.append(f"language:{request.language}")
            
        if request.filename:
            query_parts.append(f"filename:{request.filename}")
            
        if request.path:
            query_parts.append(f"path:{request.path}")
        
        search_query = " ".join(query_parts)
        
        logger.debug(f"GitHub code search query: '{search_query}'")
        
        # Search code - note that code search requires authentication
        code_results = g.search_code(query=search_query)
        
        # Get limited results safely with proper pagination handling
        code_list = []
        count = 0
        try:
            for result in code_results:
                if count >= request.per_page:
                    break
                code_list.append(result)
                count += 1
        except Exception as iter_e:
            logger.warning(f"Error iterating code results: {str(iter_e)}")
            # If we have some results, use them
            if not code_list:
                raise iter_e
        
        # Get total count safely
        try:
            total_count = code_results.totalCount
        except Exception:
            total_count = len(code_list)
        
        if not code_list:
            return f"No code found for query: '{search_query}'"
        
        # Format results
        output_lines = [
            f"Found {total_count} code matches for query: '{search_query}'",
            f"Showing top {len(code_list)} results:\n"
        ]
        
        for i, result in enumerate(code_list, 1):
            try:
                name = result.name
                path = result.path
                repo_name = result.repository.full_name
                html_url = result.html_url
                
                # Try to get a snippet of the content
                snippet = ""
                try:
                    # Get file content for snippet
                    content = result.decoded_content.decode('utf-8')
                    lines = content.split('\n')
                    # Show first few lines or around the match if possible
                    snippet_lines = lines[:5]  # First 5 lines as preview
                    snippet = '\n'.join(snippet_lines)
                    if len(lines) > 5:
                        snippet += "\n..."
                except Exception as content_e:
                    logger.debug(f"Could not get content preview for {name}: {str(content_e)}")
                    snippet = "Content preview unavailable"
                
                result_text = f"{i}. **{name}** in {repo_name}"
                result_text += f"\n   Path: {path}"
                result_text += f"\n   Code preview:\n```\n{snippet[:300]}{'...' if len(snippet) > 300 else ''}\n```"
                result_text += f"\n   URL: {html_url}\n"
                
                output_lines.append(result_text)
                
            except Exception as result_e:
                logger.warning(f"Error processing code result {i}: {str(result_e)}")
                # Add a basic entry even if we can't get all details
                try:
                    basic_info = f"{i}. Code result (details unavailable)\n   URL: {result.html_url}\n"
                    output_lines.append(basic_info)
                except Exception:
                    continue
        
        return "\n".join(output_lines)
        
    except GithubException as e:
        logger.error(f"GitHub API error during code search: {e.status} - {getattr(e, 'data', {})}")
        if e.status == 403:
            return "GitHub code search requires authentication and has rate limits. Please add a GITHUB_TOKEN environment variable."
        elif e.status == 401:
            return "GitHub API authentication failed. Code search requires a valid GITHUB_TOKEN."
        elif e.status == 422:
            return f"Invalid code search query. Try using simpler search terms or add organization/repository filters."
        else:
            return f"GitHub API error: {getattr(e, 'data', {}).get('message', str(e))}"
    except Exception as e:
        logger.error(f"Unexpected error during code search: {str(e)}")
        return f"Error searching code: {str(e)}"

def download_github_file(request) -> str:
    """Download source code file from GitHub repository.

    Args:
        request: FileDownloadSchema containing repository, file path, and branch

    Returns:
        The file content as a string, or error message if download fails
    """
    try:
        g = _get_github_client()
        
        # Handle both dict and object inputs
        if isinstance(request, dict):
            repository = request.get('repository')
            file_path = request.get('file_path')
            branch = request.get('branch', 'main')
        else:
            repository = getattr(request, 'repository', None)
            file_path = getattr(request, 'file_path', None)
            branch = getattr(request, 'branch', 'main')
        
        # Validate required parameters
        if not repository:
            return "Error: repository parameter is required"
        if not file_path:
            return "Error: file_path parameter is required"
        
        # Get the repository
        try:
            repo = g.get_repo(repository)
        except GithubException as repo_e:
            if repo_e.status == 404:
                return f"Repository '{repository}' not found. Please check the repository name and ensure it's public or you have access."
            else:
                return f"Error accessing repository '{repository}': {getattr(repo_e, 'data', {}).get('message', str(repo_e))}"
        
        logger.debug(f"Downloading file '{file_path}' from '{repository}' branch '{branch}'")
        
        try:
            # Get file content from the specified branch
            file_content = repo.get_contents(file_path, ref=branch)
            
            # Handle if it's a file (not a directory)
            if isinstance(file_content, list):
                return f"Error: '{file_path}' is a directory, not a file. Please specify a file path."
            
            # Decode the content
            if file_content.encoding == 'base64':
                try:
                    decoded_content = base64.b64decode(file_content.content).decode('utf-8')
                except UnicodeDecodeError:
                    # Try with different encodings for binary files
                    try:
                        decoded_content = base64.b64decode(file_content.content).decode('latin1')
                        return f"File '{file_path}' appears to be binary. First 500 chars:\n\n{decoded_content[:500]}..."
                    except Exception:
                        return f"Error: '{file_path}' appears to be a binary file that cannot be displayed as text."
            else:
                decoded_content = file_content.content
            
            # Add file metadata
            file_info = f"# File: {file_path}\n"
            file_info += f"# Repository: {repository}\n"
            file_info += f"# Branch: {branch}\n"
            file_info += f"# Size: {file_content.size} bytes\n"
            file_info += f"# Last modified: {file_content.last_modified}\n"
            file_info += f"# URL: {file_content.html_url}\n\n"
            
            # Limit very large files
            if len(decoded_content) > 50000:  # 50KB limit
                file_info += f"# Note: File is large ({len(decoded_content)} chars), showing first 50,000 characters\n\n"
                decoded_content = decoded_content[:50000] + "\n\n... [File truncated - download full file from URL above]"
            
            return file_info + decoded_content
            
        except GithubException as file_e:
            if file_e.status == 404:
                # Try common branch alternatives if main/master doesn't work
                if branch == "main":
                    logger.debug(f"File not found on 'main' branch, trying 'master'")
                    try:
                        # Retry with master branch
                        if isinstance(request, dict):
                            master_request = request.copy()
                            master_request['branch'] = 'master'
                        else:
                            master_request = type('MasterRequest', (), {
                                'repository': repository,
                                'file_path': file_path,
                                'branch': 'master'
                            })()
                        return download_github_file(master_request)
                    except Exception:
                        pass
                elif branch == "master":
                    logger.debug(f"File not found on 'master' branch, trying 'main'")
                    try:
                        # Retry with main branch
                        if isinstance(request, dict):
                            main_request = request.copy()
                            main_request['branch'] = 'main'
                        else:
                            main_request = type('MainRequest', (), {
                                'repository': repository,
                                'file_path': file_path,
                                'branch': 'main'
                            })()
                        return download_github_file(main_request)
                    except Exception:
                        pass
                
                return f"File '{file_path}' not found in repository '{repository}' on branch '{branch}'. Please check the file path and branch name."
            else:
                return f"Error accessing file: {getattr(file_e, 'data', {}).get('message', str(file_e))}"
        
    except GithubException as e:
        logger.error(f"GitHub API error during file download: {e.status} - {getattr(e, 'data', {})}")
        if e.status == 403:
            return "GitHub API rate limit exceeded. Please add a GITHUB_TOKEN environment variable for higher limits."
        elif e.status == 401:
            return "GitHub API authentication failed. Please check your GITHUB_TOKEN."
        else:
            return f"GitHub API error: {getattr(e, 'data', {}).get('message', str(e))}"
    except Exception as e:
        logger.error(f"Unexpected error during file download: {str(e)}")
        return f"Error downloading file: {str(e)}"