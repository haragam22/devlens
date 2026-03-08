import { MolecularGraph } from '../components/Graph/MolecularGraph';
import { useAppStore } from '../store/useAppStore';
import { SidePanel } from '../components/Graph/SidePanel';
import { CodeViewer } from '../components/Panels/CodeViewer';
import { IntentPanel } from '../components/Panels/IntentPanel';
import { ExplainPanel } from '../components/Panels/ExplainPanel';
import { StateMachine } from '../core/StateMachine';
import { AnimatePresence, motion } from 'framer-motion';
import { ANIMATION } from '../core/AnimationTimings';
import { ArchitectPanel } from '../components/Panels/ArchitectPanel';

export const CockpitScene = () => {
    const { mode, selectedFile, setBlastTarget, setSelectedFile, setFocusFileContent } = useAppStore();

    // Hide cockpit entirely during landing or ingesting
    if (mode === 'landing' || mode === 'ingesting') return null;

    // In focus mode, graph shifts left to make room for CodeViewer
    // In architect mode, graph shifts left to make room for ArchitectPanel
    const isFocus = mode === 'focus';
    const isArchitect = mode === 'architect';

    const isFeatureExplorer = mode === 'feature-explorer';

    const handleCloseMap = () => {
        setSelectedFile(null);
        setBlastTarget(null);
        setFocusFileContent(null);
        StateMachine.transition(isFocus ? 'cockpit' : 'landing');
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: isFeatureExplorer ? 0 : 1 }}
            transition={{ duration: ANIMATION.NORMAL }}
            className={`absolute inset-0 w-full h-full overflow-hidden ${isFeatureExplorer ? 'pointer-events-none' : 'pointer-events-auto'}`}
        >
            {/* Graph — 70% in focus, calc in architect, 100% otherwise */}
            <motion.div
                animate={{ width: isFocus ? '70%' : isArchitect ? 'calc(100% - 450px)' : '100%' }}
                transition={{ duration: ANIMATION.NORMAL, ease: ANIMATION.EASE as any }}
                className="absolute top-0 left-0 h-full bg-black"
            >
                <MolecularGraph />
            </motion.div>

            {/* HUD Label */}
            <div className="absolute top-6 left-6 text-primary tracking-widest text-sm opacity-50 z-50 pointer-events-none uppercase font-mono">
                {isFocus ? 'Sector: Focus' : 'Sector: Deep Code'}
            </div>

            {/* Close Map / Exit Focus Button — shifts left when SidePanel is open to not cover its ✕ */}
            <motion.button
                onClick={handleCloseMap}
                animate={{
                    right: (!isFocus && selectedFile) ? 440 : 24
                }}
                transition={{ duration: ANIMATION.NORMAL, ease: ANIMATION.EASE as any }}
                className="absolute top-6 z-[90] bg-white/5 hover:bg-white/10 text-white/70 hover:text-white rounded-full border border-white/10 backdrop-blur-md transition-colors flex items-center gap-2 px-6 py-2 shadow-xl font-mono text-sm uppercase tracking-widest cursor-pointer"
            >
                ✕ {isFocus ? 'Exit Focus' : 'Close Map'}
            </motion.button>

            {/* CodeViewer — right 30% in focus mode, height reduced for 120px terminal */}
            <AnimatePresence>
                {isFocus && <CodeViewer />}
            </AnimatePresence>

            {/* Side Panel for node details — hidden in focus mode (CodeViewer owns right side) */}
            <SidePanel />

            {/*
              Floating Panel Column — stacks IntentPanel and ExplainPanel vertically.
              ALWAYS anchored to the LEFT side to avoid overlap with SidePanel on the right.
            */}
            <div
                className="absolute top-16 left-6 z-[80] flex flex-col gap-3 pointer-events-auto overflow-y-auto"
                style={{ width: 360, maxHeight: 'calc(100vh - 96px)' }}
            >
                <AnimatePresence mode="popLayout">
                    <IntentPanel />
                </AnimatePresence>
                <AnimatePresence mode="popLayout">
                    <ExplainPanel />
                </AnimatePresence>
            </div>

            {/* Architect Panel - displays Agent checklist and chat */}
            <AnimatePresence>
                {isArchitect && <ArchitectPanel />}
            </AnimatePresence>
        </motion.div>
    );
};
