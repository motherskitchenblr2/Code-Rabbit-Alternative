import * as vscode from 'vscode';
import { GitFixClient, Repository } from '../client';

export class RepositoriesPanel {
    private panel: vscode.WebviewPanel | undefined;
    private client: GitFixClient;
    private repositories: any[] = [];
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
            'gitfixRepositories',
            'Git-Fix Repositories',
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

    public update(repositories: any[]): void {
        this.repositories = repositories;
        if (this.panel) {
            this.panel.webview.postMessage({
                type: 'updateRepositories',
                repositories: this.repositories
            });
        }
    }

    public refresh(): void {
        this.client.getRepositories().then(repos => {
            this.repositories = repos;
            if (this.panel) {
                this.panel.webview.postMessage({
                    type: 'updateRepositories',
                    repositories: this.repositories
                });
            }
        }).catch(err => {
            console.error('Failed to fetch repositories:', err);
        });
    }

    private handleMessage(message: any): void {
        switch (message.type) {
            case 'openRepository':
                this.openRepository(message.repoId);
                break;
            case 'scanRepository':
                this.scanRepository(message.repoId);
                break;
            case 'configureRepository':
                this.configureRepository(message.repoId);
                break;
            case 'removeRepository':
                this.removeRepository(message.repoId);
                break;
            case 'addRepository':
                this.addRepository();
                break;
            case 'filter':
                this.filterRepositories(message.filter);
                break;
            case 'sort':
                this.sortRepositories(message.sortBy, message.order);
                break;
        }
    }

    private async openRepository(repoId: string): void {
        vscode.commands.executeCommand('gitfix.openRepository', message.repoId);
    }

    private async scanRepository(repoId: string): void {
        vscode.window.showInformationMessage('Triggering scan for repository...');
    }

    private configureRepository(repoId: string): void {
        vscode.window.showInformationMessage('Opening repository settings...');
    }

    private async removeRepository(repoId: string): void {
        const confirm = await vscode.window.showWarningMessage(
            'Are you sure you want to remove this repository?',
            { modal: true },
            'Yes, Remove'
        );
        
        if (confirm === 'Yes, Remove') {
            // Remove logic here
            vscode.window.showInformationMessage('Repository removed');
        }
    }

    private addRepository(): void {
        const name = await vscode.window.showInputBox({
            prompt: 'Enter repository name (owner/repo)',
            placeHolder: 'owner/repository'
        });
        
        if (name) {
            vscode.window.showInformationMessage(`Adding repository ${name}...`);
        }
    }

    private filterRepositories(filter: any): void {
        // Filter logic
    }

    private sortRepositories(sortBy: string, order: string): void {
        // Sort logic
    }

