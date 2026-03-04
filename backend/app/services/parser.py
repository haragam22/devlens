"""
Tree-sitter Parsing Engine
Extracts a dependency graph (nodes = files, edges = imports) from a cloned
repository. Supports Python, JavaScript, and Go out of the box.
"""

import os
import mimetypes
from pathlib import Path
from typing import NamedTuple

from pydantic import BaseModel
from tree_sitter_languages import get_language, get_parser

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Maximum individual file size (bytes) before we skip it
MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MB

# File-extension → Tree-sitter grammar name
LANG_MAP: dict[str, str] = {
    ".py":   "python",
    ".js":   "javascript",
    ".jsx":  "javascript",
    ".ts":   "typescript",
    ".tsx":  "tsx",
    ".go":   "go",
}

# Directories / patterns to always skip (mirrors common .gitignore rules)
SKIP_DIRS: set[str] = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".venv", "venv", "env", ".mypy_cache", ".pytest_cache",
    "coverage", ".next", ".nuxt", "out",
}

SKIP_EXTENSIONS: set[str] = {
    ".min.js", ".min.css", ".map", ".lock",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bin", ".exe",
}


# ---------------------------------------------------------------------------
# Pydantic output models
# ---------------------------------------------------------------------------

class Node(BaseModel):
    id: str          # relative file path, e.g. "src/utils/helpers.py"
    language: str
    size_bytes: int
    extracted_names: list[str] = []


class Edge(BaseModel):
    source: str      # relative file path of the importer
    target: str      # raw import string (e.g. "os", "./utils/helpers")
    edge_type: str = "import"


class GraphData(BaseModel):
    nodes: list[Node]
    edges: list[Edge]
    circular_deps: list[list[str]] = []   # cycles detected (Phase 1: best-effort)
    skipped_files: list[str] = []         # files that were filtered out


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _should_skip_file(path: Path, rel_path: str, size: int) -> str | None:
    """Return a skip reason string, or None if the file should be parsed."""
    # 1. Skip blacklisted directories anywhere in the path
    for part in path.parts:
        if part in SKIP_DIRS:
            return f"blacklisted dir: {part}"

    # 2. Skip by extension
    for bad_ext in SKIP_EXTENSIONS:
        if rel_path.endswith(bad_ext):
            return f"skipped extension: {bad_ext}"

    # 3. Skip files > 1 MB
    if size > MAX_FILE_BYTES:
        return f"too large: {size} bytes"

    # 4. MIME-type sniffing — skip binary files
    mime, _ = mimetypes.guess_type(str(path))
    if mime and not mime.startswith("text/"):
        return f"binary mime: {mime}"

    return None


# ---------------------------------------------------------------------------
# Tree-sitter query strings per language
# (extracts import / require statements)
# ---------------------------------------------------------------------------

_PY_IMPORT_QUERY = """
(import_statement
  name: (dotted_name) @import)
(import_from_statement
  module_name: (dotted_name) @import)
(import_from_statement
  module_name: (relative_import) @import)
"""

_JS_IMPORT_QUERY = """
(import_declaration
  source: (string) @import)
(call_expression
  function: (identifier) @fn (#eq? @fn "require")
  arguments: (arguments (string) @import))
"""

_GO_IMPORT_QUERY = """
(import_spec path: (interpreted_string_literal) @import)
"""

QUERY_MAP: dict[str, str] = {
    "python":     _PY_IMPORT_QUERY,
    "javascript": _JS_IMPORT_QUERY,
    "typescript": _JS_IMPORT_QUERY,
    "tsx":        _JS_IMPORT_QUERY,
    "go":         _GO_IMPORT_QUERY,
}

# ---------------------------------------------------------------------------
# Tree-sitter query strings per language for functions
# ---------------------------------------------------------------------------

_PY_FUNCTION_QUERY = """
(class_definition name: (identifier) @function)
(function_definition name: (identifier) @function)
"""

_JS_FUNCTION_QUERY = """
(class_declaration name: (identifier) @function)
(function_declaration name: (identifier) @function)
(method_definition name: (property_identifier) @function)
(variable_declarator name: (identifier) @function value: [(arrow_function) (function)])
"""

_GO_FUNCTION_QUERY = """
(type_spec name: (type_identifier) @function)
(function_declaration name: (identifier) @function)
(method_declaration name: (field_identifier) @function)
"""

FUNC_QUERY_MAP: dict[str, str] = {
    "python":     _PY_FUNCTION_QUERY,
    "javascript": _JS_FUNCTION_QUERY,
    "typescript": _JS_FUNCTION_QUERY,
    "tsx":        _JS_FUNCTION_QUERY,
    "go":         _GO_FUNCTION_QUERY,
}


