"""
DevLens – Streamlit Backend Tester
A side-by-side UI to test all DevLens backend endpoints interactively.
"""

import time
import httpx
import streamlit as st
import pandas as pd

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DevLens Tester",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar – server config
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🔍 DevLens Tester")
    st.markdown("---")
    base_url = st.text_input(
        "Backend URL",
        value="http://127.0.0.1:8000",
        help="URL where the FastAPI backend is running",
    )
    st.markdown("---")

    # Health check widget
    if st.button("🩺 Check Health", use_container_width=True):
        try:
            r = httpx.get(f"{base_url}/health", timeout=5)
            if r.status_code == 200:
                st.success(f"✅ Server is up  \n`{r.json()}`")
            else:
                st.error(f"❌ Status {r.status_code}")
        except Exception as e:
            st.error(f"❌ Cannot reach server  \n`{e}`")

    st.markdown("---")
    st.caption("Phases 1-8: Ingest, Graph, Vectorize, Search, Explain, Intent, History, Setup, Issues, Gatekeeper, Repo Buddy")

    st.markdown("---")
    st.subheader("🎭 User Profile")
    profile_level = st.selectbox("Skill Level", ["student", "junior", "senior"], index=1, key="profile_level")
    profile_lang = st.selectbox("Language", ["English", "Hindi", "Hinglish", "Tamil", "Telugu", "Marathi", "Bengali"], key="profile_lang")
    profile_goal = st.selectbox("Goal", ["contributing", "learning"], key="profile_goal")

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------
if "ingest_result" not in st.session_state:
    st.session_state.ingest_result = None
if "graph_result" not in st.session_state:
    st.session_state.graph_result = None
if "vectorize_result" not in st.session_state:
    st.session_state.vectorize_result = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "active_mission" not in st.session_state:
    st.session_state.active_mission = None

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_ingest, tab_graph, tab_vectorize, tab_search, tab_explain, tab_intent, tab_history, tab_setup, tab_issues, tab_gatekeeper, tab_buddy = st.tabs([
    "📥 Ingest", "🗺️ Graph", "🧠 Vectorize", "🔎 Search", "💬 Explain", "🎬 Intent", "📜 History", "🛠️ Setup", "🎯 Issues", "🛡️ Gatekeeper", "🤖 Repo Buddy"
])

# ===========================================================================
# TAB 1 — INGEST
# ===========================================================================
with tab_ingest:
    st.header("📥 Ingest a GitHub Repository")
    st.markdown("Shallow-clones the repo and fetches metadata from the GitHub API.")

    col1, col2 = st.columns([3, 1])
    with col1:
        github_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/owner/repo",
            key="ingest_url",
        )
    with col2:
        github_pat = st.text_input(
            "GitHub PAT (optional)",
            type="password",
            placeholder="ghp_...",
            key="ingest_pat",
        )

    if st.button("🚀 Ingest Repository", type="primary", use_container_width=True):
        if not github_url:
            st.warning("Please enter a GitHub URL.")
        else:
            with st.spinner("Cloning repo and fetching metadata..."):
                try:
                    payload = {"github_url": github_url}
                    if github_pat:
                        payload["github_pat"] = github_pat
                    t0 = time.time()
                    r = httpx.post(
                        f"{base_url}/api/v1/repository/ingest",
                        json=payload,
                        timeout=120,
                    )
                    elapsed = time.time() - t0

                    if r.status_code == 200:
                        data = r.json()
                        st.session_state.ingest_result = data
                        st.success(f"✅ Ingested in **{elapsed:.1f}s**")
                        
                        # Wait for background parsing to complete
                        if "repo_id" in data:
                            owner_repo = data["repo_id"]
                            with st.spinner("⏳ Waiting for AST graph parsing to finish..."):
                                max_retries = 60
                                for _ in range(max_retries):
                                    time.sleep(1)
                                    status_resp = httpx.get(f"{base_url}/api/v1/repository/status/{owner_repo}", timeout=5)
                                    if status_resp.status_code == 200:
                                        p_status = status_resp.json().get("status")
                                        if p_status == "completed":
                                            st.success("🎉 Parsing complete! You can now fetch the full network on the Graph tab.")
                                            break
                                        elif p_status == "failed":
                                            st.error("❌ Background parsing failed. Check server terminal logs.")
                                            break
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")

                except Exception as e:
                    st.error(f"❌ Request failed: `{e}`")

    if st.session_state.ingest_result:
        result = st.session_state.ingest_result
        meta = result.get("metadata", {})

        st.markdown("---")
        st.subheader(f"📦 `{result.get('repo_id', '')}`")

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("⭐ Stars", f"{meta.get('stars', 0):,}")
        mc2.metric("🍴 Forks", f"{meta.get('forks', 0):,}")
        mc3.metric("Language", meta.get("language") or "N/A")
        mc4.metric("Branch", meta.get("default_branch") or "main")

        if meta.get("description"):
            st.info(f"📝 {meta['description']}")

        if meta.get("topics"):
            st.markdown("**Topics:** " + " · ".join(f"`{t}`" for t in meta["topics"]))

        with st.expander("📂 Raw JSON response"):
            st.json(result)

        st.caption(f"Clone path: `{result.get('clone_path', '')}`")

