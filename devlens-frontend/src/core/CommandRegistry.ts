export interface CommandContext {
    args: string[];
    raw: string;
    writeOutput: (text: string, color?: string) => void;
}

export interface Command {
    name: string;
    description: string;
    execute: (ctx: CommandContext) => Promise<void> | void;
}

export const BuiltInCommands = {
    intent: {
        id: 'intent',
        name: 'intent <file>',
        description: 'Discover the architectural intent and history of a specific file',
    },
    architect: {
        id: 'architect',
        name: 'architect <issue>',
        description: 'Start an agentic mission to solve a specific GitHub issue',
    },
};

export const CommandRegistry: Record<string, Command> = {};

export const registerCommand = (cmd: Command) => {
    CommandRegistry[cmd.name] = cmd;
};
