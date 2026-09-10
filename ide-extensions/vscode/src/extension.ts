import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { GitFixClient } from './client';
import { FindingsPanel } from './panels/FindingsPanel';
import { PipelinePanel } from './panels/PipelinePanel';
import { RepositoriesPanel } from './panels/RepositoriesPanel';
import { SettingsPanel } from './panels/SettingsPanel';
import { DiagnosticProvider } from './providers/DiagnosticProvider';
import { CodeLensProvider } from './providers/CodeLensProvider';
import { Configuration } from './configuration';

export class GitFixExtension {
    private client: GitFixClient;
    private findingsPanel: FindingsPanel;
    private pipelinePanel: PipelinePanel;
    private repositoriesPanel: RepositoriesPanel;
    private settingsPanel: SettingsPanel;
    private diagnosticProvider: DiagnosticProvider;
    private codeLensProvider: CodeLensProvider;
    private config: Configuration;
    private statusBarItem: vscode.StatusBarItem;
    private outputChannel: vscode.OutputChannel;

    constructor(private context: vscode.ExtensionContext) {
        this.config = new Configuration();
        this.client = new GitFixClient(this.config);
        this.outputChannel = vscode.window.createOutputChannel('Git-Fix');
        
        // Initialize panels
        this.findingsPanel = new FindingsPanel(this.context, this.client);
        this.pipelinePanel = new PipelinePanel(this.context, this.client);
        this.repositoriesPanel = new RepositoriesPanel(this.context, this.client);
        this.settingsPanel = new SettingsPanel(this.context, this.config);
        
        // Initialize providers
        this.diagnosticProvider = new DiagnosticProvider(this.client);
        this.codeLensProvider = new CodeLensProvider(this.client);
        
        // Create status bar item
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        
        this.registerCommands();
        this.registerEventListeners();
        this.updateStatusBar();
    }

    private registerCommands(): void {
        const commands = [
            vscode.commands.registerCommand('gitfix.scanFile', () => this.scanCurrentFile()),
            vscode.commands.registerCommand('gitfix.scanWorkspace', () => this.scanWorkspace()),
            vscode.commands.registerCommand('gitfix.openDashboard', () => this.openDashboard()),
            vscode.commands.registerCommand('gitfix.showFindings', () => this.findingsPanel.show()),
            vscode.commands.registerCommand('gitfix.applyFix', (args) => this.applyFix(args)),
            vscode.commands.registerCommand('gitfix.dismissFinding', (args) => this.dismissFinding(args)),
            vscode.commands.registerCommand('gitfix.configure', () => this.settingsPanel.show()),
            vscode.commands.registerCommand('gitfix.viewReport', () => this.openReport()),
            vscode.commands.registerCommand('gitfix.toggleAutoReview', () => this.toggleAutoReview()),
            vscode.commands.registerCommand('gitfix.refresh', () => this.refresh()),
        ];

        this.context.subscriptions.push(...commands);
    }

