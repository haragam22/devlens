import { CommandRegistry } from './CommandRegistry';
import { useAppStore } from '../store/useAppStore';

export const executeCommand = async (
    input: string,
    writeOutput: (text: string, color?: string) => void
) => {
    const store = useAppStore.getState();
    const trimmed = input.trim();
    if (!trimmed) return;

    store.addToHistory(`> ${trimmed}`);
    const parts = trimmed.split(/\s+/);
    const cmdName = parts[0];
    const args = parts.slice(1);
    const command = CommandRegistry[cmdName];

    if (!command) {
        store.addToHistory(`Command not recognized. Type 'help'.`);
        writeOutput(`Command not recognized. Type 'help'.`, '#EF4444');
        return;
    }

    try {
        await command.execute({ args, raw: trimmed, writeOutput });
    } catch (error: any) {
        const errorMsg = error.message || 'Execution failed';
        store.addToHistory(`[Error] ${errorMsg}`);
        writeOutput(errorMsg, '#EF4444');
    }
};
