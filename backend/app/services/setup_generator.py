"""
Phase 5: Automated Onboarding
Generates setup scripts (Bash/PowerShell) based on detected configuration files
in the root directory of the repository.
"""

import os
from pathlib import Path
from typing import Dict

def generate_setup_script(clone_path: str) -> Dict[str, str]:
    """
    Scans the repository root for common manifest files and generates
    basic setup scripts for Bash and PowerShell.
    """
    root = Path(clone_path)
    
    # Detect features
    has_package_json = (root / "package.json").exists()
    has_yarn_lock = (root / "yarn.lock").exists()
    has_pnpm_lock = (root / "pnpm-lock.yaml").exists()
    
    has_requirements_txt = (root / "requirements.txt").exists()
    has_pipfile = (root / "Pipfile").exists()
    has_pyproject = (root / "pyproject.toml").exists()
    
    has_cargo = (root / "Cargo.toml").exists()
    has_go_mod = (root / "go.mod").exists()
    has_docker = (root / "Dockerfile").exists()
    has_docker_compose = (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists()

    bash_lines = ["#!/bin/bash", "echo 'Setting up project environment...'"]
    ps1_lines = ["Write-Host 'Setting up project environment...'"]
    
    # Node.js
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

    # Python
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

    # Rust
    if has_cargo:
        bash_lines.append("cargo build")
        ps1_lines.append("cargo build")

    # Go
    if has_go_mod:
        bash_lines.append("go mod download\ngo build ./...")
        ps1_lines.append("go mod download\ngo build ./...")

    # Docker
    if has_docker_compose:
        bash_lines.append("docker-compose up -d")
        ps1_lines.append("docker-compose up -d")
    elif has_docker:
        bash_lines.append("docker build -t devlens-app .\ndocker run -p 8080:8080 devlens-app")
        ps1_lines.append("docker build -t devlens-app .\ndocker run -p 8080:8080 devlens-app")

    if len(bash_lines) == 2:
        bash_lines.append("echo 'No standard configuration files detected.'")
        ps1_lines.append("Write-Host 'No standard configuration files detected.'")

    # ── Phase 8: Safety warnings ──
    safety_warnings: list[str] = []
    safety_warnings.append("Make sure you have git installed (run 'git --version' to check).")

    # Detect Python version from pyproject.toml
    if has_pyproject:
        try:
            pyproject_text = (root / "pyproject.toml").read_text(errors="replace")
            import re
            # Look for requires-python = ">=3.10" or python = "^3.10" etc.
            match = re.search(r'(?:requires-python|python)\s*=\s*["\']([^"\']+)["\']', pyproject_text)
            if match:
                safety_warnings.append(
                    f"This project requires Python {match.group(1)}. "
                    "Check your version with 'python --version' before proceeding."
                )
        except Exception:
            pass

    # Detect Node version from .nvmrc
    if (root / ".nvmrc").exists():
        try:
            node_version = (root / ".nvmrc").read_text().strip()
            safety_warnings.append(
                f"This project expects Node.js {node_version}. "
                "Check your version with 'node --version'."
            )
        except Exception:
            pass

    # Detect Node version from package.json engines
    if has_package_json:
        try:
            import json
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
