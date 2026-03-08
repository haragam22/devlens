import { FeatureTree2D } from '../components/Graph/FeatureTree2D';
import { CLIButton } from '../components/CLI/CLIButton';
import { motion } from 'framer-motion';

export const FeatureExplorerScene = () => {
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            className="absolute inset-0 w-full h-full z-10 overflow-hidden"
        >
            {/* Minimalist heading — LEFT aligned */}
            <div className="absolute top-6 left-8 z-20 text-left pointer-events-none">
                <h1 className="text-white/80 text-xl font-extralight tracking-[0.4em] uppercase font-mono">
                    DevLens
                </h1>
                <p className="text-white/25 text-[10px] tracking-[0.3em] uppercase mt-0.5 font-mono">
                    Feature Overview
                </p>
                <p className="text-white/30 text-xs mt-3 font-mono leading-relaxed max-w-[320px]">
                    Hover over any feature to learn more.
                    <br />
                    <span className="text-cyan-400/50">Click the terminal button →</span> to start exploring a repository.
                </p>
            </div>

            {/* Tree — inset top by 64px to clear heading */}
            <div className="absolute left-0 right-0 bottom-0 top-16 flex items-center justify-center">
                <FeatureTree2D />
            </div>

            <CLIButton />
        </motion.div>
    );
};
