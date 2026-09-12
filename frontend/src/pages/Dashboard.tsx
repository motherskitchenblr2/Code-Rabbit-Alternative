import { useState, useEffect, useMemo, useCallback } from 'react'
import { useWebSocket } from '../contexts/WebSocketContext'
import {
  Zap,
  MessageSquare,
  GitPullRequest,
  Radio,
  Clock,
  Download,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Activity,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

const typeColors: Record<string, string> = {
  webhook: '#10b981',
  github: '#8b5cf6',
  chat: '#3b82f6',
  auth: '#f59e0b',
  llm: '#ef4444',
  rag: '#06b6d4',
  critique: '#ec4899',
  ast: '#84cc16',
  integration: '#14b8a6',
}

const statusIcons: Record<string, typeof CheckCircle2> = {
  ok: CheckCircle2,
  completed: CheckCircle2,
  failed: XCircle,
  error: XCircle,
  running: AlertTriangle,
  pending: AlertTriangle,
  warning: AlertTriangle,
}

const statusColors: Record<string, string> = {
  ok: 'text-emerald-500',
  completed: 'text-emerald-500',
  failed: 'text-red-400',
  error: 'text-red-400',
  running: 'text-amber-400',
  pending: 'text-slate-400',
  warning: 'text-amber-400',
}

export default function Dashboard() {
  const { events, totals, pipeline, isConnected } = useWebSocket()
  const [loading, setLoading] = useState(true)
  const [webhooks, setWebhooks] = useState<any[]>([])
  const [status, setStatus] = useState<any>(null)
  const [llm, setLlm] = useState<any>(null)
  const [agents, setAgents] = useState<any[]>([])
  const [, setOverview] = useState<any>(null)
  const [selfImpStatus, setSelfImpStatus] = useState<any>(null)

  const headers = useCallback((): Record<string, string> => {
    const token = localStorage.getItem('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [])

  useEffect(() => {
    let cancelled = false
    Promise.allSettled([
      fetch('/api/v1/status', { headers: headers() }).then(r => r.json()),
      fetch('/api/v1/llm/status', { headers: headers() }).then(r => r.json()),
      fetch('/api/v1/agents/roster', { headers: headers() }).then(r => r.json()),
      fetch('/api/v1/admin/overview', { headers: headers() }).then(r => r.json()),
      fetch('/api/v1/integrations/webhooks', { headers: headers() }).then(r => r.json()),
      fetch('/api/self-improvement/status', { headers: headers() }).then(r => r.json()),
    ]).then(([s, l, a, o, w, si]) => {
      if (cancelled) return
      if (s.status === 'fulfilled') setStatus(s.value)
      if (l.status === 'fulfilled') setLlm(l.value)
      if (a.status === 'fulfilled') setAgents(a.value.agents || [])
      if (o.status === 'fulfilled') setOverview(o.value)
      if (w.status === 'fulfilled') setWebhooks(w.value.webhooks || [])
      if (si.status === 'fulfilled') setSelfImpStatus(si.value)
      setLoading(false)
    })
    return () => { cancelled = true }
  }, [headers])

  // Event activity — bucket feed events by hour (last 24h)
  const eventActivity = useMemo(() => {
    const now = Date.now()
    const buckets: Record<string, { time: string; events: number }> = {}
    for (let i = 23; i >= 0; i--) {
      const d = new Date(now - i * 3600000)
      const key = d.toISOString().slice(0, 13)
      buckets[key] = { time: key.slice(11) + ':00', events: 0 }
    }
    for (const e of events) {
      const t = e.timestamp?.slice(0, 13)
      if (t && buckets[t]) buckets[t].events++
    }
    return Object.values(buckets)
  }, [events])

  // Event mix pie from totals
  const eventMix = useMemo(() => {
    return Object.entries(totals)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({ name, value, color: typeColors[name] || '#6a6a8a' }))
  }, [totals])

  const recentEvents = useMemo(() => events.slice(0, 8), [events])

  const webhookSources = webhooks.map((w: any) => ({
    id: w.id,
    name: w.name,
    kind: w.channel || w.kind,
    enabled: w.enabled !== false,
    url_tail: w.url_tail || '',
  }))

  const providerStats = (status as any)?.config?.ai_providers || { total: 0, enabled: 0 }
  const mcpStats = (status as any)?.config?.mcp_servers || { total: 0, enabled: 0 }

  const eventsProcessed = pipeline.events_processed ?? status?.pipeline_state?.events_processed ?? 0
  const commentsDispatched = pipeline.comments_dispatched ?? status?.pipeline_state?.comments_dispatched ?? 0
  const reviewsCreated = pipeline.reviews_created ?? status?.pipeline_state?.reviews_created ?? 0

  const stats = [
    { label: 'Events Processed', value: eventsProcessed, icon: Zap, color: 'text-blue-500', bg: 'bg-blue-500/10' },
    { label: 'Comments Dispatched', value: commentsDispatched, icon: MessageSquare, color: 'text-purple-500', bg: 'bg-purple-500/10' },
    { label: 'Reviews Created', value: reviewsCreated, icon: GitPullRequest, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
    { label: 'Monitored Sources', value: webhookSources.length, icon: Radio, color: 'text-orange-500', bg: 'bg-orange-500/10' },
    { label: 'Uptime', value: formatUptime(status?.uptime_seconds ?? 0), icon: Clock, color: 'text-cyan-500', bg: 'bg-cyan-500/10', isText: true },
  ]

  const handleExport = () => {
    const blob = {
      exported_at: new Date().toISOString(),
      system_status: status,
      pipeline,
      totals,
      recent_events: events.slice(0, 50),
      webhooks: webhookSources,
      llm_providers: llm?.providers
        ? llm.providers.map((p: any) => ({ name: p.name, model: p.current_model, health: p.health_status }))
        : [],
      self_improvement: selfImpStatus,
    }
    const url = URL.createObjectURL(new Blob([JSON.stringify(blob, null, 2)], { type: 'application/json' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `dashboard-export-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div className="card-cyber p-12 text-center">
        <div className="w-8 h-8 border-2 border-neon-magenta border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-cyber-400 font-mono tracking-wider">LOADING SYSTEM STATUS…</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> Dashboard
          </h1>
          <p className="text-cyber-400 mt-1 font-mono text-sm tracking-wider">
            {isConnected ? 'SYSTEM OPERATIONAL — ALL SERVICES NOMINAL' : 'RECONNECTING…'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleExport} className="btn-cyber-sm flex items-center gap-2 bg-cyber-800/50 border border-cyber-700/50 text-cyber-200 hover:bg-cyber-700/50">
            <Download className="w-4 h-4" />
            Export
          </button>
          <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono ${
            isConnected
              ? 'bg-neon-green/20 text-neon-green border border-neon-green/30'
              : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-neon-green animate-pulse' : 'bg-red-500'}`} />
            {isConnected ? 'OPERATIONAL' : 'OFFLINE'}
          </span>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="card-cyber p-4">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${stat.bg}`}>
                <stat.icon className={`w-4 h-4 ${stat.color}`} />
              </div>
              <div>
                <div className="text-2xl font-bold font-mono tracking-wider">
                  {stat.isText ? stat.value : formatNumber(stat.value as number)}
                </div>
                <div className="text-xs text-cyber-400 font-mono tracking-wider">{stat.label.toUpperCase()}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card-cyber p-6">
          <h3 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-neon-cyan" /> EVENT ACTIVITY — 24H
          </h3>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={eventActivity}>
                <XAxis dataKey="time" stroke="#6a6a8a" tick={{ fill: '#6a6a8a', fontSize: 10 }} />
                <YAxis stroke="#6a6a8a" tick={{ fill: '#6a6a8a' }} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #ff00ff', borderRadius: '8px' }} labelStyle={{ color: '#fff' }} />
                <Line type="monotone" dataKey="events" stroke="#00ffff" strokeWidth={2} dot={false} name="Events" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card-cyber p-6">
          <h3 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-neon-magenta" /> EVENT MIX
          </h3>
          {eventMix.length > 0 ? (
            <div className="h-[200px] flex items-center gap-6">
              <ResponsiveContainer width="55%" height="100%">
                <PieChart>
                  <Pie data={eventMix} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                    {eventMix.map((e, i) => (
                      <Cell key={i} fill={e.color} stroke="#1a1a2e" />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #ff00ff', borderRadius: '8px' }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {eventMix.map(e => (
                  <div key={e.name} className="flex items-center gap-2 text-xs font-mono">
                    <div className="w-2 h-2 rounded-full" style={{ background: e.color }} />
                    <span className="text-cyber-300">{e.name}</span>
                    <span className="text-white">{e.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-[200px] flex items-center justify-center text-cyber-500 font-mono text-sm tracking-wider">
              NO EVENTS YET
            </div>
          )}
        </div>
      </div>

      {/* Tables row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monitored Sources */}
        <div className="card-cyber p-6">
          <h3 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-4">
            MONITORED SOURCES <span className="text-neon-green ml-1">LIVE</span>
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-cyber-700/50">
                  <th className="text-left py-2 text-xs font-mono text-cyber-400 tracking-wider">SOURCE</th>
                  <th className="text-left py-2 text-xs font-mono text-cyber-400 tracking-wider">KIND</th>
                  <th className="text-left py-2 text-xs font-mono text-cyber-400 tracking-wider">STATUS</th>
                  <th className="text-right py-2 text-xs font-mono text-cyber-400 tracking-wider">ENDPOINT</th>
                </tr>
              </thead>
              <tbody>
                {webhookSources.length === 0 && (
                  <tr><td colSpan={4} className="py-6 text-center text-cyber-500 font-mono text-sm tracking-wider">NO WEBHOOKS CONFIGURED</td></tr>
                )}
                {webhookSources.map((src, i) => (
                  <tr key={src.id || i} className="border-b border-cyber-800/50 hover:bg-cyber-800/30">
                    <td className="py-3 text-sm font-medium text-white">{src.name}</td>
                    <td className="py-3"><span className="text-xs px-2 py-1 bg-cyber-800 rounded text-cyber-300 font-mono">{src.kind}</span></td>
                    <td className="py-3">
                      <span className={`text-xs font-mono ${src.enabled ? 'text-neon-green' : 'text-cyber-500'}`}>
                        {src.enabled ? '● ACTIVE' : '○ INACTIVE'}
                      </span>
                    </td>
                    <td className="py-3 text-right text-xs font-mono text-cyber-500">{src.url_tail || '—'}</td>
                  </tr>
                ))}
                {providerStats.total > 0 && (
                  <tr className="border-t border-cyber-700/50 bg-cyber-800/20">
                    <td className="py-2 text-xs font-mono text-cyber-400 col-span-2">AI Providers</td>
                    <td className="py-2"><span className="text-xs font-mono text-neon-cyan">{providerStats.enabled}/{providerStats.total}</span></td>
                    <td className="py-2 text-right text-xs font-mono text-cyber-500">configured</td>
                  </tr>
                )}
                {mcpStats.total > 0 && (
                  <tr className="bg-cyber-800/10">
                    <td className="py-2 text-xs font-mono text-cyber-400">MCP Servers</td>
                    <td className="py-2"><span className="text-xs font-mono text-neon-magenta">{mcpStats.enabled}/{mcpStats.total}</span></td>
                    <td className="py-2 text-right text-xs font-mono text-cyber-500" colSpan={2}>connected</td>
                  </tr>
                )}
                {agents.length > 0 && (
                  <tr className="bg-cyber-800/10">
                    <td className="py-2 text-xs font-mono text-cyber-400">Agents</td>
                    <td className="py-2"><span className="text-xs font-mono text-neon-green">{agents.length}</span></td>
                    <td className="py-2 text-right text-xs font-mono text-cyber-500" colSpan={2}>registered</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card-cyber p-6">
          <h3 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-4">
            RECENT ACTIVITY <span className="text-neon-cyan ml-1">{events.length}</span>
          </h3>
          <div className="space-y-1">
            {recentEvents.length === 0 && (
              <div className="py-8 text-center text-cyber-500 font-mono text-sm tracking-wider">
                NO ACTIVITY YET — INTERACT WITH THE SYSTEM TO SEE EVENTS
              </div>
            )}
            {recentEvents.map((event) => {
              const StatusIcon = statusIcons[event.status] || AlertTriangle
              const iconColor = statusColors[event.status] || 'text-cyber-400'
              return (
                <div key={event.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-cyber-800/30 transition-colors">
                  <StatusIcon className={`w-4 h-4 shrink-0 ${iconColor}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded font-mono"
                        style={{ background: (typeColors[event.type] || '#6a6a8a') + '20', color: typeColors[event.type] || '#6a6a8a' }}
                      >
                        {event.type}
                      </span>
                      <span className="text-xs font-mono text-cyber-500">{formatEventTime(event.timestamp)}</span>
                    </div>
                    <div className="text-xs text-cyber-300 mt-1 font-mono truncate">{formatEventData(event)}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Live Pipeline Events */}
      <div className="card-cyber p-6">
        <h3 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-4 flex items-center gap-2">
          LIVE PIPELINE EVENTS
          {isConnected ? (
            <Wifi className="w-4 h-4 text-neon-green animate-pulse" />
          ) : (
            <WifiOff className="w-4 h-4 text-red-400" />
          )}
          <span className="text-xs text-cyber-500 ml-auto">polling /api/v1/events</span>
        </h3>
        <div className="h-[200px] overflow-y-auto font-mono text-xs space-y-1 pr-2">
          {events.length === 0 ? (
            <div className="flex items-center justify-center h-full text-cyber-500 tracking-wider">
              WAITING FOR PIPELINE EVENTS…
            </div>
          ) : (
            events.map((event) => {
              const StatusIcon = statusIcons[event.status] || AlertTriangle
              const iconColor = statusColors[event.status] || 'text-cyber-400'
              return (
                <div key={event.id} className="flex items-center gap-3 py-1 hover:bg-cyber-800/30 px-2 rounded">
                  <StatusIcon className={`w-3 h-3 shrink-0 ${iconColor}`} />
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded font-mono"
                    style={{ background: (typeColors[event.type] || '#6a6a8a') + '20', color: typeColors[event.type] || '#6a6a8a' }}
                  >
                    {event.type}
                  </span>
                  <span className="text-cyber-300 flex-1 truncate">{formatEventData(event)}</span>
                  <span className="text-cyber-500 shrink-0 text-[10px]">{formatEventTime(event.timestamp)}</span>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}

function formatUptime(seconds: number): string {
  if (!seconds) return '0s'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function formatEventTime(ts?: string): string {
  if (!ts) return ''
  try {
    return new Date(ts.endsWith('Z') ? ts : ts + 'Z').toLocaleTimeString(undefined, {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
  } catch {
    return ts
  }
}

function formatEventData(event: any): string {
  const d = event.data || {}
  if (event.type === 'auth') return d.action || 'auth event'
  if (event.type === 'chat') return d.comment_id || 'chat reply'
  if (event.type === 'webhook') return d.channel_id || d.name || 'webhook event'
  if (event.type === 'github') return d.owner && d.repo ? `${d.owner}/${d.repo}` : 'github event'
  if (event.type === 'llm') return d.model || 'llm call'
  if (event.type === 'integration') return d.name || 'integration event'
  return `${event.type} event`
}