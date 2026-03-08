import { useAppStore } from '../../store/useAppStore';
import { StateMachine } from '../../core/StateMachine';
import { motion } from 'framer-motion';

export const CLIButton = () => {
    const { mode } = useAppStore();

    if (mode !== 'feature-explorer') return null;

    const handleLaunch = () => {
        StateMachine.transition('landing');
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.4 }}
            className="fixed bottom-10 right-10 z-[90]"
        >
            <button
                onClick={handleLaunch}
                className="flex items-center gap-3 bg-cyan-500/90 hover:bg-cyan-400 text-slate-900 font-mono text-sm font-semibold px-5 py-3 rounded-xl shadow-[0_0_20px_rgba(6,182,212,0.4)] cursor-pointer transition-colors"
            >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="4 17 10 11 4 5"></polyline>
                    <line x1="12" y1="19" x2="20" y2="19"></line>
                </svg>
                Open Terminal
            </button>
        </motion.div>
    );
};
