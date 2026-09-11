import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useWebSocket } from '../contexts/WebSocketContext'
import { useAuth } from '../contexts/AuthContext'
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Terminal,
  GitBranch as GitBranchIcon,
  Activity,
  ChevronRight,
  Shield,
  Bug,
  Plus,
  Eye,
  Download,
  AlertCircle,
  CheckCircle2,
  Zap as ZapIcon,
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

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
}

interface PipelineStats {
  total_scans: number
  issues_found: number
  critical_issues: number
  avg_scan_time: number
  success_rate: number
}

const SEVERITY_COLORS = {
  critical: 'text-red-400 bg-red-900/30 border-red-500/30',
  high: 'text-orange-400 bg-orange-900/30 border-orange-500/30',
  medium: 'text-amber-400 bg-amber-900/30 border-amber-500/30',
  low: 'text-green-400 bg-green-900/30 border-green-500/30',
}

const SEVERITY_ICONS = {
  critical: AlertTriangle,
  high: AlertCircle,
  medium: AlertCircle,
  low: CheckCircle2,
}

export default function Dashboard() {
  const { isConnected, events } = useWebSocket()
  const { user } = useAuth()
  const [repos, setRepos] = useState<Repository[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [stats, setStats] = useState<PipelineStats>({
    total_scans: 0,
    issues_found: 0,
    critical_issues: 0,
    avg_scan_time: 0,
    success_rate: 0,
  })
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h')

  // Mock data for demonstration
  useEffect(() => {
    const mockRepos: Repository[] = [
      { id: '1', name: 'gitfix-core', full_name: 'org/gitfix-core', description: 'Core Git-Fix engine', private: true, language: 'Python', stars: 142, forks: 28, open_prs: 5, last_scan: '2 min ago', status: 'active' },
      { id: '2', name: 'gitfix-frontend', full_name: 'org/gitfix-frontend', description: 'Cyberpunk dashboard', private: true, language: 'TypeScript', stars: 89, forks: 15, open_prs: 3, last_scan: '15 min ago', status: 'active' },
      { id: '3', name: 'gitfix-cli', full_name: 'org/gitfix-cli', description: 'CLI tool for Git-Fix', private: false, language: 'Go', stars: 256, forks: 42, open_prs: 2, last_scan: '1 hour ago', status: 'idle' },
      { id: '4', name: 'gitfix-hooks', full_name: 'org/gitfix-hooks', description: 'Git hooks integration', private: true, language: 'Python', stars: 67, forks: 12, open_prs: 1, last_scan: '3 hours ago', status: 'active' },
    ]

    const mockFindings: Finding[] = [
      { id: '1', type: 'security', severity: 'critical', file: 'backend/app.py', line: 22, message: 'Hardcoded webhook secret in source code', confidence: 98.5, timestamp: '2024-01-15T10:30:00Z' },
      { id: '2', type: 'security', severity: 'high', file: 'backend/app.py', line: 11, message: 'CORS misconfiguration allows all origins', confidence: 92.3, timestamp: '2024-01-15T10:25:00Z' },
      { id: '3', type: 'security', severity: 'high', file: 'frontend/src/main.tsx', line: 8, message: 'Missing CSP headers in production build', confidence: 88.7, timestamp: '2024-01-15T10:20:00Z' },
      { id: '4', type: 'logic', severity: 'medium', file: 'backend/hooks/pre-commit.py', line: 45, message: 'Potential path traversal in file path validation', confidence: 85.2, timestamp: '2024-01-15T10:15:00Z' },
      { id: '5', type: 'style', severity: 'low', file: 'backend/app.py', line: 374, message: 'Debug mode enabled in production config', confidence: 95.1, timestamp: '2024-01-15T10:10:00Z' },
      { id: '6', type: 'test', severity: 'medium', file: 'backend/app.py', line: 200, message: 'Missing unit tests for webhook validation', confidence: 82.4, timestamp: '2024-01-15T10:05:00Z' },
    ]

    const mockStats: PipelineStats = {
      total_scans: 1247,
      issues_found: 3421,
      critical_issues: 47,
      avg_scan_time: 842,
      success_rate: 98.7,
    }

    setRepos(mockRepos)
    setFindings(mockFindings)
    setStats(mockStats)
    setLoading(false)
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-neon-magenta border-t-transparent rounded-full animate-spin" />
          <p className="text-cyber-400 font-mono">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> Dashboard
          </h1>
          <p className="text-cyber-400 mt-1">Welcome back, {user?.username || 'Operator'}. System status: <span className="text-neon-green font-mono">OPERATIONAL</span></p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-cyber-ghost flex items-center">
            <Download className="w-4 h-4 md:mr-2" />
            <span className="hidden md:inline">Export Report</span>
          </button>
          <Link to="/repositories" className="btn-cyber-magenta flex items-center">
            <Plus className="w-4 h-4 md:mr-2" />
            <span className="hidden md:inline">Add Repository</span>
            <span className="md:hidden">Add Repo</span>
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-4 mb-8">
        <StatCard
          title="Total Scans"
          value={stats.total_scans.toLocaleString()}
          icon={Activity}
          color="neon-cyan"
          trend="+12%"
          trendColor="neon-green"
        />
        <StatCard
          title="Issues Found"
          value={stats.issues_found.toLocaleString()}
          icon={Bug}
          color="neon-magenta"
          trend="+89"
          trendColor="neon-amber"
        />
        <StatCard
          title="Critical Issues"
          value={stats.critical_issues.toLocaleString()}
          icon={Shield}
          color="red"
          trend="-12%"
          trendColor="neon-green"
        />
        <StatCard
          title="Avg Scan Time"
          value={`${stats.avg_scan_time}ms`}
          icon={Clock}
          color="neon-amber"
          trend="-5%"
          trendColor="neon-green"
        />
        <StatCard
          title="Success Rate"
          value={`${stats.success_rate}%`}
          icon={CheckCircle}
          color="neon-green"
          trend="+0.2%"
          trendColor="neon-green"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Scan Activity Chart */}
        <div className="card-cyber p-4 md:p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold font-display text-white">Scan Activity</h3>
            <div className="flex items-center gap-2">
              {['24h', '7d', '30d'].map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range as '24h' | '7d' | '30d')}
                  className={`px-3 py-1 rounded-lg text-xs font-mono transition-all ${
                    timeRange === range
                      ? 'bg-neon-magenta/20 text-neon-magenta border border-neon-magenta/30'
                      : 'text-cyber-400 hover:text-cyber-200'
                  }`}
                >
                  {range}
                </button>
              ))}
            </div>
          </div>
          <div className="h-56 md:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={generateChartData(timeRange)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
                <XAxis dataKey="time" stroke="#6a6a8a" fontSize={12} tick={{ fill: '#6a6a8a' }} />
                <YAxis stroke="#6a6a8a" fontSize={12} tick={{ fill: '#6a6a8a' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1a1a2e',
                    border: '1px solid #ff00ff',
                    borderRadius: '8px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="scans"
                  stroke="#ff00ff"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6, fill: '#ff00ff' }}
                />
                <Line
                  type="monotone"
                  dataKey="issues"
                  stroke="#00ffff"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 6, fill: '#00ffff' }}
                />
              </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

        {/* Issues by Severity */}
        <div className="card-cyber p-4 md:p-6">
          <h3 className="text-lg font-bold font-display text-white mb-4">Issues by Severity</h3>
          <div className="h-56 md:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={[
                    { name: 'Critical', value: 47, color: '#ff3333' },
                    { name: 'High', value: 124, color: '#ff8c00' },
                    { name: 'Medium', value: 567, color: '#ff8c00' },
                    { name: 'Low', value: 1245, color: '#00ff00' },
                  ]}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {[
                    { name: 'Critical', value: 47, color: '#ff3333' },
                    { name: 'High', value: 124, color: '#ff8c00' },
                    { name: 'Medium', value: 567, color: '#ff8c00' },
                    { name: 'Low', value: 1245, color: '#00ff00' },
                  ].map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1a1a2e',
                    border: '1px solid #ff00ff',
                    borderRadius: '8px',
                  }}
                />
              </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap justify-center gap-4 mt-4">
              {[
                { label: 'Critical', color: '#ff3333' },
                { label: 'High', color: '#ff8c00' },
                { label: 'Medium', color: '#ff8c00' },
                { label: 'Low', color: '#00ff00' },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                  <span className="text-xs text-cyber-300">{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

      {/* Recent Repositories & Findings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Repositories Table */}
        <div className="card-cyber">
          <div className="p-6 border-b border-cyber-700/50 flex items-center justify-between">
            <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
              <GitBranchIcon className="w-5 h-5 text-neon-cyan" />
              Repositories
            </h3>
            <Link to="/repositories" className="text-neon-magenta hover:text-neon-cyan text-sm font-mono flex items-center gap-1">
              View All
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-cyber-700/50">
                  <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Repository</th>
                  <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider hidden md:table-cell">Language</th>
                  <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider hidden lg:table-cell">Open PRs</th>
                  <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Last Scan</th>
                  <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-mono text-cyber-400 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {repos.map((repo) => (
                  <tr key={repo.id} className="border-b border-cyber-800/50 hover:bg-cyber-800/30 transition-colors">
                    <td className="px-4 py-3">
                      <Link to={`/repositories/${repo.id}`} className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-cyber-800 flex items-center justify-center">
                          <GitBranchIcon className="w-4 h-4 text-neon-cyan" />
                        </div>
                        <div>
                          <p className="font-medium text-white">{repo.name}</p>
                          <p className="text-xs text-cyber-400">{repo.full_name}</p>
                        </div>
                      </Link>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-xs px-2 py-1 bg-cyber-800 rounded text-cyber-300 font-mono">{repo.language}</span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <span className="text-cyber-300 font-mono">{repo.open_prs}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-cyber-400 font-mono">{repo.last_scan}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-mono ${
                        repo.status === 'active' ? 'bg-neon-green/20 text-neon-green border border-neon-green/30' :
                        repo.status === 'idle' ? 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30' :
                        'bg-red-500/20 text-red-400 border border-red-500/30'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${repo.status === 'active' ? 'bg-neon-green' : repo.status === 'idle' ? 'bg-neon-amber' : 'bg-red-500'}`} />
                        {repo.status.charAt(0).toUpperCase() + repo.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link to={`/repositories/${repo.id}`} className="p-2 rounded-lg bg-cyber-800/50 hover:bg-neon-magenta/10 hover:border-neon-magenta/30 border border-cyber-700/50 transition-colors" aria-label="View repository">
                        <Eye className="w-4 h-4 text-cyber-400" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile card list */}
          <div className="divide-y divide-cyber-800/50 md:hidden">
            {repos.map((repo) => (
              <Link key={repo.id} to={`/repositories/${repo.id}`} className="flex items-center gap-3 p-4 active:bg-cyber-800/50 transition-colors">
                <div className="w-9 h-9 rounded-lg bg-cyber-800 flex items-center justify-center flex-shrink-0">
                  <GitBranchIcon className="w-4 h-4 text-neon-cyan" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-white truncate">{repo.name}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-cyber-400 font-mono truncate">{repo.full_name}</span>
                    <span className="text-xs text-cyber-500">·</span>
                    <span className="text-xs text-cyber-400 font-mono flex-shrink-0">{repo.last_scan}</span>
                  </div>
                </div>
                <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-mono flex-shrink-0 ${
                  repo.status === 'active' ? 'bg-neon-green/20 text-neon-green border border-neon-green/30' :
                  repo.status === 'idle' ? 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30' :
                  'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                  {repo.status.charAt(0).toUpperCase() + repo.status.slice(1)}
                </span>
              </Link>
            ))}
          </div>
        </div>

        {/* Recent Findings */}
        <div className="card-cyber">
          <div className="p-6 border-b border-cyber-700/50 flex items-center justify-between">
            <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
              <Bug className="w-5 h-5 text-neon-magenta" />
              Recent Findings
            </h3>
            <span className="badge-cyber bg-neon-magenta/20 text-neon-magenta border-neon-magenta/30">
              {findings.length} total
            </span>
          </div>
          <div className="divide-y divide-cyber-800/50">
            {findings.slice(0, 5).map((finding) => {
              const SeverityIcon = SEVERITY_ICONS[finding.severity]
              return (
                <div key={finding.id} className="p-4 hover:bg-cyber-800/30 transition-colors">
                  <div className="flex items-start gap-3">
                    <SeverityIcon className={`w-5 h-5 flex-shrink-0 ${SEVERITY_COLORS[finding.severity].replace('text-', 'text-').replace('bg-', 'bg-')}`} />
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
            })}
            {findings.length > 5 && (
              <div className="p-4 text-center border-t border-cyber-700/50">
                <Link to="/repositories" className="text-neon-magenta hover:text-neon-cyan text-sm font-mono flex items-center justify-center gap-1">
                  View All Findings
                  <ChevronRight className="w-4 h-4" />
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Live Pipeline Events */}
      <div className="card-cyber">
        <div className="p-6 border-b border-cyber-700/50 flex items-center justify-between">
          <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
            <ZapIcon className="w-5 h-5 text-neon-amber" />
            Live Pipeline Events
          </h3>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-neon-green' : 'bg-neon-amber'}`} />
            <span className="text-xs font-mono text-cyber-400">{isConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
          </div>
        </div>
        <div className="p-6 max-h-64 overflow-y-auto font-mono text-sm">
          {events.length === 0 ? (
            <div className="text-center py-8 text-cyber-500">
              <Terminal className="w-12 h-12 mx-auto mb-4 text-cyber-700" />
              <p>No live events yet. Trigger a webhook to see live pipeline activity.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {events.slice(0, 20).map((event, i) => (
                <div key={i} className="flex items-center gap-3 p-2 rounded-lg bg-cyber-800/50 border border-cyber-700/30">
                  <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                  <span className="text-cyber-500 font-mono text-xs">[{new Date().toLocaleTimeString()}]</span>
                  <span className="px-2 py-0.5 rounded text-xs font-mono bg-neon-magenta/20 text-neon-magenta border border-neon-magenta/30">{event.type?.toUpperCase() || 'UNKNOWN'}</span>
                  <span className="text-cyber-300 flex-1 truncate">{event.data?.repo || 'Processing...'}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-mono ${event.status === 'completed' ? 'bg-neon-green/20 text-neon-green' : event.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-neon-amber/20 text-neon-amber'}`}>
                    {event.status?.toUpperCase() || 'PENDING'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Helper Components
function StatCard({ title, value, icon: Icon, color, trend, trendColor }: { title: string; value: string; icon: React.ComponentType<any>; color: string; trend: string; trendColor: string }) {
  const colorMap: Record<string, string> = {
    'neon-cyan': 'text-neon-cyan',
    'neon-magenta': 'text-neon-magenta',
    'neon-amber': 'text-neon-amber',
    'neon-green': 'text-neon-green',
    red: 'text-red-400',
  }

  const bgMap: Record<string, string> = {
    'neon-cyan': 'bg-neon-cyan/10',
    'neon-magenta': 'bg-neon-magenta/10',
    'neon-amber': 'bg-neon-amber/10',
    'neon-green': 'bg-neon-green/10',
    red: 'bg-red-500/10',
  }

  return (
    <div className="card-cyber p-4 md:p-6">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] md:text-xs font-mono text-cyber-400 uppercase tracking-wider mb-1 truncate">{title}</p>
          <p className="text-xl md:text-3xl font-bold font-display text-white">{value}</p>
        </div>
        <div className={`w-10 h-10 md:w-12 md:h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${bgMap[color] || 'bg-neon-magenta/10'}`}>
          <Icon className="w-5 h-5 md:w-6 md:h-6" style={{ color: colorMap[color] || '#ff00ff' }} />
        </div>
      </div>
      <div className="mt-3 md:mt-4 flex items-center gap-1">
        <span className={`text-[10px] md:text-xs font-mono ${colorMap[trendColor] || 'text-neon-green'}`}>{trend}</span>
        <span className="text-[10px] md:text-xs text-cyber-500 truncate">vs last period</span>
      </div>
    </div>
  )
}

function generateChartData(range: string) {
  const points = range === '24h' ? 24 : range === '7d' ? 7 : 30
  const data = []
  for (let i = 0; i < points; i++) {
    data.push({
      time: range === '24h' ? `${i}:00` : range === '7d' ? `Day ${i + 1}` : `Day ${i + 1}`,
      scans: Math.floor(Math.random() * 50) + 20,
      issues: Math.floor(Math.random() * 20) + 5,
    })
  }
  return data
}

