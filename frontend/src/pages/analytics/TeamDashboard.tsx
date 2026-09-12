import { useState, useEffect, useMemo, useCallback } from 'react'
import { useWebSocket } from '../../contexts/WebSocketContext'
import {
  Activity,
  Calendar,
  Users2,
  ShieldCheck,
  Zap,
  GitPullRequest,
  Radio,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

export default function TeamDashboard() {
  const { isConnected, events, totals, pipeline } = useWebSocket()
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const [agents, setAgents] = useState<any[]>([])
  const [sessions, setSessions] = useState<any[]>([])
  const [compliance, setCompliance] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const headers = useCallback((): Record<string, string> => {
    const token = localStorage.getItem('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [])

  useEffect(() => {
    Promise.allSettled([
      fetch('/api/v1/agents/roster', { headers: headers() }).then(r => r.json()),
      fetch('/api/v1/agents/sessions', { headers: headers() }).then(r => r.json()),
      fetch('/api/v1/compliance/summary', { headers: headers() }).then(r => r.json()),
    ]).then(([a, s, c]) => {
      if (a.status === 'fulfilled') setAgents(a.value.agents || [])
      if (s.status === 'fulfilled') setSessions(s.value.sessions || [])
      if (c.status === 'fulfilled') setCompliance(c.value)
      setLoading(false)
    })
  }, [headers])

  // Activity trend — real feed events bucketed by day
  const trendData = useMemo(() => {
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
    const buckets: Record<string, { date: string; events: number }> = {}
    const now = Date.now()
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now - i * 86400000)
      const key = d.toISOString().slice(0, 10)
      buckets[key] = { date: key, events: 0 }
    }
    for (const e of events) {
      const key = e.timestamp?.slice(0, 10)
      if (key && buckets[key]) buckets[key].events++
    }
    return Object.values(buckets)
  }, [events, timeRange])

  // Event mix from real feed totals
  const eventMix = useMemo(() => {
    const colors: Record<string, string> = {
      webhook: '#10b981', github: '#8b5cf6', chat: '#3b82f6', auth: '#f59e0b',
      llm: '#ff3333', rag: '#06b6d4', critique: '#ec4899', ast: '#84cc16', integration: '#14b8a6',
    }
    return Object.entries(totals)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({ name, value, color: colors[name] || '#6a6a8a' }))
  }, [totals])

  const metrics = [
    { label: 'Agents in Roster', value: agents.length, icon: Users2, color: 'neon-cyan' },
    { label: 'Events Processed', value: pipeline.events_processed, icon: Zap, color: 'neon-magenta' },
    { label: 'Reviews Created', value: pipeline.reviews_created, icon: GitPullRequest, color: 'red' },
    { label: 'Compliance Score', value: compliance?.overall?.avg_score != null ? `${compliance.overall.avg_score}%` : '—', icon: ShieldCheck, color: 'neon-green' },
  ]

  if (loading) {
    return (
      <div className="card-cyber p-12 text-center">
        <div className="w-8 h-8 border-2 border-neon-magenta border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-cyber-400 font-mono tracking-wider">LOADING TEAM ANALYTICS…</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> Team Analytics
          </h1>
          <p className="text-cyber-400 mt-1">Roster, pipeline activity & compliance posture</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-neon-green animate-pulse' : 'bg-neon-amber'}`} />
            <span className="text-xs font-mono text-cyber-400">{isConnected ? 'FEED LIVE' : 'FEED OFFLINE'}</span>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-cyber-400" />
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as any)}
              className="input-cyber px-3 py-1 text-xs"
              aria-label="Time range"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
            </select>
          </div>
          <a href="/#/agents" className="btn-cyber-magenta flex items-center gap-2">
            <Radio className="w-4 h-4" />
            Agent Team
          </a>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {metrics.map((m) => (
          <div key={m.label} className="card-cyber p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-mono text-cyber-400 uppercase tracking-wider mb-1">{m.label}</p>
                <p className="text-3xl font-bold font-display text-white">{m.value}</p>
              </div>
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-${m.color}/10`}>
                <m.icon className={`w-6 h-6 text-${m.color}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Activity trend */}
        <div className="card-cyber p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-neon-cyan" />
              Pipeline Activity Trend
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
                <XAxis dataKey="date" stroke="#6a6a8a" tick={{ fill: '#6a6a8a', fontSize: 10 }} />
                <YAxis stroke="#6a6a8a" tick={{ fill: '#6a6a8a' }} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #ff00ff', borderRadius: '8px' }} />
                <Line type="monotone" dataKey="events" stroke="#00ffff" strokeWidth={2} dot={false} activeDot={{ r: 6, fill: '#00ffff' }} name="Events" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Event mix */}
        <div className="card-cyber p-6">
          <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-neon-magenta" />
            Event Mix by Type
          </h3>
          <div className="h-64">
            {eventMix.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={eventMix}
                    cx="50%" cy="50%"
                    innerRadius={60} outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="name"
                  >
                    {eventMix.map((e, index) => (
                      <Cell key={`cell-${index}`} fill={e.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #ff00ff', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-cyber-500 font-mono tracking-wider">
                NO EVENTS YET
              </div>
            )}
          </div>
          <div className="flex flex-wrap justify-center gap-4 mt-4">
            {eventMix.map((e) => (
              <div key={e.name} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: e.color }} />
                <span className="text-xs text-cyber-300 font-mono">{e.name} ({e.value})</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Agents + Sessions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card-cyber p-6">
          <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
            <Users2 className="w-5 h-5 text-neon-amber" />
            Agent Roster
          </h3>
          <div className="space-y-2">
            {agents.length === 0 && <p className="text-cyber-500 font-mono text-sm">No agents registered.</p>}
            {agents.map((agent) => (
              <div key={agent.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-cyber-800/30">
                <div className="w-8 h-8 rounded-lg bg-cyber-800 flex items-center justify-center text-xs font-mono text-neon-cyan">
                  {agent.name.charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium truncate">{agent.name}</p>
                  <p className="text-xs text-cyber-400 truncate">{agent.title}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card-cyber p-6">
          <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-neon-amber" />
            Recent Sessions
          </h3>
          <div className="space-y-2">
            {sessions.length === 0 && <p className="text-cyber-500 font-mono text-sm">No agent sessions yet.</p>}
            {sessions.slice(0, 8).map((session: any) => (
              <div key={session.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-cyber-800/30">
                <span className={`w-2 h-2 rounded-full shrink-0 ${session.status === 'done' ? 'bg-neon-green' : session.status === 'running' ? 'bg-neon-cyan animate-pulse' : 'bg-neon-amber'}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium truncate">{session.title || session.id}</p>
                  <p className="text-xs text-cyber-400 font-mono truncate">{session.id}</p>
                </div>
                <span className="text-xs font-mono text-cyber-500 uppercase">{session.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}