    private getHtml(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Git-Fix Repositories</title>
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
        .toolbar {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        .btn {
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-primary {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
        }
        .btn-secondary {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
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
        .repos-table {
            width: 100%;
            border-collapse: collapse;
        }
        .repos-table th,
        .repos-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .repos-table th {
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            color: var(--vscode-descriptionForeground);
            background: var(--vscode-editor-background);
        }
        .repo-name {
            font-weight: 500;
            color: var(--vscode-editor-foreground);
        }
        .repo-fullname {
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
        }
        .language-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 10px;
            font-weight: 500;
            text-transform: uppercase;
        }
        .lang-python { background: #3572A522; color: #3572A5; }
        .lang-javascript { background: #F1E05A22; color: #F1E05A; }
        .lang-typescript { background: #2B748922; color: #2B7489; }
        .lang-go { background: #00ADD822; color: #00ADD8; }
        .lang-rust { background: #DEA58422; color: #DEA584; }
        .lang-java { background: #B0721922; color: #B07219; }
        .lang-cpp { background: #F34B7D22; color: #F34B7D; }
        .lang-c { background: #55555522; color: #555555; }
        .lang-csharp { background: #17860022; color: #178600; }
        .lang-php { background: #4F5D9522; color: #4F5D95; }
        .lang-ruby { background: #70151622; color: #701516; }
        .lang-swift { background: #FFAC4522; color: #FFAC45; }
        .lang-kotlin { background: #A97BFF22; color: #A97BFF; }
        .lang-go { background: #00ADD822; color: #00ADD8; }
        .repo-status {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 500;
        }
        .status-active { background: #00ff0022; color: #00ff00; }
        .status-idle { background: #ff8c0022; color: #ff8c00; }
        .status-error { background: #ff333322; color: #ff3333; }
        .visibility-badge {
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 500;
        }
        .visibility-private { background: #ff333322; color: #ff3333; }
        .visibility-public { background: #00ff0022; color: #00ff00; }
        .actions {
            display: flex;
            gap: 4px;
        }
        .btn-sm {
            padding: 4px 8px;
            font-size: 11px;
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
        .toolbar {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">📦 Git-Fix Repositories</h1>
        <div class="toolbar">
            <button class="btn btn-primary" onclick="addRepository()">
                <span>➕</span> Add Repository
            </button>
        </div>
    </div>

    <div class="toolbar">
        <input type="text" class="filter-input" id="searchInput" placeholder="Search repositories...">
        <select class="select" id="statusFilter">
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="idle">Idle</option>
            <option value="error">Error</option>
        </select>
        <select class="select" id="visibilityFilter">
            <option value="">All Visibility</option>
            <option value="private">Private</option>
            <option value="public">Public</option>
        </select>
        <select class="select" id="languageFilter">
            <option value="">All Languages</option>
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
            <option value="go">Go</option>
            <option value="rust">Rust</option>
            <option value="java">Java</option>
            <option value="cpp">C++</option>
        </select>
        <select class="select" id="sortBy">
            <option value="last_scan">Last Scan</option>
            <option value="name">Name</option>
            <option value="language">Language</option>
            <option value="open_prs">Open PRs</option>
        </select>
        <select class="select" id="sortOrder">
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
        </select>
    </div>

    <div class="table-container">
        <table class="repos-table" id="reposTable">
            <thead>
                <tr>
                    <th style="width: 30%">Repository</th>
                    <th style="width: 15%">Language</th>
                    <th style="width: 10%">Visibility</th>
                    <th style="width: 10%">Open PRs</th>
                    <th style="width: 10%">Last Scan</th>
                    <th style="width: 10%">Status</th>
                    <th style="width: 15%">Actions</th>
                </tr>
            </thead>
            <tbody id="reposBody"></tbody>
        </table>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let repositories = [];

        window.addEventListener('message', event => {
            const message = event.data;
            switch (message.type) {
                case 'updateRepositories':
                    repositories = message.repositories;
                    renderRepositories();
                    break;
            }
        });

        function renderRepositories() {
            const tbody = document.getElementById('reposBody');
            if (!repositories || repositories.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><div class="icon">📦</div><p>No repositories configured</p><button class="btn btn-primary" onclick="addRepository()">Add Your First Repository</button></div>';
                return;
            }

            tbody.innerHTML = repositories.map(repo => \`
                <tr data-id="\${repo.id}">
                    <td>
                        <div class="repo-name">\${repo.name}</div>
                        <div class="repo-fullname">\${repo.full_name}</div>
                    </td>
                    <td>
                        <span class="language-badge lang-\${repo.language?.toLowerCase()}">\${repo.language || 'Unknown'}</span>
                    </td>
                    <td>
                        <span class="visibility-badge \${repo.private ? 'visibility-private' : 'visibility-public'}">
                            \${repo.private ? '🔒 Private' : '🌐 Public'}
                        </span>
                    </td>
                    <td>\${repo.open_prs || 0}</td>
                    <td>\${repo.last_scan ? new Date(repo.last_scan).toLocaleString() : 'Never'}</td>
                    <td>
                        <span class="repo-status status-\${repo.status}">\${repo.status.charAt(0).toUpperCase() + repo.status.slice(1)}</span>
                    </td>
                    <td>
                        <div class="actions">
                            <button class="btn btn-sm btn-secondary" onclick="openRepository('\${repo.id}')" title="Open">👁</button>
                            <button class="btn btn-sm btn-secondary" onclick="scanRepository('\${repo.id}')" title="Scan">🔍</button>
                            <button class="btn btn-sm btn-secondary" onclick="configureRepository('\${repo.id}')" title="Configure">⚙️</button>
                            <button class="btn btn-sm btn-danger" onclick="removeRepository('\${repo.id}')" title="Remove">🗑</button>
                        </div>
                    </td>
                </tr>
            \`).join('');
        }

        function addRepository() {
            vscode.postMessage({ type: 'addRepository' });
        }

        function openRepository(repoId) {
            vscode.postMessage({ type: 'openRepository', repoId });
        }

        function scanRepository(repoId) {
            vscode.postMessage({ type: 'scanRepository', repoId });
        }

        function configureRepository(repoId) {
            vscode.postMessage({ type: 'configureRepository', repoId });
        }

        function removeRepository(repoId) {
            if (confirm('Are you sure you want to remove this repository?')) {
                vscode.postMessage({ type: 'removeRepository', repoId });
            }
        }

        // Event listeners
        document.getElementById('searchInput')?.addEventListener('input', (e) => {
            // Filter logic would go here
        });
        document.getElementById('statusFilter')?.addEventListener('change', (e) => {
            // Filter logic
        });
        document.getElementById('visibilityFilter')?.addEventListener('change', (e) => {
            // Filter logic
        });
        document.getElementById('languageFilter')?.addEventListener('change', (e) => {
            // Filter logic
        });
        document.getElementById('sortBy')?.addEventListener('change', (e) => {
            // Sort logic
        });
        document.getElementById('sortOrder')?.addEventListener('change', (e) => {
            // Sort logic
        });
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