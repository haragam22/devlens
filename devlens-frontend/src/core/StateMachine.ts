import { useAppStore } from '../store/useAppStore';
import type { AppMode } from '../store/useAppStore';

const ALLOWED_TRANSITIONS: Record<AppMode, AppMode[]> = {
    landing: ["ingesting", "cockpit", "feature-explorer"],
    ingesting: ["feature-explorer", "cockpit", "landing"],
    "feature-explorer": ["cockpit", "landing", "ingesting"],
    cockpit: ["focus", "architect", "landing", "feature-explorer"],
    architect: ["cockpit", "feature-explorer", "focus"],
    focus: ["cockpit", "feature-explorer", "architect"]
};

export const StateMachine = {
    transition: (to: AppMode): boolean => {
        const store = useAppStore.getState();
        const currentMode = store.mode;

        if (ALLOWED_TRANSITIONS[currentMode]?.includes(to)) {
            store.setMode(to);
            return true;
        }

        console.error(`Illegal transition blocked: ${currentMode} -> ${to}`);
        return false;
    }
};
