import * as vscode from 'vscode';
import { GitFixClient, PipelineRun, PipelineStage } from '../client';

export class PipelinePanel {
    private panel: vscode.WebviewPanel | undefined;
    private client: GitFixClient;
    private runs: any[] = [];
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
            'gitfixPipeline',
            'Git-Fix Pipeline',
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

    public update(pipeline: any): void {
        if (this.panel) {
            this.panel.webview.postMessage({
                type: 'updatePipeline',
                pipeline
            });
        }
    }

    public refresh(): void {
        this.client.onPipelineUpdate((pipeline) => {
            if (this.panel) {
                this.panel.webview.postMessage({
                    type: 'updatePipeline',
                    pipeline
                });
            }
        });

        this.client.onPipelineRunUpdate((run) => {
            if (this.panel) {
                this.panel.webview.postMessage({
                    type: 'pipelineRunUpdate',
                    run
                });
            }
        });
    }

    private handleMessage(message: any): void {
        switch (message.type) {
            case 'refresh':
                this.refresh();
                break;
            case 'openRun':
                this.openRun(message.runId);
                break;
            case 'retryStage':
                this.retryStage(message.runId, message.stageId);
                break;
            case 'cancelRun':
                this.cancelRun(message.runId);
                break;
        }
    }

    private openRun(runId: string): void {
        // Open run details in a new panel or view
        vscode.window.showInformationMessage(`Opening run ${runId}...`);
    }

    private retryStage(runId: string, stageId: string): void {
        vscode.window.showInformationMessage(`Retrying stage ${stageId}...`);
    }

    private cancelRun(runId: string): void {
        vscode.window.showInformationMessage(`Cancelling run ${runId}...`);
    }

