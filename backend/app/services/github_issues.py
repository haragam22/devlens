"""
Phase 6: The "Good First Issue" Matcher
Fetches OPEN issues labeled as beginner-friendly, and checks their timeline
to flag if an active Pull Request is already addressing them.
"""

import logging
import httpx
from typing import Dict, Any, List

from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import get_settings

logger = logging.getLogger(__name__)


# ── Fetch a single issue by number (REST API) ─────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def fetch_issue_by_number(
    owner: str, repo: str, issue_number: int
) -> Dict[str, Any]:
    """
    Fetch a single GitHub issue by its number using the REST API.
    Returns { number, title, body, labels, state, url }.
    Raises on HTTP errors (404 if issue doesn't exist, etc.).
    """
    settings = get_settings()

    headers: Dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "DevLens-REST-Client",
    }
    if settings.github_pat:
        headers["Authorization"] = f"Bearer {settings.github_pat}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}",
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    labels = [
        lbl["name"] if isinstance(lbl, dict) else str(lbl)
        for lbl in data.get("labels", [])
    ]

    return {
        "number": data.get("number", issue_number),
        "title": data.get("title", ""),
        "body": data.get("body", "") or "",
        "labels": labels,
        "state": data.get("state", "open"),
        "url": data.get("html_url", ""),
    }


# Single-shot GraphQL to get open beginner issues and their cross-referenced Pull Requests
GRAPHQL_ISSUES_QUERY = """
query GetBeginnerIssues($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    issues(first: 20, states: OPEN, labels: ["good first issue", "beginner", "help wanted"], orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        number
        title
        url
        body
        timelineItems(first: 5, itemTypes: CROSS_REFERENCED_EVENT) {
          nodes {
            ... on CrossReferencedEvent {
              source {
                ... on PullRequest {
                  state
                  url
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def fetch_beginner_issues(owner: str, repo: str) -> List[Dict[str, Any]]:
    """
    Fetches up to 20 beginner-friendly issues.
    Checks if there's an OPEN PR referencing them to flag them as 'In Progress'.
    """
    settings = get_settings()
    
    headers = {
        "Authorization": f"Bearer {settings.github_pat}",
        "Content-Type": "application/json",
        "User-Agent": "DevLens-GraphQL-Client"
    }

    variables = {
        "owner": owner,
        "repo": repo
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://api.github.com/graphql",
            headers=headers,
            json={"query": GRAPHQL_ISSUES_QUERY, "variables": variables}
        )
        
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            raise ValueError(f"GitHub GraphQL returned errors: {data['errors'][0].get('message')}")

        repo_data = data.get("data", {}).get("repository")
        if not repo_data:
            return []

        issues_nodes = repo_data.get("issues", {}).get("nodes", [])
        
        formatted_issues = []
        for issue in issues_nodes:
            if not issue:
                continue
            
            in_progress = False
            active_prs = []
            
            # Check timeline items for CrossReferencedEvent involving an OPEN PullRequest
            timeline = issue.get("timelineItems", {}).get("nodes", [])
            for event in timeline:
                if not event:
                    continue
                source = event.get("source")
                if source and source.get("state") == "OPEN":
                    in_progress = True
                    active_prs.append(source.get("url"))
                    
            formatted_issues.append({
                "number": issue.get("number"),
                "title": issue.get("title"),
                "url": issue.get("url"),
                "body_preview": issue.get("body", "")[:200] + "..." if issue.get("body") else "",
                "in_progress": in_progress,
                "active_prs": active_prs
            })
            
        return formatted_issues
