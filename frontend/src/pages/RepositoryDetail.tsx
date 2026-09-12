import { useState, useEffect, useCallback } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { GitBranch, ArrowLeft, Power, Zap, Trash2, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'

const statusIcons: Record<string, typeof CheckCircle2> = {
  ok: CheckCircle2,
  completed: CheckCircle2,
  failed: XCircle,
  error: XCircle,
  running: AlertTriangle,
  pending: AlertTriangle,
}
const statusColors: Record<string, string> = {
  ok: 'text-neon-green',
  completed: 'text-neon-green',
  failed: 'text-red-400',
  error: 'text-red-400',
  running: 'text-neon-amber',
  pending: 'text-neon-amber',
}

interface RecentEvent {
  type: string
  status: string
  timestamp: string
  data?: any
}

interface SourceDetail {
  id: string
  name: string
  kind: string
  channel: string
  url_set: boolean
  url_tail: string
  enabled: boolean
  created_at?: number
  updated_at?: number
  probe?: { ok?: boolean; status?: number | null; detail?: string }
  recent_events?: RecentEvent[]
}

export default function RepositoryDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [source, setSource] = useState<SourceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [testing, setTesting] = useState(false)

  const headers = useCallback((): Record<string, string> => {
    const token = localStorage.getItem('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [])

  const load = useCallback(async () => {
    if (!id) return
    setLoading(true)
    try {
      const response = await fetch(`/api/v1/integrations/webhooks/${id}`, { headers: headers() })
      if (response.status === 404) {
        setError('Source not found (it may have been deleted).')
        setSource(null)
      } else if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      } else {
        setSource(await response.json())
        setError(null)
      }
    } catch (e: any) {
      setError(e.message || 'Failed to load source')
    } finally {
      setLoading(false)
    }
  }, [id, headers])

  useEffect(() => { load() }, [load])

  const toggleEnabled = async () => {
    if (!source) return
    setBusy(true)
    try {
      await fetch('/api/v1/integrations/webhooks', {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: source.id, name: source.name, kind: source.kind, enabled: !source.enabled }),
      })
      await load()
    } finally {
      setBusy(false)
    }
  }

  const testConnection = async () => {
    if (!source) return
    setTesting(true)
    try {
      const response = await fetch(`/api/v1/integrations/webhooks/${source.id}/test`, {
        method: 'POST',
        headers: headers(),
      })
      if (response.ok) {
        const body = await response.json()
        setSource({ ...source, probe: body.result })
      }
    } finally {
      setTesting(false)
    }
  }

  const remove = async () => {
    if (!source || !window.confirm(`Delete "${source.name}"? This cannot be undone.`)) return
    setBusy(true)
    try {
      await fetch(`/api/v1/integrations/webhooks/${source.id}`, { method: 'DELETE', headers: headers() })
      navigate('/repositories')
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return (
      <div className="card-cyber p-12 text-center">
        <div className="w-8 h-8 border-2 border-neon-magenta border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-cyber-400 font-mono tracking-wider">LOADING SOURCE…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card-cyber flex items-center gap-4 p-8">
        <AlertTriangle className="w-6 h-6 text-neon-amber shrink-0" />
        <div>
          <p className="text-white font-medium mb-1">Source unavailable</p>
          <p className="text-cyber-400 text-sm mb-4">{error}</p>
          <Link to="/repositories" className="btn-cyber-sm gap-2">
            <ArrowLeft className="w-4 h-4" /> Back to Repositories
          </Link>
        </div>
      </div>
    )
  }

  if (!source) return null

  const probe = source.probe || { ok: false, status: null, detail: 'Not tested yet' }

  return (
    <div className="space-y-6">
      <Link to="/repositories" className="inline-flex items-center gap-2 text-cyber-400 hover:text-neon-cyan transition-colors text-sm font-mono">
        <ArrowLeft className="w-4 h-4" /> BACK TO REPOSITORIES
      </Link>

      {/* Header */}
      <div className="card-cyber p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-cyber-800 flex items-center justify-center">
            <GitBranch className="w-6 h-6 text-neon-cyan" />
          </div>
          <div>
            <h1 className="text-2xl font-bold font-display text-white flex items-center gap-3">
              {source.name}
              <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-mono ${
                source.enabled ? 'bg-neon-green/20 text-neon-green border border-neon-green/30' : 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${source.enabled ? 'bg-neon-green' : 'bg-neon-amber'}`} />
                {source.enabled ? 'Active' : 'Disabled'}
              </span>
            </h1>
            <p className="text-cyber-400 text-sm font-mono mt-1">channel-{source.id} · {source.channel}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={testConnection} disabled={testing || busy} className="btn-cyber-sm gap-2 disabled:opacity-60">
            <Zap className="w-4 h-4" /> {testing ? 'Testing…' : 'Test'}
          </button>
          <button onClick={toggleEnabled} disabled={busy} className="btn-cyber-sm gap-2 disabled:opacity-60">
            <Power className="w-4 h-4" /> {source.enabled ? 'Disable' : 'Enable'}
          </button>
          <button onClick={remove} disabled={busy} className="btn-cyber-sm gap-2 bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 disabled:opacity-60">
            <Trash2 className="w-4 h-4" /> Delete
          </button>
        </div>
      </div>

      {/* Config + probe */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card-cyber p-6 md:col-span-2">
          <h2 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-4">Configuration</h2>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <dt className="text-xs font-mono text-cyber-500 uppercase tracking-wider mb-1">Channel</dt>
              <dd className="text-white font-medium">{source.channel}</dd>
            </div>
            <div>
              <dt className="text-xs font-mono text-cyber-500 uppercase tracking-wider mb-1">Kind</dt>
              <dd className="text-white font-mono text-sm">{source.kind}</dd>
            </div>
            <div>
              <dt className="text-xs font-mono text-cyber-500 uppercase tracking-wider mb-1">Webhook Endpoint</dt>
              <dd className="text-white font-mono text-sm break-all">{source.url_set ? (source.url_tail || 'Configured') : 'Not set'}</dd>
            </div>
            <div>
              <dt className="text-xs font-mono text-cyber-500 uppercase tracking-wider mb-1">Updated</dt>
              <dd className="text-white font-mono text-sm">
                {source.updated_at ? new Date(source.updated_at * 1000).toLocaleString() : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-mono text-cyber-500 uppercase tracking-wider mb-1">Created</dt>
              <dd className="text-white font-mono text-sm">
                {source.created_at ? new Date(source.created_at * 1000).toLocaleString() : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-mono text-cyber-500 uppercase tracking-wider mb-1">Source ID</dt>
              <dd className="text-white font-mono text-sm">{source.id}</dd>
            </div>
          </dl>
        </div>

        <div className="card-cyber p-6">
          <h2 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-4">Connection Status</h2>
          <div className="flex items-start gap-3">
            {(() => {
              const Icon = probe.ok ? CheckCircle2 : XCircle
              return <Icon className={`w-6 h-6 shrink-0 ${probe.ok ? 'text-neon-green' : 'text-red-400'}`} />
            })()}
            <div>
              <p className={`font-medium font-mono text-sm ${probe.ok ? 'text-neon-green' : 'text-red-400'}`}>
                {probe.ok ? 'ENDPOINT REACHABLE' : 'ENDPOINT UNREACHABLE'}
              </p>
              <p className="text-cyber-400 text-xs mt-1">{probe.detail || 'No detail'}</p>
              {probe.status && <p className="text-cyber-500 text-xs font-mono mt-2">HTTP {probe.status}</p>}
            </div>
          </div>
        </div>
      </div>

      {/* Recent events for this source */}
      <div className="card-cyber p-6">
        <h2 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-4">
          Recent Pipeline Activity
          <span className="text-neon-magenta ml-2">{source.recent_events?.length || 0}</span>
        </h2>
        {source.recent_events && source.recent_events.length > 0 ? (
          <div className="font-mono text-xs space-y-1">
            {source.recent_events.map((event, i) => {
              const Icon = statusIcons[event.status] || AlertTriangle
              const color = statusColors[event.status] || 'text-cyber-400'
              return (
                <div key={i} className="flex items-center gap-3 py-2 px-2 rounded hover:bg-cyber-800/30">
                  <Icon className={`w-4 h-4 shrink-0 ${color}`} />
                  <span className="px-1.5 py-0.5 rounded bg-cyber-800 text-cyber-300">{event.type}</span>
                  <span className="text-cyber-400 flex-1 truncate">
                    {event.data?.action || event.data?.name || event.type}
                  </span>
                  <span className="text-cyber-500 shrink-0">
                    {event.timestamp ? new Date((event.timestamp.endsWith('Z') ? event.timestamp : event.timestamp + 'Z')).toLocaleString() : ''}
                  </span>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="py-10 text-center">
            <p className="text-cyber-500 font-mono tracking-wider mb-2">NO ACTIVITY FOR THIS SOURCE YET</p>
            <p className="text-cyber-500 text-sm">Use the Test button above to fire a probe event.</p>
          </div>
        )}
      </div>
    </div>
  )
}