# ===========================================================================
# TAB 2 — GRAPH
# ===========================================================================
with tab_graph:
    st.header("🗺️ Dependency Graph")
    st.markdown("Fetches the Tree-sitter parsed dependency graph for an ingested repo.")

    owner_in = st.text_input("Owner", placeholder="e.g. realpython", key="graph_owner")
    repo_in = st.text_input("Repo", placeholder="e.g. reader", key="graph_repo")

    # Auto-fill from last ingest
    if st.session_state.ingest_result:
        repo_id = st.session_state.ingest_result.get("repo_id", "")
        if "/" in repo_id and not owner_in:
            auto_owner, auto_repo = repo_id.split("/", 1)
            st.caption(f"💡 Last ingested: `{repo_id}` — fill above or use defaults below")

    if st.button("🔍 Fetch Graph", type="primary", use_container_width=True):
        owner = owner_in.strip()
        repo = repo_in.strip()

        # Fallback to last ingest if fields are empty
        if not owner and not repo and st.session_state.ingest_result:
            repo_id = st.session_state.ingest_result.get("repo_id", "")
            if "/" in repo_id:
                owner, repo = repo_id.split("/", 1)

        if not owner or not repo:
            st.warning("Please enter owner and repo name.")
        else:
            with st.spinner(f"Fetching graph for `{owner}/{repo}`..."):
                try:
                    r = httpx.get(
                        f"{base_url}/api/v1/repository/graph/{owner}/{repo}",
                        timeout=30,
                    )
                    if r.status_code == 200:
                        st.session_state.graph_result = r.json()
                        st.success(f"✅ Graph loaded for `{owner}/{repo}`")
                    elif r.status_code == 404:
                        st.warning("⏳ Graph not ready yet — parsing may still be in progress. Wait a few seconds and retry.")
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"❌ Request failed: `{e}`")

    if st.session_state.graph_result:
        graph = st.session_state.graph_result
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        circular = graph.get("circular_deps", [])
        skipped = graph.get("skipped_files", [])

        st.markdown("---")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("📄 Files (Nodes)", len(nodes))
        g2.metric("🔗 Import Edges", len(edges))
        g3.metric("🔴 Circular Deps", len(circular))
        g4.metric("⏭️ Skipped Files", len(skipped))

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("📄 Nodes (Files)")
            if nodes:
                df_nodes = pd.DataFrame(nodes)
                df_nodes["size_kb"] = (df_nodes["size_bytes"] / 1024).round(2)
                
                if "extracted_names" in df_nodes.columns:
                    df_nodes["Entities"] = df_nodes["extracted_names"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
                    cols_to_show = ["id", "language", "size_kb", "Entities"]
                else:
                    cols_to_show = ["id", "language", "size_kb"]
                    
                st.dataframe(
                    df_nodes[cols_to_show].rename(columns={
                        "id": "File", "language": "Lang", "size_kb": "Size (KB)"
                    }),
                    use_container_width=True,
                    height=400,
                )

        with col_b:
            st.subheader("🔗 Edges (Imports)")
            if edges:
                df_edges = pd.DataFrame(edges)
                st.dataframe(
                    df_edges[["source", "target", "edge_type"]].rename(columns={
                        "source": "From", "target": "Import", "edge_type": "Type"
                    }),
                    use_container_width=True,
                    height=400,
                )

        if circular:
            st.error("🔴 Circular Dependencies Detected:")
            for cycle in circular:
                st.code(" → ".join(cycle), language=None)

        if skipped:
            with st.expander(f"⏭️ {len(skipped)} skipped files"):
                for s in skipped:
                    st.text(s)

        with st.expander("📂 Raw JSON response"):
            st.json(graph)

# ===========================================================================
# TAB 3 — VECTORIZE (Phase 2)
# ===========================================================================
with tab_vectorize:
    st.header("🧠 Vectorize Repository (Phase 2)")
    st.markdown("Chunks code by class/function, embeds with AWS Bedrock Titan v2, stores in ChromaDB.")

    v_owner = st.text_input("Owner", placeholder="e.g. realpython", key="vec_owner")
    v_repo = st.text_input("Repo", placeholder="e.g. reader", key="vec_repo")

    if st.button("⚡ Vectorize", type="primary", use_container_width=True):
        owner = v_owner.strip()
        repo = v_repo.strip()
        if not owner or not repo:
            st.warning("Please fill owner and repo.")
        else:
            with st.spinner("Chunking + embedding... (this may take a minute)"):
                try:
                    r = httpx.post(
                        f"{base_url}/api/v1/repository/vectorize",
                        json={"owner": owner, "repo": repo},
                        timeout=300,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        st.session_state.vectorize_result = data
                        st.success("✅ Vectorization complete!")
                        st.json(data)
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"❌ Request failed: `{e}`")

# ===========================================================================
# TAB 4 — SEARCH (Phase 2)
# ===========================================================================
with tab_search:
    st.header("🔎 Issue-to-Code Search (Phase 2)")
    st.markdown("Hybrid search (dense vector + BM25 sparse) to find relevant files for a query.")

    s_owner = st.text_input("Owner", placeholder="e.g. realpython", key="search_owner")
    s_repo = st.text_input("Repo", placeholder="e.g. reader", key="search_repo")
    query = st.text_area("Search Query / Issue Description", placeholder="How does authentication work?", key="search_query")

    if st.button("🔍 Search", type="primary", use_container_width=True):
        if not query.strip():
            st.warning("Please enter a search query.")
        else:
            with st.spinner("Running hybrid search..."):
                try:
                    r = httpx.post(
                        f"{base_url}/api/v1/search",
                        json={"owner": s_owner.strip(), "repo": s_repo.strip(), "query": query},
                        timeout=30,
                    )
                    if r.status_code == 200:
                        results = r.json()
                        st.success(f"✅ Found {len(results.get('results', []))} results")
                        for i, res in enumerate(results.get("results", []), 1):
                            with st.expander(f"#{i} — `{res.get('file_path', '')}` (score: {res.get('score', 0):.3f})"):
                                st.code(res.get("chunk", ""), language="python")
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"❌ Request failed: `{e}`")