    private registerEventListeners(): void {
        // Watch for configuration changes
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('gitfix')) {
                this.config.reload();
                this.client.updateConfig(this.config);
                this.updateStatusBar();
            }
        });

        // Auto-scan on save
        vscode.workspace.onDidSaveTextDocument(doc => {
            if (this.config.autoReview && this.shouldScanDocument(doc)) {
                this.scanDocument(doc);
            }
        });

        // Watch for file changes
        const watcher = vscode.workspace.createFileSystemWatcher('**/*');
        watcher.onDidChange(uri => this.onFileChange(uri));
        watcher.onDidCreate(uri => this.onFileChange(uri));
        this.context.subscriptions.push(watcher);

        // WebSocket connection
        this.client.onFindingsUpdate(findings => this.onFindingsUpdate(findings));
        this.client.onPipelineUpdate(pipeline => this.onPipelineUpdate(pipeline));
        this.client.onConnectionChange(connected => this.updateConnectionStatus(connected));
    }

    private async scanCurrentFile(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        await this.scanDocument(editor.document);
    }

    private async scanDocument(document: vscode.TextDocument): Promise<void> {
        if (!this.shouldScanDocument(document)) {
            return;
        }

        const code = document.getText();
        const language = document.languageId;
        const filePath = vscode.workspace.asRelativePath(document.uri);

        try {
            this.updateStatusBar('scanning');
            const findings = await this.client.scanCode(code, language, filePath);
            this.updateDiagnostics(document, findings);
            this.updateStatusBar('ready');
        } catch (error) {
            this.outputChannel.appendLine(`Scan failed: ${error}`);
            this.updateStatusBar('error');
        }
    }

    private shouldScanDocument(document: vscode.TextDocument): boolean {
        if (!this.config.enabled) return false;
        if (!this.config.languages.includes(document.languageId)) return false;
        if (document.isUntitled) return false;
        if (document.isDirty && !this.config.scanDirtyFiles) return false;
        
        // Check file size
        const maxSize = this.config.maxFileSize || 1024 * 1024; // 1MB
        if (document.getText().length > maxSize) return false;
        
        // Check excluded patterns
        const relativePath = vscode.workspace.asRelativePath(document.uri);
        for (const pattern of this.config.excludePatterns || []) {
            if (minimatch(relativePath, pattern)) return false;
        }
        
        return true;
    }

    private async scanWorkspace(): Promise<void> {
        const files = await vscode.workspace.findFiles(
            '**/*',
            '**/node_modules/**,**/.git/**,**/dist/**,**/build/**'
        );

        if (files.length === 0) {
            vscode.window.showInformationMessage('No files to scan');
            return;
        }

        const progress = await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Scanning workspace...',
            cancellable: true
        }, async (progress, token) => {
            let scanned = 0;
            const total = files.length;

            for (const file of files) {
                if (token.isCancellationRequested) break;

                try {
                    const doc = await vscode.workspace.openTextDocument(file);
                    if (this.shouldScanDocument(doc)) {
                        const code = doc.getText();
                        const language = doc.languageId;
                        const filePath = vscode.workspace.asRelativePath(doc.uri);
                        
                        await this.client.scanCode(code, doc.languageId, filePath);
                    }
                } catch (error) {
                    this.outputChannel.appendLine(`Failed to scan ${file.fsPath}: ${error}`);
                }

                scanned++;
                progress.report({ increment: 100 / total, message: `Scanned ${scanned}/${total}` });
            }
        });

        vscode.window.showInformationMessage(`Scanned ${files.length} files`);
    }

    private updateDiagnostics(document: vscode.TextDocument, findings: any[]): void {
        if (!this.config.showInlineAnnotations) return;

        const diagnostics: vscode.Diagnostic[] = [];
        
        for (const finding of findings) {
            const line = finding.line_start || finding.line || 0;
            const severity = this.mapSeverity(finding.severity);
            
            const range = new vscode.Range(
                line - 1, 0,
                (finding.line_end || finding.line_end || line), 100
            );

            const diagnostic = new vscode.Diagnostic(range, finding.message, severity);
            diagnostic.code = finding.category;
            diagnostic.source = 'Git-Fix';
            
            // Add related information
            if (finding.suggested_fix) {
                diagnostic.relatedInformation = [
                    new vscode.DiagnosticRelatedInformation(
                        new vscode.Location(document.uri, range),
                        `Suggested fix: ${finding.suggested_fix}`
                    )
                ];
            }

            diagnostics.push(diagnostic);
        }

        this.diagnosticProvider.updateDiagnostics(document.uri, diagnostics);
    }

    private mapSeverity(severity: string): vscode.DiagnosticSeverity {
        switch (severity?.toLowerCase()) {
            case 'critical': return vscode.DiagnosticSeverity.Error;
            case 'high': return vscode.DiagnosticSeverity.Error;
            case 'medium': return vscode.DiagnosticSeverity.Warning;
            case 'low': return vscode.DiagnosticSeverity.Information;
            case 'info': return vscode.DiagnosticSeverity.Hint;
            default: return vscode.DiagnosticSeverity.Information;
        }
    }

    private async applyFix(args: any): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) return;

        const finding = args.finding;
        if (!finding || !finding.suggested_fix) {
            vscode.window.showWarningMessage('No fix available for this finding');
            return;
        }

        const edit = new vscode.WorkspaceEdit();
        const range = new vscode.Range(
            finding.line_start - 1, 0,
            finding.line_end || finding.line_start, 100
        );
        
        edit.replace(editor.document.uri, range, finding.suggested_fix);
        
        const success = await vscode.workspace.applyEdit(edit);
        if (success) {
            vscode.window.showInformationMessage('Fix applied successfully');
            this.dismissFinding(args);
        } else {
            vscode.window.showErrorMessage('Failed to apply fix');
        }
    }

    private dismissFinding(args: any): void {
        const finding = args.finding;
        if (finding) {
            this.client.dismissFinding(finding.id);
            this.findingsPanel.removeFinding(finding.id);
        }
    }

    private openDashboard(): void {
        vscode.env.openExternal(vscode.Uri.parse('http://localhost:5173'));
    }

    private openReport(): void {
        vscode.env.openExternal(vscode.Uri.parse('http://localhost:5173/report'));
    }

    private toggleAutoReview(): void {
        const newValue = !this.config.autoReview;
        this.config.update('autoReview', newValue);
        vscode.window.showInformationMessage(`Auto-review ${newValue ? 'enabled' : 'disabled'}`);
    }

    private refresh(): void {
        this.findingsPanel.refresh();
        this.pipelinePanel.refresh();
        this.repositoriesPanel.refresh();
    }

    private async onFileChange(uri: vscode.Uri): Promise<void> {
        try {
            const doc = await vscode.workspace.openTextDocument(uri);
            if (this.shouldScanDocument(doc)) {
                await this.scanDocument(doc);
            }
        } catch (error) {
            // Ignore errors for binary files etc.
        }
    }

    private onFindingsUpdate(findings: any[]): void {
        this.findingsPanel.update(findings);
        this.updateStatusBar();
    }

    private onPipelineUpdate(pipeline: any): void {
        this.pipelinePanel.update(pipeline);
        this.updateStatusBar();
    }

    private updateConnectionStatus(connected: boolean): void {
        this.statusBarItem.text = connected ? '$(plug) Git-Fix' : '$(plug) Git-Fix (disconnected)';
        this.statusBarItem.color = connected ? '#00ff00' : '#ff00ff';
    }

    private updateStatusBar(status: 'ready' | 'scanning' | 'error' = 'ready'): void {
        const icons = {
            ready: '$(check)',
            scanning: '$(sync~spin)',
            error: '$(error)'
        };
        
        const colors = {
            ready: '#00ff00',
            scanning: '#ff8c00',
            error: '#ff0000'
        };

        this.statusBarItem.text = `${icons[status]} Git-Fix`;
        this.statusBarItem.color = colors[status] as any;
        this.statusBarItem.tooltip = `Git-Fix: ${status}`;
        this.statusBarItem.show();
    }

    private openDashboard(): void {
        vscode.env.openExternal(vscode.Uri.parse('http://localhost:5173'));
    }

    private openReport(): void {
        vscode.env.openExternal(vscode.Uri.parse('http://localhost:5173/report'));
    }

    private updateStatusBar(status: 'ready' | 'scanning' | 'error' = 'ready'): void {
        const icons = {
            ready: '$(check)',
            scanning: '$(sync~spin)',
            error: '$(error)'
        };
        
        const colors = {
            ready: '#00ff00',
            scanning: '#ff8c00',
            error: '#ff0000'
        };

        this.statusBarItem.text = `${icons[status]} Git-Fix`;
        this.statusBarItem.color = colors[status] as any;
        this.statusBarItem.tooltip = `Git-Fix: ${status}`;
        this.statusBarItem.show();
    }

    private async onFindingsUpdate(findings: any[]): Promise<void> {
        this.findingsPanel.update(findings);
        this.updateStatusBar();
    }

    private onPipelineUpdate(pipeline: any): void {
        this.pipelinePanel.update(pipeline);
    }

    private updateConnectionStatus(connected: boolean): void {
        this.statusBarItem.text = connected ? '$(plug) Git-Fix' : '$(plug) Git-Fix (disconnected)';
        this.statusBarItem.color = connected ? '#00ff00' : '#ff00ff';
    }

    public dispose(): void {
        this.client.dispose();
        this.findingsPanel.dispose();
        this.pipelinePanel.dispose();
        this.repositoriesPanel.dispose();
        this.settingsPanel.dispose();
        this.statusBarItem.dispose();
        this.outputChannel.dispose();
    }
}

export async function activate(context: vscode.ExtensionContext) {
    const extension = new GitFixExtension(context);
    context.subscriptions.push(extension);
}

export function deactivate() {
    // Cleanup handled by dispose()
}