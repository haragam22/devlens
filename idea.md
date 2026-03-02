# **DevLens: The AI Navigator for Your Codebase**

**Team Name:** DABBA | **Team Leader:** HARAGAM DEEP SINGH

## **1\. Executive Summary & Vision**

**The Problem:** Open-source projects contain thousands of lines of code and years of history. For new contributors—especially India’s 1.5 million annual engineering graduates from Tier-2/3 colleges—the hardest part isn't writing code, but understanding where to start. This lack of context leads to confusion and hesitation. Most existing tools assume prior understanding of the repository.

**The Solution:** DevLens is an AI-powered onboarding navigator that acts as a "Digital Senior Mentor". It builds "Architectural Intuition" by analyzing a repository's code, issues, and pull-request history to provide clear, logic-aware guidance.

**Core Philosophy:** DevLens acts as the Strategic Navigator (telling users where to go and why), designed to perfectly complement tactical execution tools like GitHub Copilot (which helps with the how once the user is in the right file).

## **2\. Key Features**

* **Issue-to-Code Mapping:** Uses semantic search and RAG to automatically pinpoint the exact files and functions needed to solve a specific GitHub Issue.  
* **Architectural Intent (Institutional Memory):** Scans past Pull Requests to explain the "why" behind specific logic and architectural decisions.  
* **Repository Visualization:** Generates a highly interactive, bird's-eye Force-Directed Graph to show how different modules and dependencies are connected.  
* **Code Entity Extraction:** Uses AST to parse files and extract functions, classes, and methods, allowing users to jump directly to specific code blocks.
* **The "Jargon Buster" (Indic Bridge):** Acts as an AI mentor that simplifies dense technical documentation into "Student-Friendly" analogies, actively supporting regional languages (Hindi, Hinglish, Tamil, etc.).
* **Beginner Issue Matcher:** Automatically hooks into GitHub GraphQL to fetch "Good First Issues" and crucially flags if they are already being worked on.
* **DevLens Architect (Agentic Onboarding):** A state-aware conversational agent that graphs "blast radiuses", prints direct terminal setup commands, and reacts to system logs in real-time.
* **Personalized Feasibility Engine:** Uses a pre-flight "Gatekeeper" to warn beginners off dead or highly complex repos, while modifying its own AI tone based on the user's skill level and language entirely dynamically.

## **3\. Technical Architecture**

DevLens is built for scale and speed, utilizing a robust three-tier architecture:

* **Frontend Presentation Layer:** Built with React and Tailwind CSS for a high-performance Single Page Application (SPA). Utilizes Generative UI (v0.dev) for a distraction-free developer interface.  
* **Backend API Layer:** Powered by FastAPI (Python) for asynchronous, high-concurrency API routing. Uses PyGithub and GitPython to handle real-time repository ingestion, issue fetching, and cloning.  
* **AI & ML Layer (Powered by OpenRouter & AWS):** 
  * **OpenRouter (Nemotron-3):** Orchestrates `nvidia/nemotron-3-nano-30b-a3b:free` for superior code reasoning, architectural synthesis, and jargon simplification.  
  * **Amazon Titan Embeddings v2:** Generates high-dimensional vector embeddings for code chunks (up to 8k token context) for cost-optimized semantic search.  
* **Data & Memory Layer:** \* **ChromaDB:** A local vector store for low-latency retrieval-augmented generation (RAG).  
  * **Python AST (Abstract Syntax Tree):** A parsing engine used to generate 100% accurate, deterministic dependency graphs.

## **4\. Implementation Details & System Flow**

* **Robust Ingestion:** The user pastes a GitHub URL. The IngestService handles cloning and metadata extraction. It includes a Rate\_Limit\_Handler to manage GitHub API 429 errors using exponential backoff and token rotation.  
* **Analysis & Mapping:** The StaticAnalyzer processes Python files to map dependencies (and flag circular imports), while the Issue\_Sentinel generates embeddings to link issues directly to the relevant codebase logic.  
* **Synthesis:** The RAG\_Orchestrator translates the raw code data and PR history into strategic guidance.  
* **Security (The Persistence Paradox):** DevLens employs a strict hybrid storage strategy. Guest user data is stored entirely in ephemeral RAM and wiped post-session. Authenticated users get persistent ChromaDB storage (S3 backed). Personal Access Tokens (PATs) are strictly held in RAM and never persisted to disk.  
* **Performance Constraints:** The system is optimized to ingest 100MB repositories within 60 seconds, query up to 10,000 files in under 2 seconds, and map AST for 1,000 Python files in under 5 seconds.

## **5\. Why We Win (The Technical Moat)**

* **Deterministic Architecture (AST vs. LLM):** Unlike standard RAG applications that feed code directly to an LLM and risk hallucinations, DevLens relies on a deterministic StaticAnalyzer using Python AST to generate 100% accurate dependency graphs. The AI layer is strictly reserved for semantic reasoning and synthesis, ensuring structural truth.  
* **Enterprise-Grade Resilience:** Engineered to handle the messy reality of the GitHub API. The Rate\_Limit\_Handler utilizes exponential backoff, token rotation, and queue management, while processing errors use graceful degradation (like partial AST parsing recovery), allowing the system to handle massive 5000+ file repositories without crashing.  
* **Production-Ready Rigor:** The architecture is governed by 12 strict "Correctness Properties" and validated through a Dual Testing Approach involving both unit tests and property-based testing. This demonstrates a high-level commitment to system reliability and mature MLOps practices.  
* **The "Persistence Paradox" Strategy:** A highly conscious approach to data privacy and infrastructure costs. The hybrid storage model ensures guest data remains zero-trace (RAM-only), while authenticated users benefit from sub-second loading via persistent ChromaDB and S3 backups.

