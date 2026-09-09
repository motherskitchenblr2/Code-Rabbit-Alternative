import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useWebSocket } from '../contexts/WebSocketContext'
import {
  GitBranch,
  Lock,
  Globe,
  Clock,
  AlertTriangle,
  CheckCircle,
  Bug,
  Code,
  Shield,
  Settings,
  ArrowLeft,
  Play,
  Pause,
  RefreshCw,
  ExternalLink,
  Download,
  Filter,
  Search,
  ChevronRight,
  Terminal,
  Zap,
  Activity,
  BarChart3,
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar } from 'recharts'

// Types
interface Repository {
  id: string
  name: string
  full_name: string
  description: string
  private: boolean
  language: string
  stars: number
  forks: number
  open_prs: number
  last_scan: string
  status: 'active' | 'idle' | 'error'
  created_at: string
  default_branch: string
}

interface Finding {
  id: string
  type: 'security' | 'logic' | 'style' | 'test'
  severity: 'critical' | 'high' | 'medium' | 'low'
  file: string
  line: number
  message: string
  confidence: number
  timestamp: string
  code_snippet?: string
  suggested_fix?: string
}

interface PipelineRun {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at: string
  completed_at?: string
  duration?: number
  findings_count: number
  critical_count: number
  trigger: 'webhook' | 'manual' | 'scheduled'
}

const mockRepo: Repository = {
  id: '1',
  name: 'gitfix-core',
  full_name: 'org/gitfix-core',
  description: 'Core Git-Fix engine with 5-stage pipeline for automated code review',
  private: true,
  language: 'Python',
  stars: 142,
  forks: 28,
  open_prs: 5,
  last_scan: '2 min ago',
  status: 'active',
  created_at: '2024-01-01',
  default_branch: 'main',
}

const mockFindings: any[] = [
  { id: '1', type: 'security', severity: 'critical', file: 'backend/app.py', line: 22, message: 'Hardcoded webhook secret in source code', confidence: 98.5, timestamp: '2024-01-15T10:30:00Z', code_snippet: 'GITHUB_WEBHOOK_SECRET = "code-rabbit-alternative-secret-key"', suggested_fix: 'GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET")' },
  { id: '2', type: 'security', severity: 'high', file: 'backend/app.py', line: 11, message: 'CORS misconfiguration allows all origins', confidence: 92.3, timestamp: '2024-01-15T10:25:00Z', code_snippet: 'CORS(app)', suggested_fix: 'CORS(app, origins=os.environ.get("CORS_ORIGINS", "").split(","))' },
  { id: '3', type: 'security', severity: 'high', file: 'backend/app.py', line: 374, message: 'Debug mode enabled in production', confidence: 95.1, timestamp: '2024-01-15T10:20:00Z', code_snippet: 'app.run(debug=True)', suggested_fix: 'app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")' },
  { id: '4', type: 'logic', severity: 'medium', file: 'backend/hooks/pre-commit.py', line: 45, message: 'Potential path traversal in file path validation', confidence: 85.2, timestamp: '2024-01-15T10:15:00Z', code_snippet: 'full_path = os.path.join(os.getcwd(), file_path)', suggested_fix: 'full_path = os.path.abspath(os.path.join(os.getcwd(), file_path))\nif not full_path.startswith(os.path.abspath(os.getcwd())): return' },
  { id: '5', type: 'style', severity: 'low', file: 'backend/app.py', line: 374, message: 'Debug mode enabled in production config', confidence: 95.1, timestamp: '2024-01-15T10:10:00Z', code_snippet: 'app.run(debug=True)', suggested_fix: 'app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")' },
]

const pipelineRuns: any[] = [
  { id: 'run-001', status: 'completed', started_at: '2024-01-15T10:30:00Z', completed_at: '2024-01-15T10:30:45Z', duration: 45, findings_count: 12, critical_count: 2, trigger: 'webhook' },
  { id: 'run-002', status: 'completed', started_at: '2024-01-15T10:15:00Z', completed_at: '2024-01-15T10:15:38Z', duration: 38, findings_count: 8, critical_count: 1, trigger: 'webhook' },
  { id: 'run-003', status: 'completed', started_at: '2024-01-15T10:00:00Z', completed_at: '2024-01-15T10:00:52Z', duration: 52, findings_count: 15, critical_count: 3, trigger: 'scheduled' },
  { id: 'run-004', status: 'failed', started_at: '2024-01-15T09:45:00Z', completed_at: '2024-01-15T09:45:12Z', duration: 12, findings_count: 0, critical_count: 0, trigger: 'manual' },
  { id: 'run-005', status: 'completed', started_at: '2024-01-15T09:30:00Z', completed_at: '2024-01-15T09:30:41Z', duration: 41, findings_count: 6, critical_count: 0, trigger: 'webhook' },
]

