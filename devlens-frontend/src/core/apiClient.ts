const BASE_URL = '/api/v1';
const TIMEOUT_MS = 30_000; // 30 seconds for AI calls

function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    return fetch(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(timer));
}

export const apiClient = {
    get: async (endpoint: string) => {
        let res: Response;
        try {
            res = await fetchWithTimeout(`${BASE_URL}${endpoint}`);
        } catch (err: any) {
            if (err.name === 'AbortError') throw new Error(`Request timed out: ${endpoint}`);
            throw new Error(`Network error: ${err.message}`);
        }
        if (!res.ok) throw new Error(`API error ${res.status}: ${endpoint}`);
        return res.json();
    },
    post: async (endpoint: string, body?: any) => {
        let res: Response;
        try {
            res = await fetchWithTimeout(`${BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: body ? JSON.stringify(body) : undefined,
            });
        } catch (err: any) {
            if (err.name === 'AbortError') throw new Error(`Request timed out: ${endpoint}`);
            throw new Error(`Network error: ${err.message}`);
        }
        if (!res.ok) throw new Error(`API error ${res.status}: ${endpoint}`);
        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return res.json();
        }
        return res.text();
    },

    // --- Phase 6: Good First Issues & PR History ---
    getRecommendedIssues: async (owner: string, repo: string) => {
        return apiClient.get(`/issues/recommend/${owner}/${repo}`);
    },

    getPRHistory: async (owner: string, repo: string) => {
        return apiClient.get(`/history/${owner}/${repo}`);
    },

    // --- Phase 7: Gatekeeper ---
    getGatekeeperStatus: async (owner: string, repo: string) => {
        return apiClient.get(`/gatekeeper/${owner}/${repo}`);
    },

    // --- Phase 7/8: Architect Chatbot ---
    startMission: async (owner: string, repo: string, issueNumber: number, message: string, userProfile: any) => {
        return apiClient.post('/chatbot', {
            owner,
            repo,
            issue_number: issueNumber,
            message,
            user_profile: userProfile
        });
    },

    sendMissionUpdate: async (
        owner: string,
        repo: string,
        message: string,
        missionId: string,
        currentStep: number | null,
        type: 'user_chat' | 'terminal_output',
        userProfile: any
    ) => {
        return apiClient.post('/chatbot', {
            owner,
            repo,
            message,
            mission_id: missionId,
            current_step: currentStep,
            type,
            user_profile: userProfile
        });
    }
};
