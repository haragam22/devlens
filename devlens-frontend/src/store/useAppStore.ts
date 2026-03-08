import { create } from 'zustand';

export type AppMode = 'landing' | 'ingesting' | 'cockpit' | 'focus' | 'feature-explorer' | 'architect';

export interface AppStore {
    mode: AppMode;
    repoUrl: string | null;
    repoName: string | null;
    repoOwner: string | null;
    graphData: any | null;
    selectedFile: string | null;
    blastTarget: string | null;
    cliHistory: string[];
    // Phase 3
    focusFileContent: string | null;
    intentData: { intent_summary: string; commits_analyzed: number } | null;
    intentLoading: boolean;
    intentError: string | null;
    explainData: { explanation: string; jargon_terms: { term: string; technical_definition: string; student_analogy: string }[] } | null;
    explainLoading: boolean;
    explainError: string | null;
    // Phase 6/7 - Architect Mode
    missionState: {
        active: boolean;
        missionId: string | null;
        issueNumber: number | null;
        mode: 'exterminator' | 'builder' | 'janitor' | null;
        plan: string | null;
        gitCommands: string | null;
        relevantFiles: string[];
        blastRadius: string[];
        chatHistory: Array<{ role: 'user' | 'assistant' | 'system', content: string }>;
    };
    userProfile: {
        level: "student" | "junior" | "senior";
        language: "english" | "hindi" | "hinglish";
        goal: "learning" | "contributing";
    };

    setMode: (mode: AppMode) => void;
    setRepoUrl: (url: string) => void;
    setRepoConfig: (repoUrl: string, repoOwner: string, repoName: string) => void;
    setGraphData: (data: any) => void;
    setSelectedFile: (file: string | null) => void;
    setBlastTarget: (target: string | null) => void;
    addToHistory: (entry: string) => void;
    clearHistory: () => void;
    setFocusFileContent: (content: string | null) => void;
    setIntentData: (data: AppStore['intentData']) => void;
    setIntentLoading: (loading: boolean) => void;
    setIntentError: (error: string | null) => void;
    setExplainData: (data: AppStore['explainData']) => void;
    setExplainLoading: (loading: boolean) => void;
    setExplainError: (error: string | null) => void;
    setMissionState: (update: Partial<AppStore['missionState']>) => void;
}

export const useAppStore = create<AppStore>((set) => ({
    mode: "feature-explorer",
    repoUrl: null,
    repoName: null,
    repoOwner: null,
    graphData: null,
    selectedFile: null,
    blastTarget: null,
    cliHistory: [],
    focusFileContent: null,
    intentData: null,
    intentLoading: false,
    intentError: null,
    explainData: null,
    explainLoading: false,
    explainError: null,
    missionState: {
        active: false,
        missionId: null,
        issueNumber: null,
        mode: null,
        plan: null,
        gitCommands: null,
        relevantFiles: [],
        blastRadius: [],
        chatHistory: []
    },
    userProfile: {
        level: "student",
        language: "english",
        goal: "learning",
    },

    setMode: (mode) => set({ mode }),
    setRepoUrl: (repoUrl) => set({ repoUrl }),
    setRepoConfig: (repoUrl, repoOwner, repoName) => set({ repoUrl, repoOwner, repoName }),
    setGraphData: (graphData) => set({ graphData }),
    setSelectedFile: (selectedFile) => set({ selectedFile }),
    setBlastTarget: (blastTarget) => set({ blastTarget }),
    addToHistory: (entry) => set((state) => ({ cliHistory: [...state.cliHistory, entry] })),
    clearHistory: () => set({ cliHistory: [] }),
    setFocusFileContent: (focusFileContent) => set({ focusFileContent }),
    setIntentData: (intentData) => set({ intentData }),
    setIntentLoading: (intentLoading) => set({ intentLoading }),
    setIntentError: (intentError) => set({ intentError }),
    setExplainData: (explainData) => set({ explainData }),
    setExplainLoading: (explainLoading) => set({ explainLoading }),
    setExplainError: (explainError) => set({ explainError }),
    setMissionState: (update) => set((state) => ({
        missionState: { ...state.missionState, ...update }
    })),
}));