const SEVERITY_COLORS = {
  critical: 'text-red-400 bg-red-900/30 border-red-500/30',
  high: 'text-orange-400 bg-orange-900/30 border-orange-500/30',
  medium: 'text-amber-400 bg-amber-900/30 border-amber-500/30',
  low: 'text-green-400 bg-green-900/30 border-green-500/30',
}

const SEVERITY_ICONS = {
  critical: '🔴',
  high: '🟠',
  medium: '🟡',
  low: '🟢',
}

export default function RepositoryDetail() {
  const { id } = useParams<{ id: string }>()
  const { isConnected, events } = useWebSocket()
  const [activeTab, setActiveTab] = useState<'overview' | 'findings' | 'pipeline' | 'settings'>('overview')
  const [selectedFinding, setSelectedFinding] = useState<any>(null)

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'findings', label: 'Findings', icon: '🔍' },
    { id: 'pipeline', label: 'Pipeline', icon: '⚡' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ]

  return (
    <div className="space-y-8">
      {/* Repository Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div className="flex items-center gap-4">
          <Link to="/repositories" className="p-2 rounded-lg bg-cyber-800/50 hover:bg-cyber-700/50 border border-cyber-700/50 transition-colors">
            <span className="w-5 h-5">←</span>
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-neon-cyan to-neon-magenta flex items-center justify-center text-cyber-900">
                <span className="w-6 h-6">⌘</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold font-display text-white">{'gitfix-core'}</h1>
                <p className="text-cyber-400 text-sm">org/gitfix-core • Private • Python</p>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-cyber-ghost">
            <span className="w-4 h-4">↓</span>
            Export
          </button>
          <button className="btn-cyber-ghost">
            <span className="w-4 h-4">⚙</span>
            Settings
          </button>
          <a href="https://github.com/org/gitfix-core" target="_blank" rel="noopener noreferrer" className="btn-cyber-magenta">
            <span className="w-4 h-4">→</span>
            GitHub
          </a>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard title="Open PRs" value="5" icon="🔀" color="neon-cyan" />
        <StatCard title="Open Findings" value="23" icon="🔍" color="neon-magenta" />
        <StatCard title="Critical" value="2" icon="🔴" color="red" />
        <StatCard title="Last Scan" value="2 min ago" icon="🕐" color="neon-amber" />
      </div>

      {/* Tabs */}
      <div className="card-cyber">
        <div className="border-b border-cyber-700/50">
          <nav className="flex gap-1 p-1" aria-label="Repository tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-neon-magenta/20 text-neon-magenta border-b-2 border-neon-magenta'
                    : 'text-cyber-400 hover:text-cyber-200 hover:bg-cyber-800/50'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'overview' && <OverviewTab repo={mockRepo} />}
          {activeTab === 'findings' && <FindingsTab findings={mockFindings} selectedFinding={selectedFinding} onSelect={setSelectedFinding} />}
          {activeTab === 'pipeline' && <PipelineTab runs={pipelineRuns} />}
          {activeTab === 'settings' && <SettingsTab />}
        </div>
      </div>
    </div>
  )
}

