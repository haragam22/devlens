# DevLens Implementation Status

This document tracks the delivery of features outlined in the project's strategy documents (`idea.md`, `technical.md`, and `implementation.md`). It serves as a master checklist to flag what has been built into the backend, what is currently simulated in the Streamlit Tester, and what remains to be built for the final production release.

---

## 1. Core Engines (Infrastructure & Data Layer)

| Feature | Status | Details & Endpoints |
| :--- | :--- | :--- |
| **FastAPI & Async Architecture** | ✅ Implemented | High-concurrency routing, asynchronous subprocess calls. |
| **AI Clients (OpenRouter & AWS)** | ✅ Implemented | `app/services/bedrock_client.py` using Nemotron-3 (OpenRouter) & Titan v2 (AWS Bedrock). |
| **HybridStorageManager** | ✅ Implemented | `app/storage/hybrid_storage.py` handles ephemeral `RAMStore` and persistent ChromaDB `DiskStore`. |
| **Rate Limit Management** | ✅ Implemented | Bypasses REST API via `git clone`, uses `asyncio.Semaphore(50)` for AWS, and `tenacity` for backoff. |
| **Security: Pre-Flight Filtering** | ✅ Implemented | Skips 1MB+ files, excludes `node_modules`/`.git`, handles MIME-types. |
| **Security: XML Sandboxing** | ✅ Implemented | System prompts firmly isolate `<untrusted_repository_data>` from LLM instructions. |

---

## 2. Ingestion & Analysis Pipelines

| Feature | Status | Details & Endpoints |
| :--- | :--- | :--- |
| **Dual Ingestion (Shallow Clone)** | ✅ Implemented | `POST /api/v1/repository/ingest` |
| **GitHub GraphQL Data Fetching**| ✅ Implemented | `GET /api/v1/history/{owner}/{repo}` efficiently fetches 50 recent PRs + issues in one shot. |
| **Language-Agnostic Parsing (Tree-sitter)**| ✅ Implemented | `GET /api/v1/repository/graph/{owner}/{repo}` parses ASTs deterministically. |
| **Hybrid Vector Engine** | ✅ Implemented | `POST /api/v1/repository/vectorize` chunks by classes/functions, embeds via AWS, stores in ChromaDB. |

---

## 3. The Core Features

| Feature | Design Target | Implementation Status | Notes |
| :--- | :--- | :--- | :--- |
| **Feature 1: Issue-to-Code Mapping** | Hybrid Dense + Sparse BM25 Search. | ✅ Implemented | `POST /api/v1/search` combines Cosine Similarity & Keyword Overlap. |
| **Feature 2: Repository Visualization**| React Force-Directed Graph UI + AST Backend. | ⚠️ Partially Implemented | Backend graph JSON generator (`/api/v1/repository/graph`) is working. **React Frontend is completely missing.** |
| **Feature 3: Architectural Intent** | Analyze PR history via OpenRouter (Nemotron-3) | ✅ Implemented | `POST /api/v1/intent` queries GitHub and asks the LLM to explain why code exists. |
| **Feature 4: The Jargon Buster (Indic Bridge)** | Student-friendly technical explanations in multiple languages. | ✅ Implemented | `POST /api/v1/explain` powered by Nemotron-3 now accepts a `language` (e.g., Hindi, Hinglish). |
| **Feature 5: Environment Setup Guidance**| Deterministic setup script generation. | ✅ Implemented | `GET /api/v1/setup/{owner}/{repo}` scans `package.json`, `Dockerfile`, etc., producing Bash/PowerShell scripts. |
| **Feature 6: Beginner Issue Matcher**| Finds open beginner issues and detects if active PRs are linked. | ✅ Implemented | `GET /api/v1/issues/recommend` queries GraphQL to extract `good first issue` markers and cross-referencing timeline PRs. |
| **Feature 7: DevLens Architect**| End-to-End Agentic Contribution Planner (Mission Control & Git Commander). | ❌ Not Implemented | Phase 7 is planned. Backend needs a stateful session router (`POST /api/v1/chatbot`). |
| **Feature 8: Personalization & Feasibility**| Repo Gatekeeper, User Context Engine, and Anti-Gravity Handover | ❌ Not Implemented | Phase 8 is planned. Pre-ingestion check and dynamic prompt injection. |

---

## 4. Frontend Application

| Component | Status | Details |
| :--- | :--- | :--- |
| **React/Tailwind SPA** | ❌ Not Implemented | The final user-facing `react-force-graph` and UI described in `idea.md` is not built. |
| **Streamlit Tester Dashboard** | ✅ Implemented | `tester/app.py` exists as an engineering debug tool. Provides full interactive control over the 5 core features and all endpoints. |

---

## 🚩 Flagged Remaining Work (To-Do)

While the backend infrastructure is feature-complete for Phase 1 through 6, the following critical steps remain:

1. **Phase 7 & 8 (Backend Integration):** Build a stateful session machine for `POST /api/v1/chatbot` (DevLens Architect), create the `GET /api/v1/gatekeeper` endpoint for repo auditing, and wire the `user_profile` headers to the dynamic prompt generator.
2. **Frontend Presentation Layer:** The React + Tailwind SPA intended for the final product needs to be built and wired to the FastAPI endpoints. The Force-Directed Graph visualization must be implemented using `react-force-graph`.
3. **Context Window Degradation (Map-Reduce):** The implementation plan mentions a Map-Reduce capability if PR history (Architectural Intent) exceeds 15,000 tokens ("Lost in the Middle" mitigation). Currently, the system just trims context; a true map-reduce summarization step is pending if scale requires it.
4. **Advanced Tree-Sitter Grammars:** The Tree-Sitter pipeline currently works excellently for Python natively, but the environment may need script compilation steps for extended JavaScript, TypeScript, or Go parsing depending on deployment.
