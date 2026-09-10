import * as vscode from 'vscode';
import axios, { AxiosInstance } from 'axios';
import WebSocket from 'ws';
import { EventEmitter } from 'events';
import { Configuration } from './configuration';

export interface Finding {
    id: string;
    file_path: string;
    line_start: number;
    line_end?: number;
    severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
    category: string;
    message: string;
    suggested_fix?: string;
    confidence: number;
    timestamp: string;
}

export interface PipelineStage {
    id: string;
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    started_at: string;
    completed_at?: string;
    duration_ms?: number;
}

export interface PipelineRun {
    id: string;
    repository: string;
    pr_number: number;
    status: 'pending' | 'running' | 'completed' | 'failed';
    started_at: string;
    completed_at?: string;
    stages: PipelineStage[];
    findings_count: number;
    critical_count: number;
}

export interface ScanResult {
    findings: Finding[];
    pipeline_id: string;
    scan_time_ms: number;
}

export class GitFixClient extends EventEmitter {
    private apiClient: AxiosInstance;
    private ws: WebSocket | null = null;
    private config: any;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;

    constructor(private config: any) {
        this.config = config;
        this.apiClient = axios.create({
            baseURL: config.apiUrl || 'http://localhost:5000',
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        // Add request interceptor for auth
        this.apiClient.interceptors.request.use((config) => {
            const token = this.config.authToken;
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            return config;
        });
    }

    async scanCode(code: string, language: string, filePath: string): Promise<any[]> {
        try {
            const response = await this.apiClient.post('/api/v1/scan', {
                code,
                language,
                file_path: filePath,
            });
            return response.data.findings || [];
        } catch (error) {
            console.error('Scan failed:', error);
            throw error;
        }
    }

    async scanFile(filePath: string): Promise<any[]> {
        const code = await this.readFile(filePath);
        const language = this.getLanguageFromPath(filePath);
        return this.scanCode(code, language, filePath);
    }

    private async readFile(filePath: string): Promise<string> {
        const fs = require('fs');
        return fs.promises.readFile(filePath, 'utf-8');
    }

    private getLanguageFromPath(filePath: string): string {
        const ext = require('path').extname(filePath).toLowerCase();
        const languageMap: Record<string, string> = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.rbx': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.clj': 'clojure',
            '.hs': 'haskell',
            '.ml': 'ocaml',
            '.fs': 'fsharp',
            '.vb': 'vb',
            '.pl': 'perl',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.fish': 'fish',
            '.ps1': 'powershell',
            '.sql': 'sql',
            '.html': 'html',
            '.htm': 'html',
            '.xml': 'xml',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'ini',
            '.md': 'markdown',
            '.mdx': 'mdx',
            '.rst': 'rst',
            '.txt': 'text',
        };
        return languageMap[ext] || 'text';
    }

    async dismissFinding(findingId: string): Promise<void> {
        try {
            await this.api.post(`/api/v1/findings/${findingId}/dismiss`);
        } catch (error) {
            console.error('Failed to dismiss finding:', error);
        }
    }

    async getPipelineRuns(repoId?: string): Promise<any[]> {
        try {
            const params = repoId ? { repo_id: repoId } : {};
            const response = await this.api.get('/api/v1/pipeline/runs', { params });
            return response.data;
        } catch (error) {
            console.error('Failed to fetch pipeline runs:', error);
            return [];
        }
    }

    async getRepositories(): Promise<any[]> {
        try {
            const response = await this.api.get('/api/v1/repositories');
            return response.data;
        } catch (error) {
            console.error('Failed to fetch repositories:', error);
            return [];
        }
    }

    connectWebSocket(): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            return;
        }

        const wsUrl = this.config.wsUrl || 'ws://localhost:5000/ws';
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.emit('connectionChange', true);
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.emit('connectionChange', false);
            this.scheduleReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    private handleWebSocketMessage(message: any): void {
        switch (message.type) {
            case 'findings':
                this.emit('findingsUpdate', message.findings);
                break;
            case 'pipeline':
                this.emit('pipelineUpdate', message.pipeline);
                break;
            case 'pipeline_run':
                this.emit('pipelineRunUpdate', message.pipeline_run);
                break;
            case 'repository':
                this.emit('repositoryUpdate', message.repository);
                break;
            case 'scan_complete':
                this.emit('scanComplete', message.result);
                break;
            default:
                console.log('Unknown message type:', message.type);
        }
    }

    private scheduleReconnect(): void {
        if (this.reconnectAttempts >= 5) {
            console.log('Max reconnect attempts reached');
            return;
        }

        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        this.reconnectAttempts++;

        setTimeout(() => {
            this.connectWebSocket();
        }, delay);
    }

    async dismissFinding(findingId: string): Promise<void> {
        try {
            await this.api.delete(`/api/v1/findings/${findingId}/dismiss`);
        } catch (error) {
            console.error('Failed to dismiss finding:', error);
        }
    }

    async scanCode(code: string, language: string, filePath: string): Promise<any[]> {
        try {
            const response = await this.api.post('/api/v1/scan', {
                code,
                language,
                file_path: filePath,
            });
            return response.data.findings || [];
        } catch (error) {
            console.error('Scan failed:', error);
            throw error;
        }
    }

    async scanFile(filePath: string): Promise<any[]> {
        const fs = require('fs');
        const code = await fs.promises.readFile(filePath, 'utf-8');
        const language = this.getLanguageFromPath(filePath);
        return this.scanCode(code, language, filePath);
    }

    private getLanguageFromPath(filePath: string): string {
        const ext = require('path').extname(filePath).toLowerCase();
        const languageMap: Record<string, string> = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.rbx': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.clj': 'clojure',
            '.hs': 'haskell',
            '.ml': 'ocaml',
            '.fs': 'fsharp',
            '.vb': 'vb',
            '.pl': 'perl',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.fish': 'fish',
            '.ps1': 'powershell',
            '.sql': 'sql',
            '.html': 'html',
            '.htm': 'html',
            '.xml': 'xml',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'ini',
            '.md': 'markdown',
            '.mdx': 'mdx',
            '.rst': 'rst',
            '.txt': 'text',
        };
        const ext = require('path').extname(filePath).toLowerCase();
        return languageMap[ext] || 'text';
    }

    async getPipelineRuns(repoId?: string): Promise<any[]> {
        try {
            const params = repoId ? { repo_id: repoId } : {};
            const response = await this.api.get('/api/v1/pipeline/runs', { params });
            return response.data;
        } catch (error) {
            console.error('Failed to fetch pipeline runs:', error);
            return [];
        }
    }

    async getRepositories(): Promise<any[]> {
        try {
            const response = await this.api.get('/api/v1/repositories');
            return response.data;
        } catch (error) {
            console.error('Failed to fetch repositories:', error);
            return [];
        }
    }

    onFindingsUpdate(callback: (findings: any[]) => void): void {
        this.on('findingsUpdate', callback);
    }

    onPipelineUpdate(callback: (pipeline: any) => void): void {
        this.on('pipelineUpdate', callback);
    }

    onPipelineRunUpdate(callback: (run: any) => void): void {
        this.on('pipelineRunUpdate', callback);
    }

    onRepositoryUpdate(callback: (repo: any) => void): void {
        this.on('repositoryUpdate', callback);
    }

    onScanComplete(callback: (result: any) => void): void {
        this.on('scanComplete', callback);
    }

    onConnectionChange(callback: (connected: boolean) => void): void {
        this.on('connectionChange', callback);
    }

    dispose(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.removeAllListeners();
    }
}