# ===========================================================================
# TAB 5 — EXPLAIN
# ===========================================================================
with tab_explain:
    st.header("💬 Jargon Buster / Explain Code (Phase 2 & 6)")
    st.markdown("Sends selected code to AI for student-friendly explanation, supporting multiple languages (The Indic Bridge).")

    lang_choice = st.selectbox(
        "Explanation Language",
        ["English", "Hindi", "Tamil", "Hinglish", "Telugu", "Marathi", "Bengali"]
    )

    code_input = st.text_area(
        "Paste code or technical text to explain",
        height=200,
        placeholder="Paste a function, class, or documentation snippet here...",
        key="explain_input",
    )

    if st.button("🧙 Explain", type="primary", use_container_width=True):
        if not code_input.strip():
            st.warning("Please paste some code or text.")
        else:
            with st.spinner(f"Asking AI to explain in {lang_choice}..."):
                try:
                    r = httpx.post(
                        f"{base_url}/api/v1/explain",
                        json={"content": code_input, "language": lang_choice},
                        timeout=60,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        st.markdown("### 🎓 Explanation")
                        st.markdown(data.get("explanation", ""))
                        if data.get("jargon_terms"):
                            st.markdown("### 📖 Jargon Terms")
                            for term in data["jargon_terms"]:
                                with st.expander(f"**{term['term']}**"):
                                    st.markdown(f"**Technical:** {term['technical_definition']}")
                                    st.markdown(f"**Simple:** {term['student_analogy']}")
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"❌ Request failed: `{e}`")

