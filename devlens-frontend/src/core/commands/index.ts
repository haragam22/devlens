import { registerCommand } from '../CommandRegistry';
import { useAppStore } from '../../store/useAppStore';
import { StateMachine } from '../StateMachine';
import { apiClient } from '../apiClient';

/** Helper: fuzzy-match a file query against graph nodes */
function findNode(query: string, writeOutput: (t: string, c?: string) => void): any | null {
    const store = useAppStore.getState();
    if (!store.graphData?.nodes?.length) {
        writeOutput('No graph data. Run ingest and map first.', '#EF4444');
        return null;
    }
    const q = query.toLowerCase();
    const allNodes = store.graphData.nodes;
    let match = allNodes.find((n: any) => n.id === q);
    if (!match) {
        const matches = allNodes.filter((n: any) => n.id.toLowerCase().includes(q));
        if (matches.length === 1) {
            match = matches[0];
        } else if (matches.length > 1) {
            writeOutput(`Multiple matches for '${query}':`);
            matches.slice(0, 10).forEach((m: any) => writeOutput(`  ${m.id}`));
            if (matches.length > 10) writeOutput(`  ... and ${matches.length - 10} more`);
            writeOutput('Specify a more precise name.');
            return null;
        }
    }
    if (!match) {
        writeOutput(`No node matching '${query}' found.`, '#EF4444');
        return null;
    }
    return match;
}

/** Extract owner/repo from stored URL */
function getOwnerRepo(): { owner: string; repo: string } | null {
    const url = useAppStore.getState().repoUrl;
    if (!url) return null;
    const m = url.match(/github\.com\/([^/]+)\/([^/]+)/);
    if (!m) return null;
    let repo = m[2];
    if (repo.endsWith('.git')) repo = repo.slice(0, -4);
    return { owner: m[1], repo };
}

