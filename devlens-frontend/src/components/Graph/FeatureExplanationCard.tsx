import type { FeatureData } from './FeatureData';
import { useTypewriter } from './FeatureData';
import { motion } from 'framer-motion';

interface Props {
    feature: FeatureData;
    x: number;
    y: number;
}

export const FeatureExplanationCard = ({ feature, x, y }: Props) => {
    const typedText = useTypewriter(feature.description, 40);

    // Smart positioning: flip card ABOVE the node if node is in the bottom half
    const isBottom = y > 50;
    const preferredTop = isBottom ? y - 190 : y + 60;
    const preferredLeft = x;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.15 } }}
            className="fixed z-[80] flex bg-slate-900/95 border border-slate-600 rounded-xl p-5 shadow-2xl backdrop-blur-xl"
            style={{
                left: `clamp(240px, calc(50% + ${preferredLeft}px), calc(100vw - 240px))`,
                top: `clamp(80px, calc(50% + ${preferredTop}px), calc(100vh - 200px))`,
                width: '440px',
                transform: 'translateX(-50%)',
                pointerEvents: 'none',
                overflow: 'visible',
            }}
        >
            {/* Text on the left */}
            <div className="flex-1 pr-4 pt-1 flex flex-col min-w-0">
                <div className="text-cyan-400 text-sm font-mono uppercase tracking-widest mb-2.5 pb-2 border-b border-slate-700/50">
                    {feature.title}
                </div>
                <div className="text-slate-300 text-sm leading-relaxed font-sans">
                    {typedText}
                    <span className="inline-block w-1.5 h-4 ml-1 bg-cyan-500 animate-pulse"></span>
                </div>
            </div>

            {/* Anime character on the right — overflows the card */}
            <div className="w-[120px] flex-shrink-0 flex items-end justify-center relative" style={{ marginTop: '-30px', marginBottom: '-20px', marginRight: '-10px' }}>
                <img
                    src="/anime_mentor.png"
                    alt="Mentor"
                    className="w-[140px] h-auto object-contain drop-shadow-[0_0_12px_rgba(6,182,212,0.3)]"
                />
            </div>
        </motion.div>
    );
};