# ===========================================================================
# TAB 6 — INTENT (Phase 3)
# ===========================================================================
with tab_intent:
    st.header("🎬 Architectural Intent (Phase 3)")
    st.markdown("Fetches GitHub commit history for a file and asks Claude to summarize its architectural intent.")
    
    i_owner = st.text_input("Owner", placeholder="e.g. fastapi", key="intent_owner")
    i_repo = st.text_input("Repo", placeholder="e.g. fastapi", key="intent_repo")
    i_file = st.text_input("File Path", placeholder="e.g. fastapi/routing.py", key="intent_file")
    
    if st.button("fetch Arch Intent", type="primary", use_container_width=True):
        if not i_owner.strip() or not i_repo.strip() or not i_file.strip():
            st.warning("Please fill owner, repo, and file path.")
        else:
            with st.spinner("Fetching commits & asking Claude..."):
                try:
                    r = httpx.post(
                        f"{base_url}/api/v1/intent",
                        json={"owner": i_owner.strip(), "repo": i_repo.strip(), "file_path": i_file.strip()},
                        timeout=60,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        st.success(f"✅ Analyzed {data.get('commits_analyzed', 0)} commits.")
                        st.markdown("### 🏛 Architectural Intent")
                        st.info(data.get("intent_summary", ""))
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"❌ Request failed: `{e}`")

# ===========================================================================
# TAB 7 — HISTORY (Phase 5)
# ===========================================================================
with tab_history:
    st.header("📜 Institutional Memory (GraphQL)")
    st.markdown("Fetches the last 50 merged PRs, their linked issues, and changed files concurrently using GraphQL.")
    
    h_owner = st.text_input("Owner", placeholder="e.g. fastapi", key="history_owner")
    h_repo = st.text_input("Repo", placeholder="e.g. fastapi", key="history_repo")
    
    # Auto-fill from last ingest
    if st.session_state.ingest_result and not h_owner:
        repo_id = st.session_state.ingest_result.get("repo_id", "")
        if "/" in repo_id:
            h_owner_auto, h_repo_auto = repo_id.split("/", 1)
            st.caption(f"💡 Defaulting to ingested: `{repo_id}`")
            h_owner = h_owner_auto
            h_repo = h_repo_auto
            
    if st.button("fetch History", type="primary", use_container_width=True):
        if not h_owner.strip() or not h_repo.strip():
            st.warning("Please fill owner and repo.")
        else:
            with st.spinner("Executing GraphQL query..."):
                try:
                    t0 = time.time()
                    r = httpx.get(
                        f"{base_url}/api/v1/history/{h_owner.strip()}/{h_repo.strip()}",
                        timeout=60,
                    )
                    elapsed = time.time() - t0
                    if r.status_code == 200:
                        data = r.json()
                        prs = data.get("pull_requests", [])
                        st.success(f"✅ Fetched {len(prs)} PRs in {elapsed:.2f}s")
                        
                        for pr in prs:
                            with st.expander(f"📌 {pr.get('title')} (by {pr.get('author')})"):
                                st.caption(f"Merged at: {pr.get('merged_at')} | [View PR]({pr.get('url')})")
                                if pr.get('linked_issues'):
                                    st.markdown("**Linked Issues:**")
                                    for issue in pr['linked_issues']:
                                        st.markdown(f"- [#{issue['number']} {issue['title']}]({issue['url']})")
                                if pr.get('changed_files'):
                                    st.markdown("**Files Changed (sample):**")
                                    st.code("\\n".join(pr['changed_files'][:10]), language="text")
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"❌ Request failed: `{e}`")