// Sub-components
function StatCard({ title, value, icon, color }: { title: string; value: string | number; icon: string; color: string }) {
  const colorMap: Record<string, string> = {
    'neon-cyan': 'bg-neon-cyan/10 text-neon-cyan',
    'neon-magenta': 'bg-neon-magenta/10 text-neon-magenta',
    'neon-amber': 'bg-neon-amber/10 text-neon-amber',
    red: 'bg-red-500/10 text-red-400',
  }
  return (
    <div className="card-cyber p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-mono text-cyber-400 uppercase tracking-wider mb-1">{title}</p>
          <p className="text-3xl font-bold font-display text-white">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${{
          'neon-cyan': 'bg-neon-cyan/10',
          'neon-magenta': 'bg-neon-magenta/10',
          'neon-amber': 'bg-neon-amber/10',
          red: 'bg-red-500/10',
        }[color] || 'bg-neon-magenta/10'}`}>
          <span className="text-2xl">{icon}</span>
        </div>
      </div>
    </div>
  )
}

function OverviewTab({ repo }: { repo: any }) {
  return (
    <div className="space-y-6">
      {/* Description */}
      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <span className="w-5 h-5">📝</span> Description
        </h3>
        <p className="text-cyber-300 leading-relaxed">{repo.description}</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard label="Default Branch" value="main" icon="🌿" />
        <MetricCard label="Created" value="Jan 1, 2024" icon="📅" />
        <MetricCard label="Default Branch" value="main" icon="🌿" />
        <MetricCard label="Language" value="Python" icon="🐍" />
        <MetricCard label="Stars" value="142" icon="⭐" />
        <MetricCard label="Forks" value="28" icon="🍴" />
      </div>

      {/* Recent Activity Chart */}
      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <span className="w-5 h-5">📈</span> Scan Activity (Last 7 Days)
        </h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={[
              { day: 'Mon', scans: 12, issues: 5 },
              { day: 'Tue', scans: 19, issues: 8 },
              { day: 'Wed', scans: 15, issues: 3 },
              { day: 'Thu', scans: 22, issues: 12 },
              { day: 'Fri', scans: 18, issues: 6 },
              { day: 'Sat', scans: 8, issues: 2 },
              { day: 'Sun', scans: 5, issues: 1 },
            ]}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
              <XAxis dataKey="day" stroke="#6a6a8a" tick={{ fill: '#6a6a8a' }} />
              <YAxis stroke="#6a6a8a" tick={{ fill: '#6a6a8a' }} />
              <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #ff00ff', borderRadius: '8px' }} />
              <Line type="monotone" dataKey="scans" stroke="#ff00ff" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="issues" stroke="#00ffff" strokeWidth={2} dot={false} />
            </LineChart>
          </div>
        </div>
      </div>
    </div>
  )
}

function FindingsTab({ findings, selectedFinding, onSelect }: { findings: any[]; selectedFinding: any; onSelect: (f: any) => void }) {
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all')
  const [search, setSearch] = useState('')

  const filtered = findings.filter(f => {
    if (filter !== 'all' && f.severity !== filter) return false
    if (search && !f.message.toLowerCase().includes(search.toLowerCase()) &&
        !f.file.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-cyber-500">🔍</span>
          <input
            type="text"
            placeholder="Search findings..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input-cyber pl-10"
          />
        </div>
        <div className="flex gap-2">
          {['all', 'critical', 'high', 'medium', 'low'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f as any)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-all ${
                filter === f
                  ? 'bg-neon-magenta/20 text-neon-magenta border border-neon-magenta/30'
                  : 'text-cyber-400 hover:text-cyber-200'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Findings List */}
      <div className="divide-y divide-cyber-700/50">
        {filtered.map((finding) => (
          <FindingCard key={finding.id} finding={finding} selected={selectedFinding?.id === finding.id} onClick={() => onSelect(finding)} />
        ))}
        {filtered.length === 0 && (
          <div className="text-center py-12 text-cyber-500">
            <span className="text-4xl mb-4 block">🔍</span>
            <p>No findings match your filters</p>
          </div>
        )}
      </div>

      {/* Finding Detail Modal */}
      {selectedFinding && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="card-cyber-glow w-full max-w-3xl max-h-[90vh] overflow-hidden animate-in slide-in-from-bottom-4 duration-200">
            <div className="p-6 border-b border-cyber-700/50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={`badge-cyber ${SEVERITY_COLORS[selectedFinding.severity]}`}>{selectedFinding.severity.toUpperCase()}</span>
                <span className="badge-cyber bg-cyber-700 text-cyber-300">{selectedFinding.type}</span>
                <span className="text-xs text-cyber-400 font-mono">{selectedFinding.confidence}%</span>
              </div>
              <button onClick={() => onSelect(null)} className="p-2 rounded-lg hover:bg-cyber-700/50">✕</button>
            </div>
            <div className="p-6 max-h-[60vh] overflow-y-auto">
              <p className="text-cyber-300 mb-4">{selectedFinding.message}</p>
              <div className="mb-4">
                <p className="text-xs font-mono text-cyber-400 mb-2">{selectedFinding.file}:{selectedFinding.line}</p>
                <pre className="bg-cyber-900/50 p-4 rounded-lg overflow-x-auto text-sm"><code>{selectedFinding.code_snippet}</code></pre>
              </div>
              {selectedFinding.suggested_fix && (
                <div className="bg-neon-green/10 border border-neon-green/30 rounded-lg p-4">
                  <p className="text-xs font-mono text-neon-green mb-2">Suggested Fix:</p>
                  <pre className="text-sm"><code>{selectedFinding.suggested_fix}</code></pre>
                </div>
              )}
            </div>
            <div className="p-6 border-t border-cyber-700/50 flex justify-end gap-2">
              <button className="btn-cyber-ghost" onClick={() => onSelect(null)}>Close</button>
              <button className="btn-cyber-magenta">Create Fix PR</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function FindingCard({ finding, selected, onClick }: { finding: any; selected: boolean; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      className={`p-4 cursor-pointer transition-colors ${selected ? 'bg-neon-magenta/10 border-l-4 border-neon-magenta' : 'hover:bg-cyber-800/30'}`}
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl">{SEVERITY_ICONS[finding.severity]}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`badge-cyber ${SEVERITY_COLORS[finding.severity]}`}>{finding.severity.toUpperCase()}</span>
            <span className="badge-cyber bg-cyber-700 text-cyber-300">{finding.type}</span>
            <span className="text-xs text-cyber-400 font-mono">{finding.confidence}%</span>
          </div>
          <p className="text-cyber-300 text-sm mb-1">{finding.message}</p>
          <div className="flex items-center gap-3 text-xs text-cyber-500">
            <span className="font-mono">{finding.file}:{finding.line}</span>
            <span>{new Date(finding.timestamp).toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function PipelineTab({ runs }: { runs: any[] }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Runs" value="247" icon="⚡" color="neon-cyan" />
        <StatCard title="Success Rate" value="98.4%" icon="✅" color="neon-green" />
        <StatCard title="Avg Duration" value="42s" icon="⏱️" color="neon-amber" />
        <StatCard title="Failed" value="3" icon="❌" color="red" />
      </div>

      <div className="card-cyber overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-cyber-700/50">
              <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Run ID</th>
              <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Trigger</th>
              <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Started</th>
              <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Duration</th>
              <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Findings</th>
              <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Critical</th>
              <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className="border-b border-cyber-800/50 hover:bg-cyber-800/30">
                <td className="px-4 py-3 font-mono text-cyber-300">{run.id}</td>
                <td className="px-4 py-3">
                  <span className={`badge-cyber ${run.trigger === 'webhook' ? 'bg-neon-cyan/20 text-neon-cyan' : run.trigger === 'scheduled' ? 'bg-neon-amber/20 text-neon-amber' : 'bg-neon-magenta/20 text-neon-magenta'}`}>
                    {run.trigger}
                  </span>
                </td>
                <td className="px-4 py-3 text-cyber-300 font-mono text-xs">{new Date(run.started_at).toLocaleString()}</td>
                <td className="px-4 py-3 font-mono text-cyber-300">{run.duration}s</td>
                <td className="px-4 py-3 font-mono text-cyber-300">{run.findings_count}</td>
                <td className="px-4 py-3 font-mono text-red-400">{run.critical_count}</td>
                <td className="px-4 py-3">
                  <span className={`badge-cyber ${
                    run.status === 'completed' ? 'bg-neon-green/20 text-neon-green' :
                    run.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                    'bg-neon-amber/20 text-neon-amber'
                  }`}>{run.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SettingsTab() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4">Repository Settings</h3>
        <div className="space-y-4">
          <div>
            <label className="label-cyber">Auto Review</label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" className="w-5 h-5 accent-neon-magenta" defaultChecked />
              <span className="text-cyber-300">Enable automatic reviews on PR open/sync</span>
            </label>
          </div>
          <div>
            <label className="label-cyber">Request Changes</label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" className="w-5 h-5 accent-neon-magenta" />
              <span className="text-cyber-300">Request changes on critical findings</span>
            </label>
          </div>
          <div>
            <label className="label-cyber">High Level Summary</label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" className="w-5 h-5 accent-neon-magenta" defaultChecked />
              <span className="text-cyber-300">Include high-level summary in reviews</span>
            </label>
          </div>
          <div>
            <label className="label-cyber">Review Profile</label>
            <select className="input-cyber w-64 mt-2">
              <option value="assertive">Assertive</option>
              <option value="chill">Chill</option>
              <option value="security-first">Security First</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4">Path Filters</h3>
        <p className="text-cyber-400 mb-4">Patterns to ignore during review (glob syntax)</p>
        <div className="space-y-2">
          {['**/*.min.js', '**/vendor/**', 'package-lock.json', '**/*.lock', '**/node_modules/**'].map((pattern, i) => (
            <div key={i} className="flex items-center gap-2">
              <input type="text" defaultValue={pattern} className="input-cyber flex-1 font-mono text-sm" />
              <button className="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400">🗑</button>
            </div>
          ))}
          <button className="btn-cyber-ghost text-sm">+ Add Pattern</button>
        </div>
      </div>
    </div>
  )
}

export default RepositoryDetail