import * as vscode from 'vscode';

export class Configuration {
    private config: vscode.WorkspaceConfiguration;

    constructor() {
        this.reload();
    }

    reload(): void {
        this.config = vscode.workspace.getConfiguration('gitfix');
    }

    get enabled(): boolean {
        return this.config.get<boolean>('enabled', true);
    }

    get apiUrl(): string {
        return this.config.get<string>('apiUrl', 'http://localhost:5000');
    }

    get wsUrl(): string {
        return this.config.get<string>('wsUrl', 'ws://localhost:5000/ws');
    }

    get autoReview(): boolean {
        return this.config.get<boolean>('autoReview', true);
    }

    get severityThreshold(): string {
        return this.config.get<string>('severityThreshold', 'medium');
    }

    get showInlineAnnotations(): boolean {
        return this.config.get<boolean>('showInlineAnnotations', true);
    }

    get showStatusBar(): boolean {
        return this.config.get<boolean>('showStatusBar', true);
    }

    get realtimeUpdates(): boolean {
        return this.config.get<boolean>('realtimeUpdates', true);
    }

    get languages(): string[] {
        return this.config.get<string[]>('languages', [
            'python', 'typescript', 'javascript', 'go', 'rust', 'java', 'cpp'
        ]);
    }

    get scanDirtyFiles(): boolean {
        return this.config.get<boolean>('scanDirtyFiles', false);
    }

    get maxFileSize(): number {
        return this.config.get<number>('maxFileSize', 1024 * 1024);
    }

    get excludePatterns(): string[] {
        return this.config.get<string[]>('excludePatterns', [
            '**/node_modules/**',
            '**/.git/**',
            '**/dist/**',
            '**/build/**',
            '**/*.min.js',
            '**/*.min.css',
            '**/*.map',
            '**/vendor/**',
            '**/.venv/**',
            '**/__pycache__/**',
            '**/*.pyc',
            '**/*.pyo',
            '**/target/**',
            '**/dist/**',
            '**/build/**',
        ]);
    }

    get scanOnSave(): boolean {
        return this.config.get<boolean>('scanOnSave', true);
    }

    get scanOnType(): boolean {
        return this.config.get<boolean>('scanOnType', false);
    }

    get scanDebounceMs(): number {
        return this.config.get<number>('scanDebounceMs', 500);
    }

    get showInlineFixes(): boolean {
        return this.config.get<boolean>('showInlineFixes', true);
    }

    get showCodeLens(): boolean {
        return this.config.get<boolean>('showCodeLens', true);
    }

    get enableSounds(): boolean {
        return this.config.get<boolean>('enableSounds', false);
    }

    get theme(): 'dark' | 'light' | 'auto' {
        return this.config.get<string>('theme', 'auto') as 'dark' | 'light' | 'auto';
    }

    get accentColor(): string {
        return this.config.get<string>('accentColor', 'magenta');
    }

    get animationEnabled(): boolean {
        return this.config.get<boolean>('animationEnabled', true);
    }

    update(key: string, value: any): Thenable<void> {
        return vscode.workspace.getConfiguration('gitfix').update(key, value, vscode.ConfigurationTarget.Global);
    }
}

export const configuration = new Configuration();