### **The Stack Strategy**

* **Frontend:** React \+ Tailwind CSS \+ react-force-graph (for the visualization) \+ framer-motion (for "crazy" animations).  
* **Backend:** FastAPI \+ asyncio (for concurrency) \+ Tree-sitter (parsing) \+ ChromaDB (vector store).  
* **AI:** OpenRouter (`nvidia/nemotron-3-nano-30b-a3b:free`) + AWS Bedrock (Titan Embeddings v2).

### ---

**Phase 1: The "Skeleton & Ingestion" (Days 1-2)**

*Goal: Get the system running and able to "eat" a GitHub repository.*

**Backend Deliverables (FastAPI):**

1. **Project Shell:** Setup FastAPI with uvicorn. Create the HybridStorageManager class to handle RAM vs. Disk storage logic.

2. **Ingestion Endpoint:** Create POST /api/v1/repository/ingest.  
   * **Action:** Use subprocess to run git clone \--depth 1 \<url\> to a temp dir.

   * **Action:** Use httpx or PyGithub to fetch metadata (stars, forks) via GitHub API.  
3. **Tree-sitter Setup:** Install tree-sitter and tree-sitter-languages (Python, JS, Go). Write a parser that walks the AST and extracts (Node: File) \-\> (Edge: Import).

**Frontend Deliverables (React \+ Tailwind):**

1. **"Crazy" Landing Page:** Create a hero section with a glowing input field for the GitHub URL.  
   * *UI Tip:* Use a "Matrix-style" rain or particle background effect to signal "Code Intelligence."  
2. **Repo Loading State:** A terminal-like loader that streams real-time logs ("Cloning repo...", "Parsing AST...", "Vectorizing chunks...") as the backend processes data.

### ---

**Phase 2: The "Brain" & "The Map" (Days 3-5)**

*Goal: Make the backend smart and the frontend visual.*

**Backend Deliverables:**

1. **Vector Pipeline:** Implement the **Hybrid Vector Engine**.  
   * **Chunking:** Split code by class/function (not just lines).

   * **Embedding:** Send chunks to AWS Bedrock (Titan v2) and store in ChromaDB.

2. **Graph Endpoint:** Create GET /api/v1/repository/graph.  
   * Return the JSON schema required by react-force-graph (nodes \= files, links \= dependencies).

**Frontend Deliverables (The "Crazy UI"):**

1. **3D Force-Directed Graph:** Integrate react-force-graph-3d.  
   * **Visuals:** Make nodes glowing spheres. Dependencies should be laser-like lines.  
   * **Interaction:** Clicking a node zooms the camera into it and opens a side panel with file details.  
2. **HUD Layout:** Build a "Heads-Up Display" overlay on top of the graph.  
   * Left Panel: File Explorer (Glassmorphism effect).  
   * Right Panel: AI Chat/Context (Hidden by default, slides in).

### ---

**Phase 3: The "Intelligence" Features (Days 6-8)**

*Goal: Connect the RAG features and "Senior Mentor" mode.*

**Backend Deliverables:**

1. **Search Endpoint (Issue-to-Code):** Implement POST /api/v1/search.  
   * Perform **Hybrid Search** (Dense Vector \+ Sparse BM25) \+ Reranking to find relevant files for a query.

2. **Mentor Endpoint (Jargon Buster):** Implement POST /api/v1/explain.  
   * Send selected code/text to OpenRouter (Nemotron-3) with a prompt to identify jargon and explain it simply.

3. **Intent Endpoint:** Fetch PR history for a file, summarize it using Map-Reduce if token count \> 15k, and return the "Architectural Intent".

**Frontend Deliverables:**

1. **Contextual Chat:** When a user selects a file in the graph, allow them to "Ask the Repo".  
   * *UI Tip:* Use a typewriter effect for AI responses. Highlight code snippets with syntax highlighting.  
2. **"Jargon Hover":** If the user toggles "Junior Mode", highlight complex words in the UI. Hovering them shows a tooltip with the "Student-Friendly Analogy".

### ---

**Phase 4: Polish & Production (Days 9-10)**

*Goal: Stability and user experience refinement.*

**Steps:**

1. **Rate Limit Guardrails:** Implement the asyncio.Semaphore logic to prevent AWS Bedrock 429 errors during mass vectorization.

2. **The "Fat Repo" Check:** Add the 1MB file size limit check in the parsing loop to prevent memory crashes.

3. **Deployment:**  
   * **Frontend:** Vercel or Netlify.  
   * **Backend:** AWS EC2 or Render (Dockerized). Use a persistent volume for ChromaDB if you aren't using S3 yet.