export const initCommands = () => {
    registerCommand({
        name: 'help',
        description: 'List all available commands',
        execute: ({ writeOutput }) => {
            writeOutput('Available commands:');
            writeOutput('  help              - Show this help message');
            writeOutput('  ingest <url>      - Ingest a GitHub repository');
            writeOutput('  gatecheck <url>   - Audit repo health before ingestion');
            writeOutput('  map               - View the molecular dependency graph');
            writeOutput('  home              - Return to the Feature Explorer map');
            writeOutput('  blast <file>      - Trigger blast animation on a file node');
            writeOutput('  focus <file>      - Open code viewer for a file');
            writeOutput('  intent <file>     - Show architectural intent from commits');
            writeOutput('  explain <file>    - Jargon buster: simplify code concepts');
            writeOutput('  issues            - Find beginner-friendly issues');
            writeOutput('  history           - View recent merged PRs (Institutional Memory)');
            writeOutput('  setup             - Generate local setup commands for the repo');
            writeOutput('  architect <issue> - Start an agentic mission to solve an issue');
            writeOutput('  clear             - Clear terminal output');
        }
    });

    registerCommand({
        name: 'clear',
        description: 'Clear terminal output',
        execute: ({ writeOutput }) => {
            writeOutput('\x1b[2J\x1b[3J\x1b[H');
        }
    });

    registerCommand({
        name: 'home',
        description: 'Return to the Feature Explorer map',
        execute: async ({ writeOutput }) => {
            const store = useAppStore.getState();
            if (store.mode === 'feature-explorer') {
                writeOutput('Already on the Feature Explorer page.', '#EF4444');
                return;
            }
            if (store.mode === 'ingesting') {
                writeOutput('Cannot navigate while ingesting.', '#EF4444');
                return;
            }
            writeOutput('Returning to Feature Explorer map...');

            // Clean up selections
            store.setSelectedFile(null);
            store.setBlastTarget(null);
            store.setFocusFileContent(null);

            StateMachine.transition('feature-explorer');
        }
    });

    registerCommand({
        name: 'map',
        description: 'View the molecular dependency graph',
        execute: async ({ writeOutput }) => {
            const store = useAppStore.getState();
            if (!store.repoUrl) {
                writeOutput('No repository ingested. Run ingest <url> first.', '#EF4444');
                return;
            }

            try {
                const ids = getOwnerRepo();
                if (!ids) throw new Error('Invalid stored github URL.');

                writeOutput('Connecting to graph database...');
                const data = await apiClient.get(`/repository/graph/${ids.owner}/${ids.repo}`);

                if (data && data.nodes) {
                    const links = (data.edges || []).map((e: any) => ({
                        source: e.source,
                        target: e.target,
                        weight: e.weight || 1
                    }));

                    store.setGraphData({ nodes: data.nodes, links });
                    writeOutput('Graph synchronized. Transferring to cockpit control...');
                    StateMachine.transition('cockpit');
                } else {
                    writeOutput('Graph data malformed.', '#EF4444');
                }
            } catch (e: any) {
                writeOutput(`Map failed: ${e.message}`, '#EF4444');
            }
        }
    });

    registerCommand({
        name: 'gatecheck',
        description: 'Audit repository feasibility before ingestion',
        execute: async ({ args, writeOutput }) => {
            if (args.length === 0) {
                writeOutput('Usage: gatecheck <url>', '#EF4444');
                return;
            }

            const url = args[0].replace(/^<|>$/g, '').trim();
            const match = url.match(/github\.com\/([^/]+)\/([^/]+)/);
            if (!match) {
                writeOutput('Invalid GitHub URL format.', '#EF4444');
                return;
            }

            const owner = match[1];
            let repo = match[2];
            if (repo.endsWith('.git')) repo = repo.slice(0, -4);

            writeOutput(`Scanning repository health for ${owner}/${repo}...`);

            try {
                const data = await apiClient.getGatekeeperStatus(owner, repo);

                // Print the results out
                writeOutput('--- Gatekeeper Verdict ---', '#CBD5E1'); // light slate
                writeOutput(`Repo: ${data.repo_id}`);
                writeOutput(`Liveness: ${data.liveness} (Last push: ${data.days_since_push} days ago)`);
                writeOutput(`Traffic: ${data.open_prs} open PRs (Competition: ${data.competition})`);
                writeOutput(`Complexity: ${data.dependency_count} dependencies (${data.complexity})`);

                let verdictColor = '#10B981'; // green
                if (data.verdict.includes('Moderate') || data.verdict.includes('Mostly Friendly')) verdictColor = '#F59E0B'; // yellow
                if (data.verdict.includes('Not Recommended')) verdictColor = '#EF4444'; // red

                writeOutput(`Verdict: ${data.verdict}`, verdictColor);

                if (data.warnings && data.warnings.length > 0) {
                    data.warnings.forEach((w: string) => writeOutput(w));
                }
            } catch (e: any) {
                writeOutput(`Gatecheck failed: ${e.message}`, '#EF4444');
            }
        }
    });

    registerCommand({
        name: 'setup',
        description: 'Generate local setup commands for the ingested repository',
        execute: async ({ writeOutput }) => {
            const store = useAppStore.getState();
            if (!store.repoUrl) {
                writeOutput('No repository ingested. Please run ingest <url> first.', '#EF4444');
                return;
            }

            const ids = getOwnerRepo();
            if (!ids) {
                writeOutput('Invalid repository loaded.', '#EF4444');
                return;
            }

            writeOutput('🚀 Mission Start: Paste this into your terminal', '#10B981');
            writeOutput(`git clone https://github.com/${ids.owner}/${ids.repo}.git`);
            writeOutput(`cd ${ids.repo}`);

            // Basic heuristic for package manager
            writeOutput('npm install # (Assuming Node.js project. Use pip for Python, cargo for Rust)');
            writeOutput('npm run dev # Or equivalent start command');
        }
    });

    registerCommand({
        name: 'issues',
        description: 'Find "Good First Issues" recommended for your skill level',
        execute: async ({ writeOutput }) => {
            const store = useAppStore.getState();
            if (!store.repoUrl) {
                writeOutput('No repository ingested. Run ingest <url> first.', '#EF4444');
                return;
            }
            const ids = getOwnerRepo();
            if (!ids) {
                writeOutput('Invalid repository loaded.', '#EF4444');
                return;
            }

            writeOutput('Scanning GitHub for Good First Issues...', '#06B6D4');
            try {
                const data = await apiClient.getRecommendedIssues(ids.owner, ids.repo);
                if (!data.recommended_issues || data.recommended_issues.length === 0) {
                    writeOutput('No beginner-friendly issues found right now.', '#EAB308');
                    return;
                }
                writeOutput(`Found ${data.recommended_issues.length} beginner-friendly issue(s):`);
                data.recommended_issues.forEach((issue: any) => {
                    const statusTag = issue.in_progress ? ' ⚠️ IN PROGRESS' : ' ✅ OPEN';
                    writeOutput(`\n[Issue #${issue.number}] ${issue.title}${statusTag}`, issue.in_progress ? '#EAB308' : '#10B981');
                    writeOutput(`  URL: ${issue.url}`);
                    if (issue.body_preview) {
                        writeOutput(`  Preview: ${issue.body_preview}`);
                    }
                    if (issue.active_prs && issue.active_prs.length > 0) {
                        issue.active_prs.forEach((prUrl: string) => writeOutput(`  Active PR: ${prUrl}`, '#EAB308'));
                    }
                });
            } catch (e: any) {
                writeOutput(`Failed to fetch issues: ${e.message}`, '#EF4444');
            }
        }
    });

    registerCommand({
        name: 'history',
        description: 'View the 5 most recent merged Pull Requests (Institutional Memory)',
        execute: async ({ writeOutput }) => {
            const store = useAppStore.getState();
            if (!store.repoUrl) {
                writeOutput('No repository ingested. Run ingest <url> first.', '#EF4444');
                return;
            }
            const ids = getOwnerRepo();
            if (!ids) {
                writeOutput('Invalid repository loaded.', '#EF4444');
                return;
            }

            writeOutput('Fetching repository PR history (Institutional Memory)...', '#06B6D4');
            try {
                const data = await apiClient.getPRHistory(ids.owner, ids.repo);
                if (!data.pull_requests || data.pull_requests.length === 0) {
                    writeOutput('No merged PR history found.', '#EAB308');
                    return;
                }
                // Show up to 5 most recent merged PRs
                writeOutput(`\nShowing ${Math.min(5, data.pull_requests.length)} of ${data.pull_requests.length} merged PRs:`);
                data.pull_requests.slice(0, 5).forEach((pr: any) => {
                    const mergedDate = pr.merged_at ? new Date(pr.merged_at).toLocaleDateString() : 'Unknown';
                    writeOutput(`\n${pr.title}`, '#8B5CF6');
                    writeOutput(`  Author: ${pr.author || 'Unknown'} | Merged: ${mergedDate}`);
                    writeOutput(`  URL: ${pr.url}`);
                    if (pr.linked_issues && pr.linked_issues.length > 0) {
                        const issueList = pr.linked_issues.map((i: any) => `#${i.number}`).join(', ');
                        writeOutput(`  Closes: ${issueList}`, '#10B981');
                    }
                    if (pr.changed_files && pr.changed_files.length > 0) {
                        const fileList = pr.changed_files.slice(0, 5).join(', ');
                        const extra = pr.changed_files.length > 5 ? ` (+${pr.changed_files.length - 5} more)` : '';
                        writeOutput(`  Files: ${fileList}${extra}`);
                    }
                });
            } catch (e: any) {
                writeOutput(`Failed to fetch history: ${e.message}`, '#EF4444');
            }
        }
    });

    registerCommand({
        name: 'ingest',
        description: 'Ingest a repository',
        execute: async ({ args, writeOutput }) => {
            if (args.length === 0) {
                throw new Error('Usage: ingest <url>');
            }

            const url = args[0].replace(/^<|>$/g, '').trim();
            const store = useAppStore.getState();

            if (StateMachine.transition('ingesting')) {
                store.setRepoUrl(url);
                writeOutput(`Initiating ingestion for ${url}...`);

                try {
                    writeOutput('Connecting to pipeline...');
                    await apiClient.post('/repository/ingest', { github_url: url });

                    const match = url.match(/github\.com\/([^/]+)\/([^/]+)/);
                    if (!match) throw new Error('Invalid GitHub URL format.');
                    const owner = match[1];
                    let repo = match[2];
                    if (repo.endsWith('.git')) repo = repo.slice(0, -4);

                    store.setRepoConfig(url, owner, repo);

                    let isParsing = true;
                    while (isParsing) {
                        await new Promise(r => setTimeout(r, 2000));
                        const statusRes = await apiClient.get(`/repository/status/${owner}/${repo}`);

                        if (statusRes.status === 'completed') {
                            writeOutput('Vectorization complete.');
                            isParsing = false;
                        } else if (statusRes.status === 'failed' || statusRes.status === 'error') {
                            throw new Error('Pipeline parser failed.');
                        } else if (statusRes.status === 'not_found') {
                            throw new Error('Repository tracking lost.');
                        } else {
                            writeOutput('Parsing AST and vectorizing source code...');
                        }
                    }

                    writeOutput("Ingestion complete. Use 'map' to view dependency graph.");
                    StateMachine.transition('landing');
                } catch (e: any) {
                    writeOutput(`Ingestion failed: ${e.message}`, '#EF4444');
                    StateMachine.transition('landing');
                }
            }
        }
    });

    registerCommand({
        name: 'blast',
        description: 'Trigger blast animation on a file node',
        execute: ({ args, writeOutput }) => {
            const store = useAppStore.getState();
            if (!store.graphData?.nodes?.length) {
                writeOutput('No graph data. Run ingest and map first.', '#EF4444');
                return;
            }
            if (store.mode === 'landing' || store.mode === 'ingesting') {
                StateMachine.transition('cockpit');
            }
            if (args.length === 0) {
                writeOutput('Usage: blast <filename>');
                return;
            }

            const match = findNode(args.join(' '), writeOutput);
            if (!match) return;

            writeOutput(`Initiating blast sequence for ${match.id}...`);
            store.setBlastTarget(match.id);
            store.setSelectedFile(match.id);
        }
    });

    // ─── Phase 3 Commands ───

    registerCommand({
        name: 'focus',
        description: 'Open code viewer for a file',
        execute: async ({ args, writeOutput }) => {
            if (args.length === 0) {
                writeOutput('Usage: focus <filename>');
                return;
            }
            const store = useAppStore.getState();
            const ids = getOwnerRepo();
            if (!ids) {
                writeOutput('No repository ingested.', '#EF4444');
                return;
            }

            const match = findNode(args.join(' '), writeOutput);
            if (!match) return;

            writeOutput(`Focusing on ${match.id}...`);
            store.setSelectedFile(match.id);

            // Fetch raw file content from GitHub
            try {
                const rawUrl = `https://raw.githubusercontent.com/${ids.owner}/${ids.repo}/main/${match.id}`;
                const resp = await fetch(rawUrl);
                if (!resp.ok) {
                    // Try master branch
                    const resp2 = await fetch(rawUrl.replace('/main/', '/master/'));
                    if (!resp2.ok) throw new Error('Could not fetch file from GitHub.');
                    store.setFocusFileContent(await resp2.text());
                } else {
                    store.setFocusFileContent(await resp.text());
                }
                writeOutput('Code loaded. Entering focus mode...');
                StateMachine.transition('focus');
            } catch (e: any) {
                writeOutput(`Focus failed: ${e.message}`, '#EF4444');
            }
        }
    });

    registerCommand({
        name: 'intent',
        description: 'Show architectural intent from commit history',
        execute: async ({ args, writeOutput }) => {
            if (args.length === 0) {
                writeOutput('Usage: intent <filename>');
                return;
            }
            const ids = getOwnerRepo();
            if (!ids) {
                writeOutput('No repository ingested.', '#EF4444');
                return;
            }

            const match = findNode(args.join(' '), writeOutput);
            if (!match) return;

            const store = useAppStore.getState();
            // Clear previous + show loading panel immediately
            store.setIntentData(null);
            store.setIntentError(null);
            store.setIntentLoading(true);
            store.setSelectedFile(match.id);

            writeOutput(`Analyzing architectural intent for ${match.id}...`);
            try {
                const data = await apiClient.post('/intent', {
                    owner: ids.owner,
                    repo: ids.repo,
                    file_path: match.id,
                    user_profile: store.userProfile,
                });
                store.setIntentLoading(false);
                store.setIntentData(data);
                writeOutput(`Intent analysis complete — ${data.commits_analyzed} commits analyzed.`);
            } catch (e: any) {
                store.setIntentLoading(false);
                store.setIntentError(e.message || 'Intent analysis failed.');
                writeOutput(`Intent failed: ${e.message}`, '#EF4444');
            }
        }
    });

    registerCommand({
        name: 'explain',
        description: 'Jargon buster: simplify code concepts',
        execute: async ({ args, writeOutput }) => {
            if (args.length === 0) {
                writeOutput('Usage: explain <filename>');
                return;
            }
            const store = useAppStore.getState();
            const ids = getOwnerRepo();
            if (!ids) {
                writeOutput('No repository ingested.', '#EF4444');
                return;
            }

            const match = findNode(args.join(' '), writeOutput);
            if (!match) return;

            // Clear previous + show loading panel immediately
            store.setExplainData(null);
            store.setExplainError(null);
            store.setExplainLoading(true);
            store.setSelectedFile(match.id);

            writeOutput(`Fetching ${match.id} for explanation...`);

            // Get file content
            let content: string;
            try {
                const rawUrl = `https://raw.githubusercontent.com/${ids.owner}/${ids.repo}/main/${match.id}`;
                const resp = await fetch(rawUrl);
                if (!resp.ok) {
                    const resp2 = await fetch(rawUrl.replace('/main/', '/master/'));
                    if (!resp2.ok) throw new Error('Could not fetch file from GitHub.');
                    content = await resp2.text();
                } else {
                    content = await resp.text();
                }
            } catch (e: any) {
                store.setExplainLoading(false);
                store.setExplainError(`Could not fetch file: ${e.message}`);
                writeOutput(`Fetch failed: ${e.message}`, '#EF4444');
                return;
            }

            writeOutput('Sending to AI for jargon analysis...');
            try {
                const data = await apiClient.post('/explain', {
                    content: content.slice(0, 6000),
                    language: store.userProfile.language === 'hinglish' ? 'Hinglish' :
                        store.userProfile.language === 'hindi' ? 'Hindi' : 'English',
                    user_profile: store.userProfile,
                });
                store.setExplainLoading(false);
                store.setExplainData(data);
                writeOutput('Explanation ready — panel opened.');
            } catch (e: any) {
                store.setExplainLoading(false);
                store.setExplainError(e.message || 'Jargon analysis failed.');
                writeOutput(`Explain failed: ${e.message}`, '#EF4444');
            }
        }
    });

    registerCommand({
        name: 'architect',
        description: 'Start an agentic mission to solve a specific GitHub issue',
        execute: async ({ args, writeOutput }) => {
            if (args.length === 0) {
                writeOutput('Usage: architect <issue_number>');
                return;
            }
            const issueNumber = parseInt(args[0], 10);
            if (isNaN(issueNumber)) {
                writeOutput('Issue number must be an integer.', '#EF4444');
                return;
            }

            const store = useAppStore.getState();
            const ids = getOwnerRepo();
            if (!ids) {
                writeOutput('No repository ingested. Run ingest <url> first.', '#EF4444');
                return;
            }

            // Immediately switch to architect mode and show loading
            StateMachine.transition('architect');
            store.setMissionState({
                active: true,
                issueNumber,
                mode: null,
                plan: null,
                gitCommands: null,
                relevantFiles: [],
                blastRadius: [],
                chatHistory: [{ role: 'system', content: `Starting mission for Issue #${issueNumber}...` }]
            });

            writeOutput(`Consulting DevLens Architect for Issue #${issueNumber}...`);

            try {
                const response = await apiClient.startMission(
                    ids.owner,
                    ids.repo,
                    issueNumber,
                    `Plan a fix for issue ${issueNumber}`,
                    store.userProfile
                );

                // Update the mission state with the AI's plan
                store.setMissionState({
                    missionId: response.mission_id,
                    mode: response.mode as any,
                    plan: response.plan,
                    gitCommands: response.git_commands,
                    relevantFiles: response.relevant_files || [],
                    blastRadius: response.blast_radius || [],
                    chatHistory: [
                        ...useAppStore.getState().missionState.chatHistory,
                        { role: 'assistant', content: response.reply || 'Mission planned successfully.' }
                    ]
                });

                writeOutput('Mission ready! Architect Panel opened.');
            } catch (e: any) {
                store.setMissionState({
                    chatHistory: [
                        ...store.missionState.chatHistory,
                        { role: 'system', content: `[Error] ${e.message || 'Failed to start mission'}` }
                    ]
                });
                writeOutput(`Architect failed: ${e.message}`, '#EF4444');
            }
        }
    });
};
