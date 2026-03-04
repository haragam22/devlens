# DevLens Backend API Documentation

> **Version:** 0.1.0  
> **Base URL:** `http://localhost:8000`  
> **Interactive Docs:** [Swagger UI](http://localhost:8000/docs) · [ReDoc](http://localhost:8000/redoc)  
> **Last Updated:** 2026-03-03

---

## Table of Contents

| # | Endpoint | Method | Phase | Description |
|---|----------|--------|-------|-------------|
| 1 | `/health` | GET | — | Health check |
| 2 | `/api/v1/repository/ingest` | POST | 1 | Clone + metadata |
| 3 | `/api/v1/repository/graph/{owner}/{repo}` | GET | 1 | Dependency graph |
| 4 | `/api/v1/repository/status/{owner}/{repo}` | GET | 1 | Parse status |
| 5 | `/api/v1/repository/vectorize` | POST | 2 | Embed code → ChromaDB |
| 6 | `/api/v1/search` | POST | 2 | Hybrid search |
| 7 | `/api/v1/explain` | POST | 2,6,8 | Jargon Buster |
| 8 | `/api/v1/intent` | POST | 3 | Architectural intent |
| 9 | `/api/v1/history/{owner}/{repo}` | GET | 5 | PR/Issue history |
| 10 | `/api/v1/setup/{owner}/{repo}` | GET | 5 | Setup scripts |
| 11 | `/api/v1/issues/recommend/{owner}/{repo}` | GET | 6 | Good first issues |
| 12 | `/api/v1/gatekeeper/{owner}/{repo}` | GET | 8 | Repo health audit |
| 13 | `/api/v1/chatbot` | POST | 7,8 | AI pair programmer |

---

## Typical Frontend Workflow

```
1. Gatekeeper  →  Check if repo is healthy before investing time
2. Ingest      →  Clone repo + fetch metadata
3. (Poll) Status  →  Wait for parsing to finish
4. Graph       →  Get the dependency DAG for visualization
5. Vectorize   →  Embed code for AI search
6. Issues      →  Recommend beginner-friendly issues
7. Chatbot     →  Start a mission on a chosen issue
```

---

## Common Models

### `user_profile` (optional, used in Explain & Chatbot)

```json
{
  "level": "student | junior | senior",
  "language": "English | Hindi | Hinglish | Tamil | Telugu | Marathi | Bengali",
  "goal": "contributing | learning"
}
```
When provided, the AI adjusts its tone:
- **student** → simple analogies, encouraging, avoids jargon
- **junior** → clear and practical, defines terms
- **senior** → concise, technical, no hand-holding
- **Hinglish** → Roman Hindi mixed with English technical terms

---

## 1. Health Check

```
GET /health
```

**Response:**
```json
{ "status": "ok", "version": "0.1.0" }
```

Use this to verify the backend is up before making other calls.

---

## 2. Ingest Repository

```
POST /api/v1/repository/ingest
```

Shallow-clones a GitHub repo (depth=1) and fetches metadata from the GitHub API. Kicks off background Tree-sitter parsing and returns immediately.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `github_url` | string | ✅ | Full GitHub URL, e.g. `https://github.com/pallets/flask` |
| `github_pat` | string | ❌ | Optional GitHub PAT (overrides the server's default PAT) |

### Response Body (`IngestResponse`)

| Field | Type | Description |
|-------|------|-------------|
| `repo_id` | string | `"owner/repo"` format |
| `metadata` | object | See `RepoMetadata` below |
| `clone_path` | string | Absolute path where repo was cloned (on server) |
| `status` | string | `"ingested"` or `"error"` |
| `message` | string | Error message if status is `"error"` |

### `RepoMetadata` Object

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Repo name (`"flask"`) |
| `full_name` | string | `"pallets/flask"` |
| `description` | string\|null | Repo description |
| `stars` | int | Star count |
| `forks` | int | Fork count |
| `language` | string\|null | Primary language |
| `default_branch` | string | Default branch name |
| `topics` | string[] | GitHub topics/tags |
| `html_url` | string | URL to the repo on GitHub |

### Example

```json
// Request
POST /api/v1/repository/ingest
{ "github_url": "https://github.com/pallets/flask" }

// Response (200)
{
  "repo_id": "pallets/flask",
  "metadata": {
    "name": "flask",
    "full_name": "pallets/flask",
    "description": "The Python Micro Framework",
    "stars": 68000,
    "forks": 16000,
    "language": "Python",
    "default_branch": "main",
    "topics": ["flask", "python", "web"],
    "html_url": "https://github.com/pallets/flask"
  },
  "clone_path": "/tmp/devlens_xyz/pallets_flask",
  "status": "ingested",
  "message": ""
}
```

### Important Notes
- After ingestion, background parsing starts automatically. Poll `/status` until it returns `"completed"` before calling `/graph`.
- Ingestion is idempotent — calling it again re-clones.

---

## 3. Get Dependency Graph

```
GET /api/v1/repository/graph/{owner}/{repo}
```

Returns the Tree-sitter parsed dependency graph (files as nodes, imports as edges).

### Path Parameters

| Param | Description |
|-------|-------------|
| `owner` | GitHub user/org, e.g. `pallets` |
| `repo` | Repo name, e.g. `flask` |

### Response Body (`GraphData`)

| Field | Type | Description |
|-------|------|-------------|
| `nodes` | Node[] | Array of files in the repo |
| `edges` | Edge[] | Import relationships between files |
| `circular_deps` | string[][] | Detected circular dependency cycles |
| `skipped_files` | string[] | Files that couldn't be parsed |

### `Node` Object

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Relative file path |
| `language` | string | Detected language (python, javascript, etc.) |
| `size_bytes` | int | File size |
| `extracted_names` | string[] | Functions/classes found in the file |

### `Edge` Object

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Importing file path |
| `target` | string | Imported file path |
| `edge_type` | string | Always `"import"` |

### Error Responses
- **404** — Graph not found (repo not ingested or still parsing)

---

## 4. Check Parsing Status

```
GET /api/v1/repository/status/{owner}/{repo}
```

### Response Body

| Field | Type | Values |
|-------|------|--------|
| `status` | string | `"completed"` · `"parsing"` · `"not_found"` |

### Frontend Usage
Poll this every 1-2 seconds after calling `/ingest` until you get `"completed"`.

---

## 5. Vectorize Repository

```
POST /api/v1/repository/vectorize
```

Chunks the repo's code by class/function, embeds each chunk with AWS Bedrock Titan v2, and stores vectors in ChromaDB. **Must call `/ingest` first.**

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `owner` | string | ✅ | GitHub owner |
| `repo` | string | ✅ | Repo name |

### Response Body (`VectorizeResponse`)

| Field | Type | Description |
|-------|------|-------------|
| `repo_id` | string | `"owner/repo"` |
| `total_files` | int | Files processed |
| `total_chunks` | int | Code chunks created |
| `embedded_chunks` | int | Chunks successfully embedded |
| `skipped_chunks` | int | Chunks skipped (too small/large) |
| `status` | string | `"completed"` |

### Important Notes
- This can take 1-2 minutes for large repos. Set a long timeout (e.g. 300s).
- Must be called before `/search` will work.
- Calling it again is safe (re-indexes).

---

## 6. Hybrid Search

```
POST /api/v1/search
```

Finds relevant code for a query using dense vector search (ChromaDB) + BM25 keyword re-ranking. **Must call `/vectorize` first.**

### Request Body

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `owner` | string | ✅ | — | GitHub owner |
| `repo` | string | ✅ | — | Repo name |
| `query` | string | ✅ | — | Search query or issue description |
| `top_k` | int | ❌ | 10 | Max results to return |

### Response Body (`SearchResponse`)

| Field | Type | Description |
|-------|------|-------------|
| `repo_id` | string | `"owner/repo"` |
| `query` | string | The query sent |
| `results` | SearchResult[] | Ranked code chunks |

### `SearchResult` Object

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | File where the code was found |
| `chunk_type` | string | `"class"`, `"function"`, or `"module"` |
| `language` | string | Programming language |
| `chunk` | string | Code snippet (up to 2000 chars) |
| `score` | float | Blended relevance score (0-1, higher = better) |

### Scoring Details
- `score = 0.7 × cosine_similarity + 0.3 × keyword_overlap`
- Minimum threshold: `0.3` cosine similarity

---

## 7. Explain Code (Jargon Buster)

```
POST /api/v1/explain
```

Sends code or technical text to Claude for a student-friendly explanation with jargon breakdown. Supports multilingual output (Hindi, Hinglish, Tamil, etc.).

### Request Body

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `content` | string | ✅ | — | Code snippet or technical text (max ~6000 chars) |
| `language` | string | ❌ | `"English"` | Output language |
| `user_profile` | object | ❌ | null | `{level, language, goal}` for persona-aware tone |

### Response Body (`ExplainResponse`)

| Field | Type | Description |
|-------|------|-------------|
| `explanation` | string | 3-4 sentence friendly explanation |
| `jargon_terms` | JargonTerm[] | Technical terms broken down |

### `JargonTerm` Object

| Field | Type | Description |
|-------|------|-------------|
| `term` | string | The jargon word |
| `technical_definition` | string | Strict technical definition |
| `student_analogy` | string | Real-world analogy (e.g. "like a restaurant waiter") |

### Example

```json
// Request
{
  "content": "async def fetch_data(url):\n    async with httpx.AsyncClient() as client:\n        return await client.get(url)",
  "language": "Hinglish",
  "user_profile": { "level": "student", "language": "Hinglish", "goal": "learning" }
}

// Response
{
  "explanation": "Yeh function ek URL se data fetch karta hai...",
  "jargon_terms": [
    {
      "term": "async/await",
      "technical_definition": "Python keywords for asynchronous programming",
      "student_analogy": "Jaise aap chai banate waqt bread toast kar sakte ho — ek kaam ka wait nahi karte"
    }
  ]
}
```

---

## 8. Architectural Intent

```
POST /api/v1/intent
```

Fetches the last ~50 commits for a specific file from GitHub and asks Claude AI to summarize the file's architectural purpose and how it evolved over time.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `owner` | string | ✅ | GitHub owner |
| `repo` | string | ✅ | Repo name |
| `file_path` | string | ✅ | Path within the repo (e.g. `"src/auth/login.py"`) |

### Response Body (`IntentResponse`)

| Field | Type | Description |
|-------|------|-------------|
| `intent_summary` | string | AI-generated architectural summary (markdown) |
| `commits_analyzed` | int | Number of commits analyzed |

### Note
- Requires a valid GitHub PAT in the server config (or the repo must be public).
- Returns `commits_analyzed: 0` if the file has no commit history.

---

## 9. PR/Issue History (Institutional Memory)

```
GET /api/v1/history/{owner}/{repo}
```

Fetches the last 50 merged Pull Requests using GitHub's GraphQL API, including linked issues and changed files.

### Response Body (`HistoryResponse`)

| Field | Type | Description |
|-------|------|-------------|
| `repo_id` | string | `"owner/repo"` |
| `pull_requests` | object[] | Array of PR objects |

### Each PR Object

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | PR title |
| `author` | string | Author login |
| `url` | string | URL to the PR |
| `merged_at` | string | ISO timestamp |
| `linked_issues` | object[] | `[{number, title, url}]` |
| `changed_files` | string[] | List of files changed |

### Note
- Requires GitHub PAT with GraphQL access.

---

## 10. Setup Scripts

```
GET /api/v1/setup/{owner}/{repo}
```

Scans the ingested repo for configuration files and generates copy-pasteable setup scripts. **Must call `/ingest` first.**

### Response Body (`SetupResponse`)

| Field | Type | Description |
|-------|------|-------------|
| `repo_id` | string | `"owner/repo"` |
| `bash_script` | string | Bash script for Linux/Mac |
| `powershell_script` | string | PowerShell script for Windows |

### Detected Config Files
- `package.json` → npm/yarn/pnpm install
- `requirements.txt` / `Pipfile` / `pyproject.toml` → Python venv + pip
- `Cargo.toml` → cargo build
- `go.mod` → go mod download
- `Dockerfile` / `docker-compose.yml` → Docker commands

### Error Responses
- **404** — Repo not ingested yet

---

## 11. Good First Issues

```
GET /api/v1/issues/recommend/{owner}/{repo}
```

Fetches issues labeled as "good first issue" and checks if each has an active PR already linked (to avoid duplicated effort).

### Response Body (`RecommendIssuesResponse`)

| Field | Type | Description |
|-------|------|-------------|
| `repo_id` | string | `"owner/repo"` |
| `recommended_issues` | IssueRecommendation[] | List of beginner issues |

### `IssueRecommendation` Object

| Field | Type | Description |
|-------|------|-------------|
| `number` | int | Issue number |
| `title` | string | Issue title |
| `url` | string | GitHub URL to the issue |
| `body_preview` | string | First ~200 chars of the issue body |
| `in_progress` | bool | `true` if someone already has an open PR |
| `active_prs` | string[] | URLs of linked PRs |

### Frontend Tip
- Show `in_progress: true` issues in yellow as "⚠️ In Progress", and `false` ones in green as "🟢 Available".

---

## 12. Gatekeeper (Repo Health Audit)

```
GET /api/v1/gatekeeper/{owner}/{repo}
```

Pre-ingestion check — evaluates whether a repo is healthy and beginner-friendly **before** running the expensive clone+parse pipeline.

### Response Body (`GatekeeperVerdict`)

| Field | Type | Description |
|-------|------|-------------|
| `repo_id` | string | `"owner/repo"` |
| `liveness` | string | `"active"` · `"stale"` · `"dead"` |
| `last_push` | string | ISO timestamp of last push |
| `days_since_push` | int | Days since last push |
| `open_prs` | int | Number of open PRs |
| `competition` | string | `"low"` · `"medium"` · `"high"` |
| `dependency_count` | int | Number of dependencies found |
| `complexity` | string | `"beginner"` · `"intermediate"` · `"expert"` |
| `verdict` | string | Human-readable verdict (includes emoji) |
| `warnings` | string[] | List of warning messages |

### Verdict Logic

| Condition | Flag |
|-----------|------|
| Last push > 1 year | 🔴 Dead |
| Last push > 6 months | 🟡 Stale |
| Open PRs > 50 | 🟡 High Competition |
| Dependencies > 500 | 🔴 Expert Level |
| No red/yellow flags | ✅ Beginner Friendly |

### Example
```json
// GET /api/v1/gatekeeper/pallets/flask
{
  "repo_id": "pallets/flask",
  "liveness": "active",
  "last_push": "2026-02-20T04:00:36Z",
  "days_since_push": 11,
  "open_prs": 3,
  "competition": "low",
  "dependency_count": 0,
  "complexity": "beginner",
  "verdict": "✅ Beginner Friendly",
  "warnings": []
}
```

### Frontend Tip
- **Call this BEFORE `/ingest`** to warn users about dead/overwhelming repos.
- Color the verdict: green for ✅, yellow for 🟡, red for 🔴.

---

## 13. Chatbot (DevLens Architect)

```
POST /api/v1/chatbot
```

The AI pair programmer. This single endpoint handles **3 different flows** depending on the fields provided.

### Request Body (`ChatRequest`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `owner` | string | ✅ | — | GitHub owner |
| `repo` | string | ✅ | — | Repo name |
| `message` | string | ✅ | — | User message, issue description, or terminal output |
| `mission_id` | string | ❌ | null | Active mission ID (e.g. `"issue-42"`) |
| `current_step` | int | ❌ | null | Current step in the mission plan |
| `type` | string | ❌ | `"user_chat"` | `"user_chat"` or `"terminal_output"` |
| `issue_number` | int | ❌ | null | Triggers Flow 1 (full investigation) |
| `user_profile` | object | ❌ | null | `{level, language, goal}` for persona |

### Response Body (`ChatResponse`)

| Field | Type | Description |
|-------|------|-------------|
| `reply` | string | AI response (markdown formatted) |
| `mission_id` | string\|null | Mission ID (set when Flow 1 creates a mission) |
| `mode` | string\|null | `"exterminator"` · `"builder"` · `"janitor"` |
| `plan` | string\|null | Step-by-step mission plan (markdown checklist) |
| `relevant_files` | string[]\|null | Files related to the issue |
| `blast_radius` | string[]\|null | Files that depend on the target files |
| `git_commands` | string\|null | Ready-to-paste terminal commands |

---

### Flow 1: Start a New Mission

**Trigger:** Set `issue_number` in the request.

The agent runs the full pipeline: **Detect Mode → Investigate (Graph-RAG) → Snipe Context → Generate Plan → Generate Git Commands**.

```json
// Request
{
  "owner": "pallets",
  "repo": "flask",
  "message": "Login returns 500 when session cookie expires",
  "issue_number": 42,
  "user_profile": { "level": "student", "language": "English", "goal": "contributing" }
}

// Response
{
  "reply": "## 🐛 Mission Mode: Bug Fix\n\n### 🎯 Relevant Files\n- `src/auth/session.py`\n...",
  "mission_id": "issue-42",
  "mode": "exterminator",
  "plan": "1. [ ] Reproduce the bug by...\n2. [ ] Locate the session handler in...",
  "relevant_files": ["src/auth/session.py", "src/auth/middleware.py"],
  "blast_radius": ["src/routes/api.py", "tests/test_auth.py"],
  "git_commands": "git clone https://github.com/pallets/flask.git\ncd flask\ngit checkout -b fix/issue-42-login-returns-500..."
}
```

**Modes auto-detected from the issue text:**

| Mode | Keywords | Focus |
|------|----------|-------|
| 🐛 Exterminator | bug, error, crash, fix, fail | Reproduce → Locate → Fix → Verify |
| 🏗️ Builder | add, feature, new, implement, create | Architecture → Implement → Wire Up → Test |
| 🧹 Janitor | refactor, docs, clean, rename, lint | Scope → Dependency Safety → Execute → Verify |

---

### Flow 2: Terminal Output Analysis

**Trigger:** Set `type: "terminal_output"` + `mission_id`.

User pastes terminal errors during a mission. The agent analyzes whether the error was **caused** by the last step or **reveals** a pre-existing issue.

```json
// Request
{
  "owner": "pallets",
  "repo": "flask",
  "message": "ModuleNotFoundError: No module named 'flask_session'",
  "mission_id": "issue-42",
  "current_step": 2,
  "type": "terminal_output"
}

// Response
{
  "reply": "This error was NOT caused by your changes — it's a pre-existing missing dependency...",
  "mission_id": "issue-42",
  "mode": "exterminator"
}
```

---

### Flow 3: Follow-up Chat

**Trigger:** Default (no `issue_number`, `type` is `"user_chat"`).

General Q&A within or outside an active mission context.

```json
// Request (with active mission)
{
  "owner": "pallets",
  "repo": "flask",
  "message": "What does the verify_token function do?",
  "mission_id": "issue-42"
}

// Request (no active mission → simple AI chat)
{
  "owner": "pallets",
  "repo": "flask",
  "message": "What is Flask's application factory pattern?"
}
```

### Frontend Integration Tips
1. **Store `mission_id`** from Flow 1 response and pass it in all subsequent requests.
2. **Toggle `type`** between `"user_chat"` and `"terminal_output"` based on UI mode.
3. **Display `plan` as a checklist** — each line starts with `[ ]`.
4. **Display `relevant_files` and `blast_radius`** in collapsible sections.
5. **Display `git_commands`** in a code block with a copy button.

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message string"
}
```

| Status | Meaning |
|--------|---------|
| 404 | Resource not found (repo not ingested, no graph, no mission) |
| 422 | Validation error (missing required fields) |
| 500 | Server error (API failure, LLM timeout, etc.) |

---

## Environment Requirements

The backend requires these environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `github_pat` | Recommended | GitHub PAT for API calls (avoids rate limits) |
| `openrouter_api_key` | ✅ | API key for Claude/LLM via OpenRouter |
| `aws_region` | ✅ | AWS region for Bedrock |
| `aws_access_key_id` | ✅ | AWS credentials |
| `aws_secret_access_key` | ✅ | AWS credentials |
| `chroma_path` | ❌ | Path for persistent ChromaDB storage |
