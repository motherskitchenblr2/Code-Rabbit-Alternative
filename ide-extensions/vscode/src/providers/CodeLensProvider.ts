import * as vscode from 'vscode';
import { Configuration } from '../configuration';

export class CodeLensProvider implements vscode.CodeLensProvider {
    private config: Configuration;
    private onDidChangeCodeLensesEmitter = new vscode.EventEmitter<void>();
    public readonly onDidChangeCodeLenses = this.onDidChangeCodeLensesEmitter.event;

    private codeLensCache: Map<string, vscode.CodeLens[]> = new Map();

    constructor(config: Configuration) {
        this.config = config;
    }

    provideCodeLenses(document: vscode.TextDocument, token: vscode.CancellationToken): vscode.CodeLens[] {
        if (!this.config.showCodeLens) {
            return [];
        }

        const cacheKey = document.uri.toString();
        if (this.codeLensCache.has(cacheKey)) {
            return this.codeLensCache.get(cacheKey)!;
        }

        const codeLenses: vscode.CodeLens[] = [];

        // Add scan lens
        const scanLens = new vscode.CodeLens(
            new vscode.Range(0, 0, 0, 0),
            {
                title: '$(search) Scan with Git-Fix',
                command: 'gitfix.scanFile',
                tooltip: 'Scan this file for security issues and code quality',
            }
        );
        codeLenses.push(scanLens);

        this.codeLensCache.set(document.uri.toString(), codeLenses);
        return codeLenses;
    }

    resolveCodeLens(codeLens: vscode.CodeLens, token: vscode.CancellationToken): vscode.CodeLens {
        return codeLens;
    }

    invalidateCache(document: vscode.TextDocument): void {
        this.codeLensCache.delete(document.uri.toString());
    }

    updateCache(document: vscode.TextDocument, findings: any[]): void {
        const cacheKey = document.uri.toString();
        const codeLenses: vscode.CodeLens[] = [];

        const criticalCount = findings.filter(f => f.severity === 'critical').length;
        const highCount = findings.filter(f => f.severity === 'high').length;
        const mediumCount = findings.filter(f => f.severity === 'medium').length;
        const lowCount = findings.filter(f => f.severity === 'low').length;

        if (criticalCount > 0 || highCount > 0 || mediumCount > 0 || lowCount > 0) {
            const range = new vscode.Range(0, 0, 0, 0);
            const badgeLens = new vscode.CodeLens(
                new vscode.Range(0, 0, 0, 0),
                {
                    title: `$(error) ${criticalCount}  $(warning) ${highCount}  $(info) ${mediumCount}  $(check) ${lowCount}`,
                    command: 'gitfix.showFindings',
                    tooltip: `${findings.length} findings - Click to view`,
                }
            );
            codeLenses.push(badgeLens);
        }

        const scanLens = new vscode.CodeLens(
            new vscode.Range(0, 0, 0, 0),
            {
                title: '$(search) Scan with Git-Fix',
                command: 'gitfix.scanFile',
            }
        );
        codeLenses.push(scanLens);

        this.codeLensCache.set(document.uri.toString(), codeLenses);
        this.onDidChangeCodeLensesEmitter.fire();
    }

    clearCache(): void {
        this.codeLensCache.clear();
    }

    clearDocumentCache(document: vscode.TextDocument): void {
        this.codeLensCache.delete(document.uri.toString());
    }
}