def _extract_imports(source: bytes, lang_name: str) -> list[str]:
    """
    Extract all import/require strings from a file's source.
    Uses regex for reliability across tree-sitter grammar versions.
    """
    import re
    text = source.decode(errors="replace")
    imports: list[str] = []

    if lang_name in ("javascript", "typescript", "tsx"):
        # Match: import ... from 'xxx'  or  import 'xxx'
        for m in re.finditer(r'''import\s+.*?from\s+['"]([^'"]+)['"]''', text):
            imports.append(m.group(1))
        for m in re.finditer(r'''import\s+['"]([^'"]+)['"]''', text):
            imports.append(m.group(1))
        # Match: require('xxx')
        for m in re.finditer(r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)''', text):
            imports.append(m.group(1))

    elif lang_name == "python":
        # import foo.bar  /  from foo.bar import ...
        for m in re.finditer(r'^import\s+([\w.]+)', text, re.MULTILINE):
            imports.append(m.group(1))
        for m in re.finditer(r'^from\s+([\w.]+)\s+import', text, re.MULTILINE):
            imports.append(m.group(1))

    elif lang_name == "go":
        for m in re.finditer(r'"([^"]+)"', text):
            imports.append(m.group(1))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for imp in imports:
        if imp not in seen:
            seen.add(imp)
            unique.append(imp)
    return unique

def _extract_functions(source: bytes, lang_name: str) -> list[str]:
    """Use Tree-sitter to extract all function names from a file's source."""
    try:
        language = get_language(lang_name)
        parser = get_parser(lang_name)
        tree = parser.parse(source)
        query_src = FUNC_QUERY_MAP.get(lang_name, "")
        if not query_src:
            return []

        query = language.query(query_src)
        captures = query.captures(tree.root_node)
        functions: list[str] = []
        for node, _ in captures:
            raw = node.text.decode(errors="replace").strip()
            if raw:
                functions.append(raw)
        return functions
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Cycle detection (DFS)
# ---------------------------------------------------------------------------

class _CycleDetector:
    def __init__(self, adj: dict[str, list[str]]) -> None:
        self.adj = adj
        self.visited: set[str] = set()
        self.stack: set[str] = set()
        self.cycles: list[list[str]] = []
        self._path: list[str] = []

    def run(self) -> list[list[str]]:
        for node in self.adj:
            if node not in self.visited:
                self._dfs(node)
        return self.cycles

    def _dfs(self, node: str) -> None:
        self.visited.add(node)
        self.stack.add(node)
        self._path.append(node)

        for neighbour in self.adj.get(node, []):
            if neighbour not in self.visited:
                self._dfs(neighbour)
            elif neighbour in self.stack:
                # Found a cycle — extract it from the current path
                idx = self._path.index(neighbour)
                self.cycles.append(self._path[idx:] + [neighbour])

        self._path.pop()
        self.stack.discard(node)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _resolve_import(imp: str, source_file: str, all_node_ids: set[str]) -> str | None:
    """
    Try to resolve an import string to an actual file path present in the
    node set. Handles:
      - relative imports: './foo' or '../bar'
      - alias imports:    '@/components/Button'
      - bare module names that happen to match a node path segment
    Returns the matched node id, or None if no match found.
    """
    import posixpath

    source_dir = posixpath.dirname(source_file)

    candidates: list[str] = []

    if imp.startswith("."):
        # Relative import: resolve relative to source file's directory
        resolved = posixpath.normpath(posixpath.join(source_dir, imp))
        candidates.append(resolved)
    elif imp.startswith("@/"):
        # Common alias for src/ root
        candidates.append("src/" + imp[2:])
    else:
        # Bare import — try matching as a suffix of known node ids
        candidates.append(imp)

    # Try each candidate with common extensions
    extensions = ["", ".ts", ".tsx", ".js", ".jsx", ".py", "/index.ts", "/index.tsx", "/index.js"]
    for base in candidates:
        for ext in extensions:
            full = base + ext
            if full in all_node_ids:
                return full
    return None


def parse_repository(clone_path: str | Path) -> GraphData:
    """
    Walk the cloned repository and build a dependency graph.
    All I/O is synchronous (designed to be called in a background task).
    """
    root = Path(clone_path)
    nodes: list[Node] = []
    raw_edges: list[tuple[str, str]] = []      # (source_file, raw_import)
    skipped: list[str] = []

    # Adjacency list for cycle detection (only resolved local edges)
    adj: dict[str, list[str]] = {}

    for abs_path in root.rglob("*"):
        if not abs_path.is_file():
            continue

        ext = "".join(abs_path.suffixes)  # handles ".min.js" etc.
        if ext not in LANG_MAP:
            continue   # not a supported source language

        rel_path = str(abs_path.relative_to(root)).replace("\\", "/")
        size = abs_path.stat().st_size
        skip_reason = _should_skip_file(abs_path, rel_path, size)

        if skip_reason:
            skipped.append(f"{rel_path} [{skip_reason}]")
            continue

        lang = LANG_MAP[ext]
        nodes.append(Node(id=rel_path, language=lang, size_bytes=size))
        adj[rel_path] = []

        # Read and parse
        try:
            source = abs_path.read_bytes()
            nodes[-1].extracted_names = _extract_functions(source, lang)
        except OSError:
            skipped.append(f"{rel_path} [read error]")
            continue

        imports = _extract_imports(source, lang)
        for imp in imports:
            raw_edges.append((rel_path, imp))

    # Build set of known node ids for resolution
    node_ids = {n.id for n in nodes}

    # Resolve raw imports to actual file paths
    edges: list[Edge] = []
    for src, raw_imp in raw_edges:
        resolved = _resolve_import(raw_imp, src, node_ids)
        if resolved and resolved != src:    # skip self-imports
            edges.append(Edge(source=src, target=resolved))
            if raw_imp.startswith("."):
                adj.setdefault(src, []).append(resolved)

    # Cycle detection
    cycles = _CycleDetector(adj).run()

    return GraphData(
        nodes=nodes,
        edges=edges,
        circular_deps=cycles,
        skipped_files=skipped,
    )
