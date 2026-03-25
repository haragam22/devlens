"""
Phase 5: Automated Onboarding
Generates setup scripts (Bash/PowerShell) based on detected configuration files
in the root directory of the repository.

Uses the LLM to produce repo-specific instructions when README/CONTRIBUTING
docs are available, with a template-based fallback.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

# ── Files we try to read for LLM context ──────────────────────────────────
_DOC_FILES = ["README.md", "readme.md", "CONTRIBUTING.md", "contributing.md"]
_CONFIG_FILES = [
    "package.json", "requirements.txt", "Pipfile", "pyproject.toml",
    "Cargo.toml", "go.mod", "Makefile", "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml", ".env.example",
]


def _safe_read(path: Path, max_chars: int = 3000) -> str:
    """Read file text, truncating to max_chars. Returns '' on failure."""
    try:
        return path.read_text(errors="replace")[:max_chars]
    except Exception:
        return ""


def _gather_repo_context(root: Path) -> str:
    """
    Read documentation + config files from the repo root and build a
    compact context string for the LLM.
    """
    parts: list[str] = []

    # Documentation files (full content, higher char limit)
    for name in _DOC_FILES:
        p = root / name
        if p.exists():
            content = _safe_read(p, max_chars=4000)
            if content:
                parts.append(f"=== {name} ===\n{content}")

    # Config / manifest files (smaller limit — we mainly need structure)
    for name in _CONFIG_FILES:
        p = root / name
        if p.exists():
            content = _safe_read(p, max_chars=1500)
            if content:
                parts.append(f"=== {name} ===\n{content}")

    # .nvmrc, .node-version, .python-version — tiny files
    for tiny in [".nvmrc", ".node-version", ".python-version", ".tool-versions"]:
        p = root / tiny
        if p.exists():
            content = _safe_read(p, max_chars=200)
            if content:
                parts.append(f"=== {tiny} ===\n{content}")

    return "\n\n".join(parts)


# ── LLM-powered setup generation ──────────────────────────────────────────

_SETUP_SYSTEM_PROMPT = """\
You are DevLens Setup Assistant.
Given the contents of a repository's README, CONTRIBUTING guide, and config files,
generate PRECISE, REPO-SPECIFIC setup instructions as ready-to-paste terminal commands.

RULES:
1. Read the provided files carefully. Extract the EXACT commands the project documents.
2. If the README/CONTRIBUTING file has a "Getting Started" or "Development Setup" section, use those commands verbatim.
3. Include environment variable setup if .env.example exists (list the vars, tell user to fill them).
4. Include language/runtime version requirements if detected.
5. Do NOT hallucinate commands — only include commands supported by the detected config files.
6. Keep it concise: just the commands + brief comments, no essays.

