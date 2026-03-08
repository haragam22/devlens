import { useAppStore } from '../../store/useAppStore';
import { motion } from 'framer-motion';
import { ANIMATION } from '../../core/AnimationTimings';

export const CodeViewer = () => {
    const { focusFileContent, selectedFile, mode } = useAppStore();

    if (mode !== 'focus' || !focusFileContent) return null;

    const shortName = selectedFile?.split('/').pop() || 'file';

    return (
        <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ duration: ANIMATION.NORMAL, ease: ANIMATION.EASE as any }}
            className="absolute top-0 right-0 bg-white/5 backdrop-blur-lg border-l border-white/10 z-50 flex flex-col"
            style={{ width: '30%', height: 'calc(100vh - 120px)' }}
        >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                <div className="flex items-center gap-2">
                    <span className="text-primary text-xs font-mono uppercase tracking-widest opacity-50">Focus</span>
                    <span className="text-text text-sm font-mono">{shortName}</span>
                </div>
            </div>

            {/* Code Content */}
            <div className="flex-1 overflow-auto p-4 pb-12">
                <pre className="text-text/90 text-xs font-mono leading-relaxed whitespace-pre-wrap">
                    {focusFileContent.split('\n').map((line, i) => (
                        <div key={i} className="flex hover:bg-white/5 rounded px-1 -mx-1">
                            <span className="text-white/20 select-none w-10 text-right pr-3 flex-shrink-0">{i + 1}</span>
                            <span>{line || ' '}</span>
                        </div>
                    ))}
                </pre>
            </div>
        </motion.div>
    );
};
