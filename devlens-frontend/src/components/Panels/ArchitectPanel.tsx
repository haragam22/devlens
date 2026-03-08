import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/useAppStore';

// Correct Import
import { apiClient as api } from '../../core/apiClient';

export const ArchitectPanel = () => {
    const { missionState, setMissionState, userProfile, repoOwner, repoName } = useAppStore();
    const [inputValue, setInputValue] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const [checkedSteps, setCheckedSteps] = useState<Set<number>>(new Set());

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [missionState.chatHistory]);

    if (!missionState.active) return null;

    const parsePlanSteps = (plan: string | null) => {
        if (!plan) return [];
        // Extract bullet points starting with numbers or - [ ] 
        return plan.split('\n').filter(line => line.match(/^(\d+\.|-\s*\[\s*\])/)).map(line => line.replace(/^(\d+\.|-\s*\[\s*\])\s*/, ''));
    };

    const steps = parsePlanSteps(missionState.plan);

    const toggleStep = (idx: number) => {
        const newSet = new Set(checkedSteps);
        if (newSet.has(idx)) {
            newSet.delete(idx);
        } else {
            newSet.add(idx);
        }
        setCheckedSteps(newSet);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputValue.trim() || !repoOwner || !repoName || !missionState.missionId) return;

        const userText = inputValue;
        setInputValue('');
        setIsSubmitting(true);

        setMissionState({
            chatHistory: [...missionState.chatHistory, { role: 'user', content: userText }]
        });

        const isErrorLog = userText.toLowerCase().includes('error') || userText.includes('Exception') || userText.includes('failed');

        try {
            const resp = await api.sendMissionUpdate(
                repoOwner,
                repoName,
                userText,
                missionState.missionId,
                null,
                isErrorLog ? 'terminal_output' : 'user_chat',
                userProfile
            );

            // Update plan if AI provided a new one
            if (resp.plan) {
                setMissionState({ plan: resp.plan });
            }
            if (resp.git_commands) {
                setMissionState({ gitCommands: resp.git_commands });
            }

            setMissionState({
                chatHistory: [
                    ...useAppStore.getState().missionState.chatHistory,
                    { role: 'assistant', content: resp.reply || 'Acknowledged.' }
                ]
            });
        } catch (e: any) {
            setMissionState({
                chatHistory: [
                    ...useAppStore.getState().missionState.chatHistory,
                    { role: 'system', content: `[Error] Failed to communicate: ${e.message}` }
                ]
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    const renderChatContent = (content: string) => {
        // Simple markdown code block renderer
        const parts = content.split('```');
        return parts.map((part, index) => {
            if (index % 2 !== 0) {
                // It's a code block
                const lines = part.split('\n');
                const lang = lines[0]; // could be python, bash, etc
                const code = lines.slice(1).join('\n');
                return (
                    <div key={index} className="my-2 p-3 bg-slate-900/80 rounded border border-slate-700 font-mono text-xs overflow-x-auto text-slate-300">
                        <div className="text-[10px] text-slate-500 mb-1 uppercase">{lang}</div>
                        {code}
                    </div>
                );
            }
            // It's regular text, split by newlines for formatting
            return <div key={index} className="whitespace-pre-wrap leading-relaxed">{part}</div>;
        });
    };

    const getModeEmoji = (mode: string | null) => {
        if (mode === 'exterminator') return '🐛 Exterminator';
        if (mode === 'builder') return '🏗️ Builder';
        if (mode === 'janitor') return '🧹 Janitor';
        return '🤖 Architect';
    };

    return (
        <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="absolute top-6 bottom-6 right-6 w-[450px] bg-slate-900/80 backdrop-blur-2xl border border-slate-700/50 rounded-2xl shadow-2xl flex flex-col overflow-hidden z-[80]"
        >
            {/* Header */}
            <div className="p-4 border-b border-slate-700/50 bg-slate-900/50 shrink-0">
                <div className="flex items-center justify-between mb-2">
                    <h2 className="text-cyan-400 font-mono font-bold tracking-widest uppercase text-sm">
                        Mission: Issue #{missionState.issueNumber}
                    </h2>
                    <span className="text-xs font-mono px-2 py-1 bg-slate-800 rounded text-slate-300 border border-slate-700">
                        {getModeEmoji(missionState.mode)}
                    </span>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar space-y-6">

                {/* Blast Radius & Relevant Files Context */}
                {(missionState.relevantFiles.length > 0 || missionState.blastRadius.length > 0) && (
                    <div className="space-y-3">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Contextual Scope</h3>
                        <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50 text-xs font-mono space-y-3">
                            {missionState.relevantFiles.length > 0 && (
                                <div>
                                    <div className="text-cyan-500/80 mb-1">Target Files:</div>
                                    <ul className="list-disc list-inside text-slate-300 ml-1 space-y-0.5">
                                        {missionState.relevantFiles.map((f, i) => <li key={i}>{f}</li>)}
                                    </ul>
                                </div>
                            )}
                            {missionState.blastRadius.length > 0 && (
                                <div>
                                    <div className="text-orange-500/80 mb-1">⚠️ Blast Radius:</div>
                                    <ul className="list-disc list-inside text-slate-300 ml-1 space-y-0.5">
                                        {missionState.blastRadius.map((f, i) => <li key={i}>{f}</li>)}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Git Commands */}
                {missionState.gitCommands && (
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Environment Setup</h3>
                            <button
                                onClick={() => navigator.clipboard.writeText(missionState.gitCommands!)}
                                className="text-[10px] uppercase font-mono bg-slate-800 hover:bg-slate-700 text-cyan-400 px-2 py-1 rounded border border-slate-600 transition-colors"
                            >
                                Copy
                            </button>
                        </div>
                        <div className="bg-black/50 p-3 rounded-lg border border-slate-800 font-mono text-xs text-green-400 overflow-x-auto whitespace-pre">
                            {missionState.gitCommands}
                        </div>
                    </div>
                )}

                {/* Mission Plan Checklist */}
                {steps.length > 0 && (
                    <div className="space-y-3">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Tactical Plan</h3>
                        <div className="space-y-2">
                            {steps.map((step, idx) => (
                                <div
                                    key={idx}
                                    className={`flex items-start gap-3 p-3 rounded-lg border transition-all cursor-pointer ${checkedSteps.has(idx)
                                        ? 'bg-slate-800/30 border-slate-700/30 opacity-60'
                                        : 'bg-slate-800/80 border-slate-700 hover:border-cyan-500/50'
                                        }`}
                                    onClick={() => toggleStep(idx)}
                                >
                                    <div className={`mt-0.5 w-4 h-4 rounded border flex items-center justify-center shrink-0 ${checkedSteps.has(idx) ? 'bg-cyan-500 border-cyan-500 text-slate-900' : 'border-slate-500'
                                        }`}>
                                        {checkedSteps.has(idx) && <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                                    </div>
                                    <div className={`text-sm ${checkedSteps.has(idx) ? 'line-through text-slate-500' : 'text-slate-200'}`}>
                                        {renderChatContent(step)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Chat Feed */}
                <div className="space-y-4 pt-4 border-t border-slate-700/50">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Mission Log</h3>
                    <AnimatePresence initial={false}>
                        {missionState.chatHistory.map((msg, idx) => (
                            <motion.div
                                key={idx}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`text-sm p-3 rounded-lg border ${msg.role === 'user'
                                    ? 'bg-cyan-900/20 border-cyan-900/50 text-cyan-100 ml-8'
                                    : msg.role === 'system'
                                        ? 'bg-red-900/20 border-red-900/50 text-red-200 text-xs py-2'
                                        : 'bg-slate-800/50 border-slate-700/50 text-slate-300 mr-8'
                                    }`}
                            >
                                {renderChatContent(msg.content)}
                            </motion.div>
                        ))}
                        {isSubmitting && (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-1 p-3 bg-slate-800/50 border border-slate-700/50 rounded-lg w-16 items-center justify-center">
                                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Form */}
            <div className="p-4 bg-slate-900 border-t border-slate-700/50 shrink-0">
                <form onSubmit={handleSubmit} className="flex gap-2">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder="Ask a question or paste terminal output..."
                        className="flex-1 bg-slate-800 text-sm text-slate-200 px-4 py-2.5 rounded-lg border border-slate-700 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-all placeholder:text-slate-500 font-mono"
                        disabled={isSubmitting}
                    />
                    <button
                        type="submit"
                        disabled={isSubmitting || !inputValue.trim()}
                        className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-mono text-sm tracking-wider uppercase transition-colors"
                    >
                        Send
                    </button>
                </form>
            </div>
        </motion.div>
    );
};
