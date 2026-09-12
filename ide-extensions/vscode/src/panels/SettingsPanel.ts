import * as vscode from 'vscode';
import { Configuration } from '../configuration';

export class SettingsPanel {
    private panel: vscode.WebviewPanel | undefined;
    private config: Configuration;
    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext, config: Configuration) {
        this.context = context;
        this.config = config;
    }

    public show(): void {
        if (this.panel) {
            this.panel.reveal(vscode.ViewColumn.One);
            return;
        }

        this.panel = vscode.window.createWebviewPanel(
            'gitfixSettings',
            'Git-Fix Settings',
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
    }

    private handleMessage(message: any): void {
        switch (message.type) {
            case 'saveSettings':
                this.saveSettings(message.settings);
                break;
            case 'resetSettings':
                this.resetSettings();
                break;
            case 'testConnection':
                this.testConnection(message.settings);
                break;
            case 'openConfigFile':
                this.openConfigFile();
                break;
        }
    }

    private async saveSettings(settings: any): Promise<void> {
        try {
            for (const [key, value] of Object.entries(settings)) {
                await this.config.update(key, value);
            }
            vscode.window.showInformationMessage('Settings saved successfully');
        } catch (error) {
            vscode.window.showErrorMessage(`Failed to save settings: ${error}`);
        }
    }

    private async resetSettings(): Promise<void> {
        const confirm = await vscode.window.showWarningMessage(
            'Are you sure you want to reset all settings to defaults?',
            { modal: true },
            'Yes, Reset'
        );
        
        if (confirm === 'Yes, Reset') {
            const defaults = {
                enabled: true,
                apiUrl: 'https://localhost:5000',
                wsUrl: 'wss://localhost:5000/ws',
                autoReview: true,
                severityThreshold: 'medium',
                showInlineAnnotations: true,
                showStatusBar: true,
                realtimeUpdates: true,
                languages: ['python', 'typescript', 'javascript', 'go', 'rust', 'java', 'cpp'],
                scanDirtyFiles: false,
                maxFileSize: 1024 * 1024,
                excludePatterns: [
                    '**/node_modules/**',
                    '**/.git/**',
                    '**/dist/**',
                    '**/build/**',
                    '**/*.min.js',
                    '**/vendor/**'
                ],
                scanOnSave: true,
                scanOnType: false,
                scanDebounceMs: 500,
                showInlineFixes: true,
                showCodeLens: true,
                enableSounds: false,
                theme: 'auto',
                accentColor: 'magenta',
                animationEnabled: true,
                scanDirtyFiles: false,
                maxFileSize: 1024 * 1024,
                scanDebounceMs: 500,
                showInlineFixes: true,
                showCodeLens: true,
                enableSounds: false,
                theme: 'auto',
                accentColor: 'magenta',
                animationEnabled: true,
            };

            for (const [key, value] of Object.entries(defaults)) {
                await this.config.update(key, value);
            }
            
            vscode.window.showInformationMessage('Settings reset to defaults');
            
            // Refresh the panel
            if (this.panel) {
                this.panel.webview.postMessage({
                    type: 'settingsReset',
                    settings: defaults
                });
            }
        }
    }

    private async testConnection(settings: any): Promise<void> {
        // Test connection to Git-Fix API
        vscode.window.showInformationMessage('Testing connection...');
    }

    private async openConfigFile(): Promise<void> {
        const configPath = vscode.workspace.getConfiguration('gitfix').toString();
        vscode.window.showInformationMessage('Opening config file...');
    }

    private getHtml(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Git-Fix Settings</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--vscode-editor-background);
            color: var(--vscode-editor-foreground);
            padding: 24px;
            margin: 0;
        }
        .header {
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .title {
            font-size: 24px;
            font-weight: 600;
        }
        .subtitle {
            color: var(--vscode-descriptionForeground);
            margin-top: 4px;
        }
        .section {
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .section-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        .setting-group {
            margin-bottom: 20px;
        }
        .setting-label {
            display: block;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .setting-description {
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
            margin-top: 4px;
        }
        .input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--vscode-input-border);
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 4px;
            font-size: 13px;
            font-family: inherit;
        }
        .select {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--vscode-input-border);
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 4px;
            font-size: 13px;
            font-family: inherit;
        }
        .checkbox-label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            padding: 8px 0;
        }
        .checkbox-label input[type="checkbox"] {
            width: 16px;
            height: 16px;
            accent-color: var(--vscode-checkbox-background);
        }
        .color-picker {
            width: 60px;
            height: 36px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
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
        .btn-danger {
            background: #ff3333;
            color: white;
        }
        .btn-group {
            display: flex;
            gap: 8px;
            margin-top: 16px;
        }
        .divider {
            height: 1px;
            background: var(--vscode-panel-border);
            margin: 24px 0;
        }
        .tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 500;
            margin: 2px;
        }
        .tag-input {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">⚙️ Git-Fix Settings</h1>
        <p class="subtitle">Configure your Git-Fix experience</p>
    </div>

    <div class="section">
        <h2 class="section-title">🔌 Connection</h2>
        <div class="setting-group">
            <label class="setting-label">API Server URL</label>
            <input type="url" class="input" id="apiUrl" placeholder="http://localhost:5000">
            <p class="setting-description">Git-Fix API server endpoint</p>
        </div>
        <div class="setting-group">
            <label class="setting-label">WebSocket URL</label>
            <input type="url" class="input" id="wsUrl" placeholder="ws://localhost:5000/ws">
            <p class="setting-description">WebSocket endpoint for real-time updates</p>
        </div>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="realtimeUpdates" checked>
                Enable real-time updates
            </label>
        </div>
    </div>

    <div class="divider"></div>

    <div class="section">
        <h2 class="section-title">🛡️ Security & Review</h2>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="enabled" checked>
                Enable Git-Fix
            </label>
        </div>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="autoReview" checked>
                Auto-review on save
            </label>
            <p class="setting-description">Automatically scan files when saved</p>
        </div>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="scanOnType" >
                Scan on type (experimental)
            </label>
            <p class="setting-description">Scan as you type (may impact performance)</p>
        </div>
        <div class="setting-group">
            <label class="setting-label">Severity Threshold</label>
            <select class="select" id="severityThreshold">
                <option value="critical">Critical only</option>
                <option value="high">High and above</option>
                <option value="medium" selected>Medium and above</option>
                <option value="low">Low and above</option>
                <option value="info">All (including info)</option>
            </select>
            <p class="setting-description">Minimum severity to display</p>
        </div>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="showInlineAnnotations" checked>
                Show inline annotations
            </label>
        </div>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="showInlineFixes" checked>
                Show inline fix suggestions
            </label>
        </div>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="showCodeLens" checked>
                Show CodeLens
            </label>
        </div>
    </div>

    <div class="divider"></div>

    <div class="section">
        <h2 class="section-title">🎨 Appearance</h2>
        <div class="setting-group">
            <label class="setting-label">Theme</label>
            <select class="select" id="theme">
                <option value="auto">Auto (System)</option>
                <option value="dark">Dark</option>
                <option value="light">Light</option>
            </select>
        </div>
        <div class="setting-group">
            <label class="setting-label">Accent Color</label>
            <div style="display: flex; gap: 12px; align-items: center;">
                <input type="color" class="color-picker" id="accentColor" value="#ff00ff">
                <select class="select" id="accentColorSelect" style="width: auto;">
                    <option value="magenta">Magenta</option>
                    <option value="cyan">Cyan</option>
                    <option value="amber">Amber</option>
                    <option value="green">Green</option>
                </select>
            </div>
        </div>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="animationEnabled" checked>
                Enable animations
            </label>
        </div>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="enableSounds" >
                Enable sounds
            </label>
        </div>
    </div>

    <div class="divider"></div>

    <div class="section">
        <h2 class="section-title">🌐 Languages</h2>
        <div class="tag-input" id="languageTags">
            <span class="tag" data-lang="python">Python <span class="remove">×</span></span>
            <span class="tag" data-lang="typescript">TypeScript <span class="remove">×</span></span>
            <span class="tag" data-lang="javascript">JavaScript <span class="remove">×</span></span>
            <span class="tag" data-lang="go">Go <span class="remove">×</span></span>
            <span class="tag" data-lang="rust">Rust <span class="remove">×</span></span>
            <span class="tag" data-lang="java">Java <span class="remove">×</span></span>
            <span class="tag" data-lang="cpp">C++ <span class="remove">×</span></span>
        </div>
        <div style="margin-top: 8px;">
            <select class="select" id="addLanguage" style="width: auto;">
                <option value="">Add language...</option>
                <option value="python">Python</option>
                <option value="typescript">TypeScript</option>
                <option value="javascript">JavaScript</option>
                <option value="go">Go</option>
                <option value="rust">Rust</option>
                <option value="java">Java</option>
                <option value="cpp">C++</option>
                <option value="csharp">C#</option>
                <option value="php">PHP</option>
                <option value="ruby">Ruby</option>
                <option value="swift">Swift</option>
                <option value="kotlin">Kotlin</option>
                <option value="scala">Scala</option>
                <option value="ruby">Ruby</option>
            </select>
        </div>
    </div>

    <div class="divider"></div>

    <div class="section">
        <h2 class="section-title">📁 Files & Performance</h2>
        <div class="setting-group">
            <label class="setting-label">Max File Size (bytes)</label>
            <input type="number" class="input" id="maxFileSize" value="1048576" min="1024" max="10485760">
            <p class="setting-description">Maximum file size to scan (default: 1MB)</p>
        </div>
        <div class="setting-group">
            <label class="setting-label">Scan Debounce (ms)</label>
            <input type="number" class="input" id="scanDebounceMs" value="500" min="100" max="5000">
            <p class="setting-description">Debounce time for scan on type</p>
        </div>
        <div class="setting-group">
            <label class="setting-label">Exclude Patterns</label>
            <textarea class="input" id="excludePatterns" rows="4" style="font-family: monospace; font-size: 12px;">**/node_modules/**
**/.git/**
**/dist/**
**/build/**
**/*.min.js
**/vendor/**</textarea>
            <p class="setting-description">Glob patterns to exclude from scanning (one per line)</p>
        </div>
    </div>

    <div class="divider"></div>

    <div class="section">
        <h2 class="section-title">🔔 Notifications</h2>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="showStatusBar" checked>
                Show status bar item
            </label>
        </div>
        <div class="setting-group">
            <label class="setting-label">
                <input type="checkbox" id="enableSounds" >
                Enable notification sounds
            </label>
        </div>
        <div class="setting-group">
            <label class="setting-label">Severity Threshold</label>
            <select class="select" id="severityThreshold">
                <option value="critical">Critical only</option>
                <option value="high">High and above</option>
                <option value="medium" selected>Medium and above</option>
                <option value="low">Low and above</option>
                <option value="info">All (including info)</option>
            </select>
        </div>
    </div>

    <div class="divider"></div>

    <div class="section">
        <h2 class="section-title">🔧 Advanced</h2>
        <div class="setting-group">
            <label class="setting-label">Auto Review</label>
            <select class="select" id="autoReview">
                <option value="true" selected>Enabled</option>
                <option value="false">Disabled</option>
            </select>
        </div>
        <div class="setting-group">
            <label class="setting-label">Scan Dirty Files</label>
            <select class="select" id="scanDirtyFiles">
                <option value="false" selected>No</option>
                <option value="true">Yes</option>
            </select>
        </div>
        <div class="setting-group">
            <label class="setting-label">Scan Debounce (ms)</label>
            <input type="number" class="input" id="scanDebounceMs" value="500" min="100" max="5000">
        </div>
    </div>

    <div class="divider"></div>

    <div class="btn-group">
        <button class="btn btn-primary" onclick="saveSettings()">💾 Save Settings</button>
        <button class="btn btn-secondary" onclick="resetSettings()">🔄 Reset to Defaults</button>
        <button class="btn btn-secondary" onclick="openConfigFile()">📄 Open Config File</button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let currentSettings = {};

        // Load saved settings
        window.addEventListener('message', event => {
            if (event.data.type === 'loadSettings') {
                currentSettings = message.settings;
                applySettings(currentSettings);
            }
        });

        function applySettings(settings) {
            Object.keys(settings).forEach(key => {
                const element = document.getElementById(key);
                if (element) {
                    if (element.type === 'checkbox') {
                        element.checked = settings[key];
                    } else if (element.type === 'select-one') {
                        element.value = settings[key];
                    } else if (element.type === 'text' || element.type === 'url' || element.type === 'number') {
                        element.value = settings[key];
                    } else if (element.tagName === 'TEXTAREA') {
                        element.value = settings[key];
                    }
                }
            });
        }

        function collectSettings() {
            const settings = {};
            document.querySelectorAll('input, select, textarea').forEach(el => {
                if (el.id) {
                    if (el.type === 'checkbox') {
                        settings[el.id] = el.checked;
                    } else {
                        settings[el.id] = el.value;
                    }
                }
            });
            
            // Handle language tags
            const langTags = document.querySelectorAll('.tag[data-lang]');
            settings.languages = Array.from(langTags).map(tag => tag.dataset.lang);
            
            return settings;
        }

        function saveSettings() {
            const settings = collectSettings();
            currentSettings = settings;
            vscode.postMessage({ type: 'saveSettings', settings });
        }

        function resetSettings() {
            if (confirm('Are you sure you want to reset all settings to defaults?')) {
                vscode.postMessage({ type: 'resetSettings' });
            }
        }

        function openConfigFile() {
            vscode.postMessage({ type: 'openConfigFile' });
        }

        // Add language tag
        document.getElementById('addLanguage')?.addEventListener('change', (e) => {
            const lang = e.target.value;
            if (!lang) return;
            
            const container = document.getElementById('languageTags');
            if (!container.querySelector('[data-lang="' + lang + '"]')) {
                const tag = document.createElement('span');
                tag.className = 'tag';
                tag.dataset.lang = lang;
                tag.textContent = lang;
                const remove = document.createElement('span');
                remove.className = 'remove';
                remove.textContent = '×';
                tag.appendChild(remove);
                container.insertBefore(tag, e.target);
                e.target.value = '';
            }
        });

        document.getElementById('languageTags')?.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove')) {
                e.target.parentElement.remove();
            }
        });

        // Color picker sync
        document.getElementById('accentColor')?.addEventListener('input', (e) => {
            document.getElementById('accentColorSelect').value = e.target.value;
        });
        document.getElementById('accentColorSelect')?.addEventListener('change', (e) => {
            document.getElementById('accentColor').value = e.target.value;
        });

        // Tag removal
        document.getElementById('languageTags')?.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove')) {
                e.target.parentElement.remove();
            }
        });

        // Auto-save on change (optional)
        document.querySelectorAll('input, select, textarea').forEach(el => {
            el.addEventListener('change', () => {
                // Auto-save could be enabled here
            });
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