# ===========================================================================
# TAB 8 — SETUP (Phase 5)
# ===========================================================================
with tab_setup:
    st.header("🛠️ Automated Onboarding (Phase 5)")
    st.markdown("Generates copy-pasteable setup scripts after scanning the repository configuration.")
    
    set_owner = st.text_input("Owner", placeholder="e.g. realpython", key="setup_owner")
    set_repo = st.text_input("Repo", placeholder="e.g. reader", key="setup_repo")
    
    # Auto-fill from last ingest
    if st.session_state.ingest_result and not set_owner:
        repo_id = st.session_state.ingest_result.get("repo_id", "")
        if "/" in repo_id:
            s_owner_auto, s_repo_auto = repo_id.split("/", 1)
            set_owner = s_owner_auto
            set_repo = s_repo_auto
            
    if st.button("⚙️ Generate Scripts", type="primary", use_container_width=True):
        if not set_owner.strip() or not set_repo.strip():
            st.warning("Please fill owner and repo.")
        else:
            with st.spinner("Scanning configuration files..."):
                try:
                    r = httpx.get(
                        f"{base_url}/api/v1/setup/{set_owner.strip()}/{set_repo.strip()}",
                        timeout=30,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        st.success("✅ Scripts generated")
                        st.markdown("### Bash (Linux/Mac)")
                        st.code(data.get("bash_script", ""), language="bash")
                        st.markdown("### PowerShell (Windows)")
                        st.code(data.get("powershell_script", ""), language="powershell")
                    elif r.status_code == 404:
                        st.warning("❌ Repository not cloned yet. Ingest it in Tab 1 first.")
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"❌ Request failed: `{e}`")

# ===========================================================================
# TAB 9 — ISSUES (Phase 6)
# ===========================================================================
with tab_issues:
    st.header("🎯 Good First Issue Matcher (Phase 6)")
    st.markdown("Fetches issues labeled specifically for beginners, checking if there is already an active PR linked to them.")
    
    iss_owner = st.text_input("Owner", placeholder="e.g. realpython", key="issue_owner")
    iss_repo = st.text_input("Repo", placeholder="e.g. reader", key="issue_repo")
    
    if st.session_state.ingest_result and not iss_owner:
        repo_id = st.session_state.ingest_result.get("repo_id", "")
        if "/" in repo_id:
            i_owner_auto, i_repo_auto = repo_id.split("/", 1)
            iss_owner = i_owner_auto
            iss_repo = i_repo_auto
            
    if st.button("🔍 Find Beginner Issues", type="primary", use_container_width=True):
        if not iss_owner.strip() or not iss_repo.strip():
            st.warning("Please fill owner and repo.")
        else:
            with st.spinner("Scanning issues and their timelines..."):
                try:
                    r = httpx.get(
                        f"{base_url}/api/v1/issues/recommend/{iss_owner.strip()}/{iss_repo.strip()}",
                        timeout=30,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        issues = data.get("recommended_issues", [])
                        
                        if not issues:
                            st.info("No beginner-friendly issues found that are open.")
                        else:
                            st.success(f"✅ Found {len(issues)} beginner issues!")
                            for issue in issues:
                                if issue.get("in_progress"):
                                    st.warning(f"⚠️ [In Progress] #{issue['number']} - {issue['title']}")
                                    with st.expander(f"View Issue #{issue['number']} details"):
                                        st.caption(f"[GitHub Link]({issue['url']})")
                                        st.markdown(f"**Linked PRs:**")
                                        for pr in issue.get("active_prs", []):
                                            st.markdown(f"- {pr}")
                                else:
                                    st.success(f"🟢 [Available] #{issue['number']} - {issue['title']}")
                                    with st.expander(f"View Issue #{issue['number']} details"):
                                        st.caption(f"[GitHub Link]({issue['url']})")
                                        st.markdown(f"**Preview:**\n{issue.get('body_preview', '')}")
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"❌ Request failed: `{e}`")

