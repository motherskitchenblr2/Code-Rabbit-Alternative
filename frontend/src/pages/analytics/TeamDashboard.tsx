import React, { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { useWebSocket } from '../../contexts/WebSocketContext'
import {
  Users,
  BarChart3,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  Target,
  Shield,
  GitBranch,
  Activity,
  Download,
  Filter,
  Calendar,
  ChevronDown,
  ChevronUp,
  Settings,
  RefreshCw,
  ExternalLink,
  FileText,
  PieChart,
  Users2,
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area } from 'recharts'

interface TeamMember {
  id: string
  name: string
  email: string
  role: string
  avatar?: string
  repositories: number
  scans: number
  criticalFindings: number
  lastActive: string
}

interface TeamMetrics {
  totalMembers: number
  activeMembers: number
  totalScans: number
  totalFindings: number
  criticalFindings: number
  avgScanTime: number
  fixRate: number
  avgResponseTime: number
}

interface ComplianceReport {
  standard: string
  status: 'compliant' | 'partial' | 'non-compliant'
  score: number
  findings: number
  lastAudit: string
}

interface TrendData {
  date: string
  scans: number
  findings: number
  critical: number
  fixed: number
  responseTime: number
}

export default function TeamDashboard() {
  const { user } = useAuth()
  const { isConnected } = useWebSocket()
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const [selectedMember, setSelectedMember] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'overview' | 'members' | 'trends' | 'compliance'>('overview')

  const [teamMetrics, setTeamMetrics] = useState<TeamMetrics>({
    totalMembers: 12,
    activeMembers: 8,
    totalScans: 1247,
    totalFindings: 3421,
    criticalFindings: 47,
    avgScanTime: 620,
    fixRate: 87.5,
    avgResponseTime: 4.2
  })

  const [members, setMembers] = useState<TeamMember[]>([
    { id: '1', name: 'Sarah Chen', email: 'sarah.chen@company.com', role: 'Security Lead', avatar: 'SC', repositories: 8, scans: 234, criticalFindings: 12, lastActive: '2 min ago' },
    { id: '2', name: 'Marcus Johnson', email: 'marcus.j@company.com', role: 'Senior Dev', avatar: 'MJ', repositories: 12, scans: 189, criticalFindings: 8, lastActive: '15 min ago' },
    { id: '3', name: 'Priya Patel', email: 'priya.p@company.com', role: 'DevOps Engineer', avatar: 'PP', repositories: 6, scans: 156, criticalFindings: 5, lastActive: '1 hour ago' },
    { id: '4', name: 'Alex Rivera', email: 'alex.r@company.com', role: 'Backend Dev', avatar: 'AR', repositories: 9, scans: 201, criticalFindings: 7, lastActive: '3 hours ago' },
    { id: '5', name: 'Jordan Kim', email: 'jordan.k@company.com', role: 'Frontend Dev', avatar: 'JK', repositories: 7, scans: 134, criticalFindings: 3, lastActive: '5 hours ago' },
    { id: '6', name: 'Taylor Smith', email: 'taylor.s@company.com', role: 'Full Stack', avatar: 'TS', repositories: 11, scans: 178, criticalFindings: 9, lastActive: '1 day ago' },
    { id: '7', name: 'Casey Brown', email: 'casey.b@company.com', role: 'Security Analyst', avatar: 'CB', repositories: 4, scans: 89, criticalFindings: 15, lastActive: '2 days ago' },
    { id: '8', name: 'Morgan Lee', email: 'morgan.l@company.com', role: 'Tech Lead', avatar: 'ML', repositories: 15, scans: 267, criticalFindings: 4, lastActive: '1 week ago' },
  ])

  const [trendData, setTrendData] = useState<TrendData[]>([
    { date: '2024-01-01', scans: 45, findings: 23, critical: 2, fixed: 18, responseTime: 4.2 },
    { date: '2024-01-02', scans: 52, findings: 31, critical: 3, fixed: 22, responseTime: 3.8 },
    { date: '2024-01-03', scans: 38, findings: 18, critical: 1, fixed: 15, responseTime: 4.5 },
    { date: '2024-01-04', scans: 61, findings: 42, critical: 4, fixed: 28, responseTime: 3.9 },
    { date: '2024-01-05', scans: 55, findings: 29, critical: 2, fixed: 24, responseTime: 4.1 },
    { date: '2024-01-06', scans: 42, findings: 19, critical: 0, fixed: 12, responseTime: 5.2 },
    { date: '2024-01-07', scans: 38, findings: 15, critical: 1, fixed: 10, responseTime: 4.8 },
  ])

  const [complianceReports, setComplianceReports] = useState<ComplianceReport[]>([
    { standard: 'SOC 2 Type II', status: 'compliant', score: 98, findings: 2, lastAudit: '2024-01-15' },
    { standard: 'ISO 27001', status: 'compliant', score: 95, findings: 5, lastAudit: '2024-01-10' },
    { standard: 'GDPR', status: 'partial', score: 87, findings: 12, lastAudit: '2024-01-08' },
    { standard: 'HIPAA', status: 'compliant', score: 92, findings: 3, lastAudit: '2024-01-12' },
    { standard: 'PCI DSS', status: 'partial', score: 89, findings: 8, lastAudit: '2024-01-05' },
    { standard: 'OWASP Top 10', status: 'compliant', score: 96, findings: 1, lastAudit: '2024-01-14' },
  ])

  const [filter, setFilter] = useState({ severity: '', member: '', repo: '' })

  const memberColors = {
    'Sarah Chen': '#ff00ff',
    'Marcus Johnson': '#00ffff',
    'Priya Patel': '#ff8c00',
    'Alex Rivera': '#00ff00',
    'Jordan Kim': '#ff0066',
    'Taylor Smith': '#ffaa00',
    'Casey Brown': '#ff3333',
    'Morgan Lee': '#00ccff',
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num.toString()
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-400 bg-red-900/30 border-red-500/30'
      case 'high': return 'text-orange-400 bg-orange-900/30 border-orange-500/30'
      case 'medium': return 'text-amber-400 bg-amber-900/30 border-amber-500/30'
      case 'low': return 'text-green-400 bg-green-900/30 border-green-500/30'
      case 'info': return 'text-cyan-400 bg-cyan-900/30 border-cyan-500/30'
      default: return 'text-cyber-400 bg-cyber-800/30 border-cyber-700/30'
    }
  }

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)
    
    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  if (viewMode === 'overview') {
    return (
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
              <span className="text-neon-magenta">>_</span> Team Analytics
            </h1>
            <p className="text-cyber-400 mt-1">Team performance, security posture & compliance overview</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-neon-green animate-pulse' : 'bg-neon-amber'}`} />
              <span className="text-xs font-mono text-cyber-400">{isConnected ? 'LIVE' : 'OFFLINE'}</span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-cyber-400" />
              <select value={timeRange} onChange={(e) => setTimeRange(e.target as any)} className="input-cyber px-3 py-1 text-xs">
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
                <option value="90d">Last 90 days</option>
              </select>
            </div>
            <button className="btn-cyber-magenta flex items-center gap-2" onClick={() => setViewMode('members')}>
              <Users2 className="w-4 h-4" />
              View Team
            </button>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard title="Team Members" value={teamMetrics.totalMembers} icon="👥" color="neon-cyan" trend={`+${teamMetrics.activeMembers} active`} trendColor="neon-green" />
          <MetricCard title="Total Scans" value={teamMetrics.totalScans.toLocaleString()} icon="🔍" color="neon-magenta" trend={`+${Math.floor(teamMetrics.totalScans * 0.12)} this period`} trendColor="neon-amber" />
          <MetricCard title="Critical Findings" value={teamMetrics.criticalFindings} icon="🔴" color="red" trend={`-${Math.floor(teamMetrics.criticalFindings * 0.15)} vs last period`} trendColor="neon-green" />
          <MetricCard title="Fix Rate" value={`${teamMetrics.fixRate}%`} icon="✅" color="neon-green" trend={`+${(teamMetrics.fixRate - 85).toFixed(1)}% vs last period`} trendColor="neon-green" />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Scan Activity Trend */}
          <div className="card-cyber p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-neon-cyan" />
                Scan Activity Trend
              </h3>
              <div className="flex items-center gap-2">
                {['7d', '30d', '90d'].map((range) => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range as any)}
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
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
                  <XAxis dataKey="date" stroke="#6a6a8a" tick={{ fill: '#6a6a8a' }} />
                  <YAxis stroke="#6a6a8a" tick={{ fill: '#6a6a8a' }} />
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
                    name="Scans"
                  />
                  <Line
                    type="monotone"
                    dataKey="findings"
                    stroke="#00ffff"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6, fill: '#00ffff' }}
                    name="Findings"
                  />
                  <Line
                    type="monotone"
                    dataKey="critical"
                    stroke="#ff3333"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6, fill: '#ff3333' }}
                    name="Critical"
                  />
                  <Line
                    type="monotone"
                    dataKey="fixed"
                    stroke="#00ff00"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6, fill: '#00ff00' }}
                    name="Fixed"
                  />
                </LineChart>
              </div>
            </div>
          </div>

          {/* Findings by Severity */}
          <div className="card-cyber p-6">
            <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-neon-magenta" />
              Findings by Severity
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Critical', value: 47, color: '#ff3333' },
                      { name: 'High', value: 124, color: '#ff8c00' },
                      { name: 'Medium', value: 567, color: '#ff8c00' },
                      { name: 'Low', value: 1245, color: '#00ff00' },
                      { name: 'Info', value: 342, color: '#00ffff' },
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
                      { name: 'Info', value: 342, color: '#00ffff' },
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
              </div>
              <div className="flex flex-wrap justify-center gap-4 mt-4">
                {[
                  { label: 'Critical', color: '#ff3333' },
                  { label: 'High', color: '#ff8c00' },
                  { label: 'Medium', color: '#ff8c00' },
                  { label: 'Low', color: '#00ff00' },
                  { label: 'Info', color: '#00ffff' },
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-xs text-cyber-300">{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Team Activity & Response Time */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="card-cyber p-6">
            <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-neon-amber" />
              Team Activity Heatmap
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
                  <XAxis dataKey="date" stroke="#6a6a8a" tick={{ fill: '#6a6a8a' }} />
                  <YAxis stroke="#6a6a8a" tick={{ fill: '#6a6a8a' }} />
                  <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #ff00ff', borderRadius: '8px' }} />
                  <Bar dataKey="scans" fill="#ff00ff" name="Scans" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="findings" fill="#00ffff" name="Findings" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="fixed" fill="#00ff00" name="Fixed" radius={[4, 4, 0, 0]} />
                </BarChart>
              </div>
            </div>
          </div>

          <div className="card-cyber p-6">
            <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-neon-amber" />
              Response Time & Fix Rate
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
                  <XAxis dataKey="date" stroke="#6a6a8a" tick={{ fill: '#6a6a8a' }} />
                  <YAxis stroke="#6a6a8a" tick={{ fill: '#6a6a8a' }} />
                  <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #ff00ff', borderRadius: '8px' }} />
                  <Line type="monotone" dataKey="responseTime" stroke="#ff8c00" strokeWidth={2} dot={false} name="Avg Response (hrs)" />
                  <Line type="monotone" dataKey="fixed" stroke="#00ff00" strokeWidth={2} dot={false} name="Fixed Issues" />
                </LineChart>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }
}

function MetricCard({ title, value, icon, color, trend, trendColor }: { title: string; value: string | number; icon: string; color: string; trend: string; trendColor: string }) {
  const colorMap: Record<string, string> = {
    'neon-cyan': 'bg-neon-cyan/10 text-neon-cyan',
    'neon-magenta': 'bg-neon-magenta/10 text-neon-magenta',
    'neon-amber': 'bg-neon-amber/10 text-neon-amber',
    'neon-green': 'bg-neon-green/10 text-neon-green',
    'red': 'bg-red-500/10 text-red-400',
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
          'neon-green': 'bg-neon-green/10',
          'red': 'bg-red-500/10',
        }[color] || 'bg-neon-magenta/10'}`}>
          <span className="text-2xl">{icon}</span>
        </div>
      </div>
      <div className="mt-4 flex items-center gap-1">
        <span className={`text-xs font-mono ${trendColor}`}>{trend}</span>
        <span className="text-xs text-cyber-500">vs last period</span>
      </div>
    </div>
  )
}

export default TeamDashboard