    private getHtml(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Git-Fix Pipeline</title>
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
        .stats {
            display: flex;
            gap: 16px;
            margin-bottom: 16px;
        }
        .stat {
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 8px;
            padding: 12px 16px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: 700;
            font-family: monospace;
        }
        .stat-label {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            text-transform: uppercase;
        }
        .pipeline-visualization {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .stage {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 8px;
        }
        .stage-icon {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        .stage-pending .stage-icon { background: var(--vscode-progressBar-background); }
        .stage-running .stage-icon { background: #ff8c00; animation: pulse 1.5s infinite; }
        .stage-completed .stage-icon { background: #00ff00; }
        .stage-failed .stage-icon { background: #ff3333; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .stage-info {
            flex: 1;
        }
        .stage-name {
            font-weight: 600;
            font-size: 14px;
        }
        .stage-status {
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
            text-transform: capitalize;
        }
        .stage-duration {
            font-family: monospace;
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
        }
        .runs-table {
            margin-top: 24px;
        }
        .table-header {
            display: grid;
            grid-template-columns: 1fr 100px 100px 100px 80px 100px 100px;
            gap: 12px;
            padding: 12px;
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 8px 8px 0 0;
            font-weight: 600;
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
        }
        .run-row {
            display: grid;
            grid-template-columns: 1fr 100px 100px 100px 80px 100px 100px;
            gap: 12px;
            padding: 12px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .run-row:hover {
            background: var(--vscode-list-hoverBackground);
        }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }
        .status-pending { background: var(--vscode-progressBar-background); color: var(--vscode-editor-foreground); }
        .status-running { background: #ff8c00; color: white; animation: pulse 1.5s infinite; }
        .status-completed { background: #00ff00; color: #000; }
        .status-failed { background: #ff3333; color: white; }
        .trigger-badge {
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 500;
            text-transform: uppercase;
        }
        .trigger-webhook { background: #00ffff22; color: #00ffff; }
        .trigger-scheduled { background: #ff8c0022; color: #ff8c00; }
        .trigger-manual { background: #ff00ff22; color: #ff00ff; }
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
        <h1 class="title">⚡ Git-Fix Pipeline</h1>
        <button class="btn btn-primary" onclick="refresh()">
            <span>🔄</span> Refresh
        </button>
    </div>

    <div class="stats">
        <div class="stat">
            <div class="stat-value" id="totalRuns">0</div>
            <div class="stat-label">Total Runs</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="successRate">0%</div>
            <div class="stat-label">Success Rate</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="avgDuration">0s</div>
            <div class="stat-label">Avg Duration</div>
        </div>
        <div class="stat">
            <div class="stat-value" id="activeRuns">0</div>
            <div class="stat-label">Active</div>
        </div>
    </div>

    <div class="pipeline-visualization" id="pipelineViz">
        <div class="stage stage-pending" data-stage="1">
            <div class="stage-icon">🔗</div>
            <div class="stage-info">
                <div class="stage-name">Webhook Ingestion</div>
                <div class="stage-status">Waiting</div>
            </div>
            <div class="stage-duration">-</div>
        </div>
        <div class="stage stage-pending" data-stage="2">
            <div class="stage-icon">🌳</div>
            <div class="stage-info">
                <div class="stage-name">AST Diff Slicing</div>
                <div class="stage-status">Waiting</div>
            </div>
            <div class="stage-duration">-</div>
        </div>
        <div class="stage stage-pending" data-stage="3">
            <div class="stage-icon">🔍</div>
            <div class="stage-info">
                <div class="stage-name">Contextual RAG</div>
                <div class="stage-status">Waiting</div>
            </div>
            <div class="stage-duration">-</div>
        </div>
        <div class="stage stage-pending" data-stage="4">
            <div class="stage-icon">🤖</div>
            <div class="stage-info">
                <div class="stage-name">AI Critic Ensemble</div>
                <div class="stage-status">Waiting</div>
            </div>
            <div class="stage-duration">-</div>
        </div>
        <div class="stage stage-pending" data-stage="5">
            <div class="stage-icon">📝</div>
            <div class="stage-info">
                <div class="stage-name">GitHub Dispatch</div>
                <div class="stage-status">Waiting</div>
            </div>
            <div class="stage-duration">-</div>
        </div>
    </div>

    <div class="runs-table">
        <div class="table-header">
            <div>Run ID</div>
            <div>Trigger</div>
            <div>Started</div>
            <div>Duration</div>
            <div>Findings</div>
            <div>Critical</div>
            <div>Status</div>
        </div>
        <div id="runsContainer" class="runs-container"></div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let runs = [];

        window.addEventListener('message', event => {
            const message = event.data;
            switch (message.type) {
                case 'updatePipeline':
                    updatePipeline(message.pipeline);
                    break;
                case 'pipelineRunUpdate':
                    updateRuns(message.run);
                    break;
            }
        });

        function updatePipeline(pipeline) {
            if (!pipeline) return;
            
            document.getElementById('activeRuns').textContent = pipeline.active_runs || 0;
            
            // Update stage visualization
            if (pipeline.stages) {
                pipeline.stages.forEach((stage, index) => {
                    const stageEl = document.querySelector(\`[data-stage="\${index + 1}"]\`);
                    if (stageEl) {
                        stageEl.className = 'stage stage-' + stage.status;
                        const statusEl = stageEl.querySelector('.stage-status');
                        if (statusEl) statusEl.textContent = stage.status.charAt(0).toUpperCase() + stage.status.slice(1);
                        const durationEl = stageEl.querySelector('.stage-duration');
                        if (durationEl && stage.duration_ms) {
                            durationEl.textContent = (stage.duration_ms / 1000).toFixed(1) + 's';
                        }
                    }
                });
            }
        }

        function updateRuns(run) {
            // Update runs list
            const existingIndex = runs.findIndex(r => r.id === run.id);
            if (existingIndex >= 0) {
                runs[existingIndex] = run;
            } else {
                runs.unshift(run);
            }
            renderRuns();
        }

        function renderRuns() {
            const container = document.getElementById('runsContainer');
            if (!runs.length) {
                container.replaceChildren();
                container.insertAdjacentHTML('beforeend', '<div class="empty-state"><div class="icon">⚡</div><p>No pipeline runs yet</p></div>');
                return;
            }

            const html = runs.slice(0, 20).map(run => \`
                <div class="run-row">
                    <div class="run-id font-mono" title="\${run.id}">\${run.id.substring(0, 12)}...</div>
                    <div><span class="trigger-badge trigger-\${run.trigger}">\${run.trigger}</span></div>
                    <div class="font-mono text-xs">\${new Date(run.started_at).toLocaleString()}</div>
                    <div class="font-mono text-xs">\${run.duration ? (run.duration / 1000).toFixed(1) + 's' : '-'}</div>
                    <div class="font-mono">\${run.findings_count || 0}</div>
                    <div class="font-mono text-red-400">\${run.critical_count || 0}</div>
                    <div>
                        <span class="status-badge status-\${run.status}">\${run.status}</span>
                    </div>
                \`).join('');
            container.replaceChildren();
            container.insertAdjacentHTML('beforeend', html);
        }

        function refresh() {
            vscode.postMessage({ type: 'refresh' });
        }

        // Initial load
        vscode.postMessage({ type: 'getRuns' });
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