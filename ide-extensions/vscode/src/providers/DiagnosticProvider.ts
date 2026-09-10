import * as vscode from 'vscode';
import { GitFixClient, Finding } from './client';

export class DiagnosticProvider {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private client: GitFixClient;

    constructor(client: GitFixClient) {
        this.client = client;
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('gitfix');
    }

    updateDiagnostics(uri: vscode.Uri, findings: any[]): void {
        const diagnostics: vscode.Diagnostic[] = [];

        for (const finding of findings) {
            const line = finding.line_start || finding.line || 0;
            const endLine = finding.line_end || finding.line_end || line;
            
            const severity = this.mapSeverity(finding.severity);
            
            const range = new vscode.Range(
                line - 1, 0,
                endLine, 100
            );

            const diagnostic = new vscode.Diagnostic(range, finding.message, severity);
            diagnostic.code = finding.category;
            diagnostic.source = 'Git-Fix';
            diagnostic.tags = finding.severity === 'info' ? [vscode.DiagnosticTag.Unnecessary] : [];
            
            // Add related information for suggested fixes
            if (finding.suggested_fix) {
                diagnostic.relatedInformation = [
                    new vscode.DiagnosticRelatedInformation(
                        new vscode.Location(uri, range),
                        `Suggested fix: ${finding.suggested_fix}`
                    )
                ];
            }

            // Add code actions for fixes
            if (finding.suggested_fix) {
                diagnostic.data = {
                    type: 'gitfix-fix',
                    findingId: finding.id,
                    suggestedFix: finding.suggested_fix,
                    range: range,
                };
            }

            diagnostics.push(diagnostic);
        }

        this.diagnosticCollection.set(uri, diagnostics);
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

    clearDiagnostics(uri: vscode.Uri): void {
        this.diagnosticCollection.delete(uri);
    }

    clearAll(): void {
        this.diagnosticCollection.clear();
    }

    dispose(): void {
        this.diagnosticCollection.dispose();
    }
}