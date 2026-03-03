"""
Phase 8, Feature 1: The "Gatekeeper" — Repo Health Audit

Pre-ingestion check that evaluates a repository's feasibility for beginners:
  1. Liveness   — is the repo actively maintained?
  2. Traffic    — how many open PRs (competition)?
  3. Complexity — how many dependencies?
"""

import logging
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings

logger = logging.getLogger(__name__)


class GatekeeperVerdict(BaseModel):
    repo_id: str
    liveness: str           # "active" | "stale" | "dead"
    last_push: str          # ISO date string
    days_since_push: int
    open_prs: int
    competition: str        # "low" | "medium" | "high"
    dependency_count: int
    complexity: str         # "beginner" | "intermediate" | "expert"
    verdict: str            # "✅ Beginner Friendly" | "🟡 Moderate" | "🔴 Not Recommended"
    warnings: list[str]


def _github_headers() -> dict[str, str]:
    settings = get_settings()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_pat:
        headers["Authorization"] = f"Bearer {settings.github_pat}"
    return headers


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPStatusError),
    reraise=True,
)
async def audit_repository(owner: str, repo: str) -> GatekeeperVerdict:
    """
    Run all health checks against a GitHub repository and return a verdict.
    """
    repo_id = f"{owner}/{repo}"
    warnings: list[str] = []
    headers = _github_headers()

    async with httpx.AsyncClient(timeout=20.0) as client:
        # ── 1. Fetch repo metadata (liveness + basic info) ──
        repo_resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
        )
        repo_resp.raise_for_status()
        repo_data = repo_resp.json()

        # ── 2. Count open PRs (traffic/competition check) ──
        pr_resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            params={"state": "open", "per_page": 1},
            headers=headers,
        )
        pr_resp.raise_for_status()
        # GitHub returns total count in the repo data as open_issues_count
        # but that includes issues too. Use the Link header for PR count.
        # Simpler: just use repo_data open_issues as a proxy, or count PRs
        open_prs = repo_data.get("open_issues_count", 0)  # includes issues

        # Try to get actual PR count from a separate request
        try:
            search_resp = await client.get(
                f"https://api.github.com/search/issues",
                params={"q": f"repo:{owner}/{repo} is:pr is:open", "per_page": 1},
                headers=headers,
            )
            if search_resp.status_code == 200:
                open_prs = search_resp.json().get("total_count", open_prs)
        except Exception:
            pass  # fallback to open_issues_count

        # ── 3. Complexity check — try to read package.json or requirements.txt ──
        dependency_count = 0

        # Try package.json
        try:
            pkg_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/package.json",
                headers=headers,
            )
            if pkg_resp.status_code == 200:
                import base64
                import json
                content = base64.b64decode(pkg_resp.json().get("content", "")).decode()
                pkg = json.loads(content)
                deps = pkg.get("dependencies", {})
                dev_deps = pkg.get("devDependencies", {})
                dependency_count = len(deps) + len(dev_deps)
        except Exception:
            pass

        # Try requirements.txt if no package.json deps found
        if dependency_count == 0:
            try:
                req_resp = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/contents/requirements.txt",
                    headers=headers,
                )
                if req_resp.status_code == 200:
                    import base64
                    content = base64.b64decode(req_resp.json().get("content", "")).decode()
                    lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
                    dependency_count = len(lines)
            except Exception:
                pass

    # ── Evaluate checks ──

    # Liveness
    pushed_at_str = repo_data.get("pushed_at", "")
    try:
        pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
        days_since = (datetime.now(timezone.utc) - pushed_at).days
    except Exception:
        days_since = 9999
        pushed_at_str = "unknown"

    if days_since > 365:
        liveness = "dead"
        warnings.append(f"🔴 Last push was {days_since} days ago — this repo appears abandoned.")
    elif days_since > 180:
        liveness = "stale"
        warnings.append(f"🟡 Last push was {days_since} days ago — repo may be inactive.")
    else:
        liveness = "active"

    # Competition
    if open_prs > 50:
        competition = "high"
        warnings.append(f"🟡 {open_prs} open PRs — high competition for contributions.")
    elif open_prs > 20:
        competition = "medium"
        warnings.append(f"🟡 {open_prs} open PRs — moderate competition.")
    else:
        competition = "low"

    # Complexity
    if dependency_count > 500:
        complexity = "expert"
        warnings.append(f"🔴 {dependency_count} dependencies — expert-level complexity.")
    elif dependency_count > 100:
        complexity = "intermediate"
        warnings.append(f"🟡 {dependency_count} dependencies — intermediate complexity.")
    else:
        complexity = "beginner"

    # ── Final verdict ──
    red_flags = sum(1 for w in warnings if "🔴" in w)
    yellow_flags = sum(1 for w in warnings if "🟡" in w)

    if red_flags >= 1:
        verdict = "🔴 Not Recommended for Beginners"
    elif yellow_flags >= 2:
        verdict = "🟡 Moderate — Proceed with Caution"
    elif yellow_flags == 1:
        verdict = "🟡 Mostly Friendly — One Concern"
    else:
        verdict = "✅ Beginner Friendly"

    return GatekeeperVerdict(
        repo_id=repo_id,
        liveness=liveness,
        last_push=pushed_at_str,
        days_since_push=days_since,
        open_prs=open_prs,
        competition=competition,
        dependency_count=dependency_count,
        complexity=complexity,
        verdict=verdict,
        warnings=warnings,
    )