OUTPUT FORMAT — return ONLY a JSON object with these keys:
{
  "bash": "#!/bin/bash\\n# line-by-line bash commands",
  "powershell": "# line-by-line PowerShell commands",
  "safety_warnings": ["warning 1", "warning 2"]
}
Do NOT wrap in markdown code blocks. Return raw JSON only."""


async def _llm_setup(repo_context: str) -> Dict[str, str] | None:
    """Ask the LLM to generate repo-specific setup scripts. Returns None on failure."""
    from app.services.bedrock_client import call_claude

    if not repo_context.strip():
        return None

    user_msg = (
        "Here are the files from the repository root. "
        "Generate precise setup scripts based on this information.\n\n"
        f"{repo_context}"
    )

    try:
        raw = await call_claude(_SETUP_SYSTEM_PROMPT, user_msg, max_tokens=1500)
        cleaned = raw.strip()
        # Strip markdown code fences if the LLM wraps them
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:-1])
        data = json.loads(cleaned)
        # Validate expected keys
        if "bash" in data and "powershell" in data:
            if "safety_warnings" not in data:
                data["safety_warnings"] = []
            return data
    except Exception as exc:
        logger.warning("LLM setup generation failed: %s — falling back to templates", exc)

    return None


# ── Template-based fallback (original logic) ───────────────────────────────

def _template_setup(root: Path) -> Dict[str, str]:
    """Generate generic setup scripts using file-existence checks (fallback)."""
    has_package_json = (root / "package.json").exists()
    has_yarn_lock = (root / "yarn.lock").exists()
    has_pnpm_lock = (root / "pnpm-lock.yaml").exists()

    has_requirements_txt = (root / "requirements.txt").exists()
    has_pipfile = (root / "Pipfile").exists()
    has_pyproject = (root / "pyproject.toml").exists()

    has_cargo = (root / "Cargo.toml").exists()
    has_go_mod = (root / "go.mod").exists()
    has_docker = (root / "Dockerfile").exists()
    has_docker_compose = (
        (root / "docker-compose.yml").exists()
        or (root / "docker-compose.yaml").exists()
    )

    bash_lines = ["#!/bin/bash", "echo 'Setting up project environment...'"]
    ps1_lines = ["Write-Host 'Setting up project environment...'"]

    if has_package_json:
        if has_pnpm_lock:
            bash_lines.append("pnpm install")
            ps1_lines.append("pnpm install")
        elif has_yarn_lock:
            bash_lines.append("yarn install")
            ps1_lines.append("yarn install")
        else:
            bash_lines.append("npm install")
            ps1_lines.append("npm install")

    if has_requirements_txt or has_pipfile or has_pyproject:
        bash_lines.append("python3 -m venv .venv")
        bash_lines.append("source .venv/bin/activate")
        ps1_lines.append("python -m venv .venv")
        ps1_lines.append(".\\.venv\\Scripts\\Activate.ps1")
        if has_pipfile:
            bash_lines.append("pip install pipenv && pipenv install")
            ps1_lines.append("pip install pipenv; pipenv install")
        elif has_pyproject:
            bash_lines.append("pip install -e .")
            ps1_lines.append("pip install -e .")
        elif has_requirements_txt:
            bash_lines.append("pip install -r requirements.txt")
            ps1_lines.append("pip install -r requirements.txt")

    if has_cargo:
        bash_lines.append("cargo build")
        ps1_lines.append("cargo build")

    if has_go_mod:
        bash_lines.append("go mod download\ngo build ./...")
        ps1_lines.append("go mod download\ngo build ./...")

    if has_docker_compose:
        bash_lines.append("docker-compose up -d")
        ps1_lines.append("docker-compose up -d")
    elif has_docker:
        bash_lines.append("docker build -t devlens-app .\ndocker run -p 8080:8080 devlens-app")
        ps1_lines.append("docker build -t devlens-app .\ndocker run -p 8080:8080 devlens-app")

    if len(bash_lines) == 2:
        bash_lines.append("echo 'No standard configuration files detected.'")
        ps1_lines.append("Write-Host 'No standard configuration files detected.'")

    # Safety warnings
    safety_warnings: list[str] = [
        "Make sure you have git installed (run 'git --version' to check)."
    ]

    if has_pyproject:
        try:
            pyproject_text = (root / "pyproject.toml").read_text(errors="replace")
            match = re.search(
                r'(?:requires-python|python)\s*=\s*["\'](.*?)["\']', pyproject_text
            )
            if match:
                safety_warnings.append(
                    f"This project requires Python {match.group(1)}. "
                    "Check your version with 'python --version' before proceeding."
                )
        except Exception:
            pass

    if (root / ".nvmrc").exists():
        try:
            node_version = (root / ".nvmrc").read_text().strip()
            safety_warnings.append(
                f"This project expects Node.js {node_version}. "
                "Check your version with 'node --version'."
            )
        except Exception:
            pass

    if has_package_json:
        try:
            pkg = json.loads((root / "package.json").read_text(errors="replace"))
            engines = pkg.get("engines", {})
            if "node" in engines:
                safety_warnings.append(
                    f"package.json requires Node.js {engines['node']}. "
                    "Check your version with 'node --version'."
                )
        except Exception:
            pass

    return {
        "bash": "\n".join(bash_lines),
        "powershell": "\n".join(ps1_lines),
        "safety_warnings": safety_warnings,
    }


# ── Public entry point ────────────────────────────────────────────────────

async def generate_setup_script(clone_path: str) -> Dict[str, str]:
    """
    Generate setup scripts for a cloned repository.
    Tries LLM-powered generation first (reads README, CONTRIBUTING, config files),
    falls back to template-based detection on failure.
    """
    root = Path(clone_path)

    # Gather context from the repo
    context = _gather_repo_context(root)

    # Try LLM-powered generation
    if context:
        result = await _llm_setup(context)
        if result:
            return result

    # Fallback to template-based
    return _template_setup(root)
