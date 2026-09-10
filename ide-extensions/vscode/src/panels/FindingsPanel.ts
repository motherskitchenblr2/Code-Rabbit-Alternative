import * as vscode from 'vscode';
import { GitFixClient, Finding } from '../client';

export class FindingsPanel {
    private panel: vscode.WebviewPanel | undefined;
    private client: GitFixClient;
    private findings: Finding[] = [];
    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext, client: GitFixClient) {
        this.context = context;
        this.client = client;
    }

    public show(): void {
        if (this.panel) {
            this.panel.reveal(vscode.ViewColumn.One);
            return;
        }

        this.panel = vscode.window.createWebviewPanel(
            'gitfixFindings',
            'Git-Fix Findings',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [
                    vscode.Uri.joinPath(this.context.extensionUri, 'assets')
                ]
            }
        );

        this.panel.webview.html = this.getHtml();
        this.panel.onDidDispose(() => {
            this.panel = undefined;
        }, null, this.context.subscriptions);

        this.panel.webview.onDidReceiveMessage(
            message => this.handleMessage(message),
            undefined,
            this.context.subscriptions
        );

        this.refresh();
    }

    public update(findings: any[]): void {
        this.findings = findings;
        if (this.panel) {
            this.panel.webview.postMessage({
                type: 'updateFindings',
                findings: this.findings
            });
        }
    }

    public refresh(): void {
        // Request latest findings from client
        this.client.onFindingsUpdate((findings) => {
            this.findings = findings;
            if (this.panel) {
                this.panel.webview.postMessage({
                    type: 'updateFindings',
                    findings: this.findings
                });
            }
        });
    }

    private handleMessage(message: any): void {
        switch (message.type) {
            case 'applyFix':
                this.applyFix(message.findingId);
                break;
            case 'dismissFinding':
                this.dismissFinding(message.findingId);
                break;
            case 'openFile':
                this.openFile(message.filePath, message.line);
                break;
            case 'showDetail':
                this.showDetail(message.findingId);
                break;
            case 'filter':
                this.filterFindings(message.filter);
                break;
            case 'sort':
                this.sortFindings(message.sortBy, message.order);
                break;
        }
    }

    private async applyFix(findingId: string): void {
        const finding = this.findings.find(f => f.id === findingId);
        if (!finding || !finding.suggested_fix) {
            vscode.window.showWarningMessage('No fix available for this finding');
            return;
        }

        try {
            const document = await vscode.workspace.openTextDocument(finding.file_path);
            const editor = await vscode.window.showTextDocument(document);
            
            const range = new vscode.Range(
                finding.line_start - 1, 0,
                finding.line_end || finding.line_start, 100
            );

            const edit = new vscode.WorkspaceEdit();
            edit.replace(document.uri, range, finding.suggested_fix);
            
            const success = await vscode.workspace.applyEdit(edit);
            if (success) {
                vscode.window.showInformationMessage('Fix applied successfully');
                this.dismissFinding(findings[0].id); // This would need the actual finding ID
            } else {
                vscode.window.showErrorMessage('Failed to apply fix');
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to apply fix: ${error}`);
        }
    }

    private dismissFinding(findingId: string): void {
        // Remove from local array
        this.findings = this.findings.filter(f => f.id !== findingId);
        this.client.dismissFinding(findingId);
        
        if (this.panel) {
            this.panel.webview.postMessage({
                type: 'dismissFinding',
                findingId
            });
        }
    }

    private openFile(filePath: string, line: number): void {
        vscode.workspace.openTextDocument(finding.file_path).then(doc => {
            vscode.window.showTextDocument(doc).then(editor => {
                const line = finding.line_start - 1;
                editor.selection = new vscode.Selection(line, 0, line, 0);
                editor.revealRange(new vscode.Range(line, 0, line, 0), vscode.TextEditorRevealType.InCenter);
            });
        });
    }

    private showDetail(findingId: string): void {
        const finding = this.findings.find(f => f.id === findingId);
        if (!finding) return;

        const detail = `
# Finding Details

**Severity:** ${finding.severity}
**Category:** ${finding.category}
**File:** ${finding.file_path}:${finding.line_start}
**Confidence:** ${finding.confidence * 100}%

## Message
${finding.message}

${finding.suggested_fix ? `
## Suggested Fix
\`\`\`diff
${finding.suggested_fix}
\`\`\`
` : ''}
`;

        this.panel?.webview.postMessage({
            type: 'showDetail',
            content: detail
        });
    }

    private filterFindings(filter: any): void {
        // Filter logic would be implemented here
        this.panel?.webview.postMessage({
            type: 'filterApplied',
            filter
        });
    }

    private sortFindings(sortBy: string, order: string): void {
        // Sort logic would be implemented here
        this.panel?.webview.postMessage({
            type: 'sorted',
            sortBy,
            order
        });
    }

    private getHtml(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Git-Fix Findings</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
            padding: 16px;
            margin: 0;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .title {
            font-size: 18px;
            font-weight: 600;
        }
        .controls {
            display: flex;
            gap: 8px;
        }
        .filter-input {
            padding: 6px 12px;
            border: 1px solid var(--vscode-input-border);
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 4px;
            font-size: 13px;
        }
        .select {
            padding: 6px 12px;
            border: 1px solid var(--vscode-input-border);
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 4px;
            font-size: 13px;
        }
        .findings-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .finding-card {
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 8px;
        }
        .finding-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }
        .severity-badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .severity-critical { background: #ff3333; color: white; }
        .severity-high { background: #ff8c00; color: white; }
        .severity-medium { background: #ff8c00; color: white; }
        .severity-low { background: #00ff00; color: #000; }
        .severity-info { background: #00ffff; color: #000; }
        .finding-meta {
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
        }
        .finding-message {
            margin: 12px 0;
            line-height: 1.5;
        }
        .code-snippet {
            background: var(--vscode-textCodeBlock-background);
            border-radius: 4px;
            padding: 12px;
            font-family: monospace;
            font-size: 12px;
            overflow-x: auto;
            margin: 8px 0;
        }
        .actions {
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
        }
        .btn-primary {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
        }
        .btn-secondary {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
        }
        .btn-danger {
            background: #ff3333;
            color: white;
        }
        .suggested-fix {
            background: var(--vscode-textCodeBlock-background);
            border-radius: 4px;
            padding: 12px;
            font-family: monospace;
            font-size: 12px;
            margin: 8px 0;
            white-space: pre-wrap;
        }
        .filter-bar {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        .filter-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .filter-label {
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
        }
        .empty-state {
            text-align: center;
            padding: 48px;
            color: var(--vscode-descriptionForeground);
        }
        .empty-state .icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">🔍 Git-Fix Findings</h1>
        <div class="controls">
            <input type="text" class="filter-input" id="searchInput" placeholder="Search findings...">
            <select class="select" id="severityFilter">
                <option value="">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
                <option value="info">Info</option>
            </select>
            <select class="select" id="categoryFilter">
                <option value="">All Categories</option>
                <option value="security">Security</option>
                <option value="logic">Logic</option>
                <option value="style">Style</option>
                <option value="test">Test</option>
                <option value="performance">Performance</option>
            </select>
            <select class="select" id="sortBy">
                <option value="severity">Severity</option>
                <option value="file">File</option>
                <option value="line">Line</option>
                <option value="confidence">Confidence</option>
            </select>
            <select class="select" id="sortOrder">
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
            </select>
        </div>
    </div>
    <div class="filter-bar">
        <div class="filter-group">
            <span class="filter-label">Severity:</span>
            <span id="criticalCount" class="severity-badge severity-critical">0</span>
            <span id="highCount" class="severity-badge severity-high">0</span>
            <span id="mediumCount" class="severity-badge severity-medium">0</span>
            <span id="lowCount" class="severity-badge severity-low">0</span>
            <span id="infoCount" class="severity-badge severity-info">0</span>
        </div>
        <div class="filter-group">
            <span class="filter-label">Total:</span>
            <span id="totalCount" class="badge">0</span>
        </div>
    </div>
    <div id="findingsContainer" class="findings-list"></div>

    <script>
        const vscode = acquireVsCodeApi();
        let findings = [];
        let currentFilter = { severity: '', category: '', search: '' };
        let sortBy = 'severity';
        let sortOrder = 'desc';

        // Receive findings from extension
        window.addEventListener('message', event => {
            const message = event.data;
            switch (message.type) {
                case 'updateFindings':
                    findings = message.findings;
                    renderFindings();
                    updateStats();
                    break;
                case 'dismissFinding':
                    findings = findings.filter(f => f.id !== message.findingId);
                    renderFindings();
                    updateStats();
                    break;
                case 'sorted':
                    sortBy = message.sortBy;
                    sortOrder = message.order;
                    renderFindings();
                    break;
            }
        });

        function renderFindings() {
            const container = document.getElementById('findingsContainer');
            if (!findings || findings.length === 0) {
                container.innerHTML = '<div class="empty-state"><div class="icon">🔍</div><p>No findings found</p></div>';
                return;
            }

            // Filter
            let filtered = findings.filter(f => {
                if (currentFilter.severity && f.severity !== currentFilter.severity) return false;
                if (currentFilter.category && f.category !== currentFilter.category) return false;
                if (currentFilter.search) {
                    const search = currentFilter.search.toLowerCase();
                    return f.message.toLowerCase().includes(search) || 
                           f.file_path.toLowerCase().includes(search);
                }
                return true;
            });

            // Sort
            filtered.sort((a, b) => {
                let aVal = a[sortBy];
                let bVal = b[sortBy];
                if (typeof aVal === 'string') {
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }
                if (sortOrder === 'asc') {
                    return aVal > bVal ? 1 : -1;
                }
                return aVal < bVal ? 1 : -1;
            });

            container.innerHTML = filtered.map(f => \`
                <div class="finding-card" data-id="\${f.id}">
                    <div class="finding-header">
                        <span class="severity-badge severity-\${f.severity}">\${f.severity.toUpperCase()}</span>
                        <span class="badge category-badge">\${f.category}</span>
                        <span class="confidence">\${(f.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div class="finding-meta">
                        <span class="file-path">\${f.file_path}</span>
                        <span class="line">:\${f.line_start}\${f.line_end ? '-\${f.line_end}' : ''}</span>
                        <span class="confidence">Confidence: \${(f.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <p class="finding-message">\${f.message}</p>
                    \${f.code_snippet ? '<div class="code-snippet">\${f.code_snippet}</div>' : ''}
                    \${f.suggested_fix ? '<div class="suggested-fix">\${f.suggested_fix}</div>' : ''}
                    <div class="actions">
                        <button class="btn btn-primary" onclick="applyFix('\${f.id}')">Apply Fix</button>
                        <button class="btn btn-secondary" onclick="openFile('\${f.file_path}', \${f.line_start})">Open File</button>
                        <button class="btn btn-secondary" onclick="showDetail('\${f.id}')">Details</button>
                        <button class="btn btn-danger" onclick="dismissFinding('\${f.id}')">Dismiss</button>
                    </div>
                </div>
            \`).join('');
        }

        function updateStats() {
            const counts = findings.reduce((acc, f) => {
                acc[f.severity] = (acc[f.severity] || 0) + 1;
                return acc;
            }, {});
            document.getElementById('criticalCount').textContent = counts.critical || 0;
            document.getElementById('highCount').textContent = counts.high || 0;
            document.getElementById('mediumCount').textContent = counts.medium || 0;
            document.getElementById('lowCount').textContent = counts.low || 0;
            document.getElementById('infoCount').textContent = counts.info || 0;
            document.getElementById('totalCount').textContent = findings.length;
        }

        function applyFix(id) {
            vscode.postMessage({ type: 'applyFix', findingId: id });
        }

        function dismissFinding(id) {
            vscode.postMessage({ type: 'dismissFinding', findingId: id });
        }

        function openFile(file, line) {
            vscode.postMessage({ type: 'openFile', filePath: file, line });
        }

        function showDetail(id) {
            vscode.postMessage({ type: 'showDetail', findingId: id });
        }

        function filterFindings(filter) {
            currentFilter = filter;
            renderFindings();
        }

        function sortFindings(sortBy, order) {
            vscode.postMessage({ type: 'sort', sortBy, order });
        }

        // Event listeners
        document.getElementById('searchInput')?.addEventListener('input', (e) => {
            currentFilter.search = e.target.value;
            renderFindings();
        });
        document.getElementById('severityFilter')?.addEventListener('change', (e) => {
            currentFilter.severity = e.target.value;
            renderFindings();
        });
        document.getElementById('categoryFilter')?.addEventListener('change', (e) => {
            currentFilter.category = e.target.value;
            renderFindings();
        });
        document.getElementById('sortBy')?.addEventListener('change', (e) => {
            sortBy = e.target.value;
            renderFindings();
        });
        document.getElementById('sortOrder')?.addEventListener('change', (e) => {
            sortOrder = e.target.value;
            renderFindings();
        });

        // Initial render
        renderFindings();
        updateStats();
    </script>
</body>
</html>`;
    }

    public dispose(): void {
        if (this.panel) {
            this.panel.dispose();
            this.panel = undefined;
        }
    }
}