# ===========================================================================
# TAB 10 — GATEKEEPER (Phase 8: Repo Health Audit)
# ===========================================================================
with tab_gatekeeper:
    st.header("🛡️ Gatekeeper — Repo Health Audit")
    st.markdown("Pre-ingestion check: evaluates whether a repository is healthy, active, and beginner-friendly before you invest time cloning and parsing it.")

    gk_owner = st.text_input("Owner", placeholder="e.g. pallets", key="gk_owner")
    gk_repo = st.text_input("Repo", placeholder="e.g. flask", key="gk_repo")

    if st.session_state.ingest_result and not gk_owner:
        repo_id = st.session_state.ingest_result.get("repo_id", "")
        if "/" in repo_id:
            st.caption(f"💡 Last ingested: `{repo_id}`")

    if st.button("🛡️ Run Health Audit", type="primary", use_container_width=True):
        owner = gk_owner.strip()
        repo = gk_repo.strip()
        if not owner or not repo:
            st.warning("Please fill owner and repo.")
        else:
            with st.spinner("Auditing repository health..."):
                try:
                    r = httpx.get(
                        f"{base_url}/api/v1/gatekeeper/{owner}/{repo}",
                        timeout=30,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        verdict = data.get("verdict", "Unknown")

                        # Show verdict with appropriate styling
                        if "✅" in verdict:
                            st.success(f"**{verdict}**")
                        elif "🟡" in verdict:
                            st.warning(f"**{verdict}**")
                        else:
                            st.error(f"**{verdict}**")

                        # Metrics
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("❤️ Liveness", data.get("liveness", "unknown").title())
                        m2.metric("📅 Days Since Push", data.get("days_since_push", "?"))
                        m3.metric("🔀 Open PRs", data.get("open_prs", "?"))
                        m4.metric("📦 Dependencies", data.get("dependency_count", 0))

                        # Warnings
                        warnings = data.get("warnings", [])
                        if warnings:
                            st.markdown("### ⚠️ Warnings")
                            for w in warnings:
                                st.markdown(f"- {w}")

                        with st.expander("📂 Raw JSON"):
                            st.json(data)
                    else:
                        st.error(f"❌ Error {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"❌ Request failed: `{e}`")

# ===========================================================================
# TAB 11 — REPO BUDDY (Phase 7+8: DevLens Architect)
# ===========================================================================
with tab_buddy:
    st.header("🤖 Repo Buddy — Your AI Pair Programmer")

    # ── Info banner: what the chatbot can do ──
    st.markdown("""
    > **DevLens Architect** is an agentic chatbot that guides you through contributing to any GitHub repo — from picking an issue to pushing your fix.

    | Capability | What it does |
    |---|---|
    | 🐛 **Bug Fix Mode (Exterminator)** | Helps you reproduce, locate, and fix bugs step-by-step |
    | 🏗️ **Feature Mode (Builder)** | Plans where new code fits in the architecture |
    | 🧹 **Refactor Mode (Janitor)** | Ensures dependency safety when cleaning up code |
    | 🎯 **Blast Radius** | Shows which files will break if you touch the target |
    | 📋 **Mission Plans** | Generates actionable checklists (Reproduce → Fix → Verify) |
    | 🚀 **Git Commands** | Ready-to-paste terminal commands with auto-detected setup |

    **How to use:** Enter the repo details, type an issue description (or paste one), and optionally provide an issue number to start a full mission.
    """)

    st.markdown("---")

    # ── Repo inputs ──
    col_b1, col_b2, col_b3 = st.columns([2, 2, 1])
    with col_b1:
        buddy_owner = st.text_input("Owner", placeholder="e.g. pallets", key="buddy_owner")
    with col_b2:
        buddy_repo = st.text_input("Repo", placeholder="e.g. flask", key="buddy_repo")
    with col_b3:
        buddy_issue_num = st.text_input("Issue # (optional)", placeholder="e.g. 42", key="buddy_issue_num")

    # Auto-fill hint from last ingest
    if st.session_state.ingest_result and not buddy_owner:
        repo_id = st.session_state.ingest_result.get("repo_id", "")
        if "/" in repo_id:
            st.caption(f"💡 Tip: Last ingested repo is `{repo_id}`")

    # ── Message type toggle ──
    msg_type = st.radio(
        "Message type",
        ["💬 Chat / Issue Description", "🖥️ Terminal Output"],
        horizontal=True,
        key="buddy_msg_type",
    )
    is_terminal = msg_type.startswith("🖥️")

    # ── Active mission indicator ──
    if st.session_state.active_mission:
        mission = st.session_state.active_mission
        mode_emoji = {"exterminator": "🐛", "builder": "🏗️", "janitor": "🧹"}.get(mission.get("mode", ""), "🤖")
        st.info(f"{mode_emoji} Active Mission: **{mission.get('mission_id', '')}** (Mode: {mission.get('mode', 'unknown')})")

    # ── Display chat history ──
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Chat input ──
    if prompt := st.chat_input("Describe the issue, ask a question, or paste terminal output..."):
        # Display user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build the API payload
        owner = buddy_owner.strip() if buddy_owner else ""
        repo = buddy_repo.strip() if buddy_repo else ""

        if not owner or not repo:
            assistant_msg = "⚠️ Please enter the **Owner** and **Repo** fields above before chatting."
            st.session_state.chat_messages.append({"role": "assistant", "content": assistant_msg})
            with st.chat_message("assistant"):
                st.markdown(assistant_msg)
        else:
            payload = {
                "owner": owner,
                "repo": repo,
                "message": prompt,
                "type": "terminal_output" if is_terminal else "user_chat",
                "user_profile": {
                    "level": st.session_state.get("profile_level", "junior"),
                    "language": st.session_state.get("profile_lang", "English"),
                    "goal": st.session_state.get("profile_goal", "contributing"),
                },
            }

            # If issue number is provided and no active mission, start a new mission
            issue_num_str = buddy_issue_num.strip() if buddy_issue_num else ""
            if issue_num_str.isdigit() and not st.session_state.active_mission:
                payload["issue_number"] = int(issue_num_str)

            # If there's an active mission, include the mission_id
            if st.session_state.active_mission:
                payload["mission_id"] = st.session_state.active_mission.get("mission_id")

            # Call the API
            with st.chat_message("assistant"):
                with st.spinner("🤖 Architect is thinking..."):
                    try:
                        r = httpx.post(
                            f"{base_url}/api/v1/chatbot",
                            json=payload,
                            timeout=120,
                        )
                        if r.status_code == 200:
                            data = r.json()
                            reply = data.get("reply", "No response.")

                            # Update active mission state
                            if data.get("mission_id"):
                                st.session_state.active_mission = {
                                    "mission_id": data["mission_id"],
                                    "mode": data.get("mode"),
                                }

                            st.markdown(reply)

                            # Show structured data in expanders
                            if data.get("relevant_files"):
                                with st.expander("🎯 Relevant Files"):
                                    for f in data["relevant_files"]:
                                        st.markdown(f"- `{f}`")

                            if data.get("blast_radius"):
                                with st.expander("⚠️ Blast Radius"):
                                    for f in data["blast_radius"]:
                                        st.markdown(f"- `{f}`")

                            if data.get("git_commands"):
                                with st.expander("🚀 Git Commands (copy-paste ready)"):
                                    st.code(data["git_commands"], language="bash")

                        else:
                            reply = f"❌ Error {r.status_code}: {r.text}"
                            st.error(reply)

                    except Exception as e:
                        reply = f"❌ Request failed: `{e}`"
                        st.error(reply)

                st.session_state.chat_messages.append({"role": "assistant", "content": reply})

    # ── Clear chat / Reset mission ──
    col_clear1, col_clear2 = st.columns(2)
    with col_clear1:
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
    with col_clear2:
        if st.button("🔄 Reset Mission", use_container_width=True):
            st.session_state.active_mission = None
            st.session_state.chat_messages = []
            st.rerun()
