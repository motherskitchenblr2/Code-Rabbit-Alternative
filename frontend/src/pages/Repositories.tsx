import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Plus,
  Search,
  GitBranch,
  X,
  Eye,
  ExternalLink,
  Trash2,
  Power,
  AlertTriangle,
} from 'lucide-react'

interface Source {
  id: string
  name: string
  kind: string
  channel: string
  url_tail: string
  enabled: boolean
  created_at?: number
}

const kindIcon: Record<string, string> = {
  slack: 'neon-cyan',
  discord: 'neon-magenta',
  custom: 'neon-amber',
}

export default function Repositories() {
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'active' | 'idle'>('all')
  const [showAddModal, setShowAddModal] = useState(false)
  const [busy, setBusy] = useState(false)

  const headers = useCallback((): Record<string, string> => {
    const token = localStorage.getItem('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [])

  const load = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/integrations/webhooks', { headers: headers() })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      setSources((data.webhooks || []).map((w: any) => ({
        id: w.id,
        name: w.name,
        kind: w.kind,
        channel: w.channel,
        url_tail: w.url_tail,
        enabled: w.enabled,
        created_at: w.created_at,
      })))
      setError(null)
    } catch (e: any) {
      setError(e.message || 'Failed to load sources')
    } finally {
      setLoading(false)
    }
  }, [headers])

  useEffect(() => { load() }, [load])

  const toggleEnabled = async (src: Source) => {
    setBusy(true)
    try {
      const response = await fetch('/api/v1/integrations/webhooks', {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: src.id, name: src.name, kind: src.kind, enabled: !src.enabled }),
      })
      if (response.ok) await load()
    } finally {
      setBusy(false)
    }
  }

  const deleteSource = async (src: Source) => {
    if (!window.confirm(`Delete "${src.name}"?`)) return
    setBusy(true)
    try {
      await fetch(`/api/v1/integrations/webhooks/${src.id}`, { method: 'DELETE', headers: headers() })
      await load()
    } finally {
      setBusy(false)
    }
  }

  const filteredSources = sources
    .filter(src => {
      if (filter !== 'all' && (filter === 'active') !== src.enabled) return false
      if (search && !src.name.toLowerCase().includes(search.toLowerCase()) &&
          !src.channel.toLowerCase().includes(search.toLowerCase()) &&
          !src.kind.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
    .sort((a, b) => (a.name || '').localeCompare(b.name || ''))

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> Repositories
          </h1>
          <p className="text-cyber-400 mt-1">Monitored webhook sources wired into the pipeline</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn-cyber-magenta flex items-center gap-2 self-start"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden md:inline">Add Repository</span>
          <span className="md:hidden">Add Repo</span>
        </button>
      </div>

      {/* Toolbar */}
      <div className="card-cyber p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-cyber-500" />
            <input
              type="text"
              placeholder="Search repositories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-cyber pl-10"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              className="input-cyber py-2"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="idle">Idle</option>
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="card-cyber flex items-start gap-3 p-4 border-red-500/30">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
          <div>
            <p className="text-red-400 font-medium mb-1">Failed to load sources</p>
            <p className="text-cyber-400 text-sm">{error}. Check that the backend is running.</p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="card-cyber p-12 text-center">
          <div className="w-8 h-8 border-2 border-neon-magenta border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-cyber-400 font-mono tracking-wider">LOADING SOURCES…</p>
        </div>
      ) : (
        <>
          {/* Desktop sources table */}
          <div className="card-cyber overflow-hidden hidden md:block">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-cyber-700/50">
                    <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Source</th>
                    <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider hidden md:table-cell">Kind</th>
                    <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider hidden md:table-cell">Endpoint</th>
                    <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider hidden lg:table-cell">Created</th>
                    <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Status</th>
                    <th className="px-4 py-3 text-right text-xs font-mono text-cyber-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSources.map((src) => {
                    const color = kindIcon[src.kind] || 'neon-cyan'
                    return (
                      <tr key={src.id} className="border-b border-cyber-800/50 hover:bg-cyber-800/30 transition-colors">
                        <td className="px-4 py-4">
                          <Link to={`/repositories/${src.id}`} className="flex items-center gap-3 group">
                            <div className={`w-10 h-10 rounded-lg bg-cyber-800 flex items-center justify-center group-hover:bg-${color}/20 transition-colors`}>
                              <GitBranch className={`w-5 h-5 text-${color}`} />
                            </div>
                            <div>
                              <p className="font-medium text-white group-hover:text-neon-cyan transition-colors">{src.name}</p>
                              <p className="text-xs text-cyber-400 truncate max-w-xs">channel-{src.id}</p>
                            </div>
                          </Link>
                        </td>
                        <td className="px-4 py-4 hidden md:table-cell">
                          <span className="text-xs px-2 py-1 bg-cyber-800 rounded text-cyber-300 font-mono">{src.channel}</span>
                        </td>
                        <td className="px-4 py-4 hidden md:table-cell">
                          <span className="text-xs text-cyber-400 font-mono">{src.url_tail || 'Not set'}</span>
                        </td>
                        <td className="px-4 py-4 hidden lg:table-cell">
                          <span className="text-xs text-cyber-400 font-mono">{src.created_at ? new Date(src.created_at * 1000).toLocaleDateString() : '—'}</span>
                        </td>
                        <td className="px-4 py-4">
                          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-mono ${
                            src.enabled ? 'bg-neon-green/20 text-neon-green border border-neon-green/30' : 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30'
                          }`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${src.enabled ? 'bg-neon-green' : 'bg-neon-amber'}`} />
                            {src.enabled ? 'Active' : 'Idle'}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Link to={`/repositories/${src.id}`} className="p-2 rounded-lg bg-cyber-800/50 hover:bg-neon-cyan/10 hover:border-neon-cyan/30 border border-cyber-700/50 transition-colors" aria-label="View">
                              <Eye className="w-4 h-4 text-cyber-400" />
                            </Link>
                            <a href={`https://github.com/${src.name}`} target="_blank" rel="noopener noreferrer" className="p-2 rounded-lg bg-cyber-800/50 hover:bg-neon-magenta/10 hover:border-neon-magenta/30 border border-cyber-700/50 transition-colors" aria-label="Open" hidden>
                              <ExternalLink className="w-4 h-4 text-cyber-400" />
                            </a>
                            <button
                              onClick={() => toggleEnabled(src)}
                              disabled={busy}
                              className="p-2 rounded-lg bg-cyber-800/50 hover:bg-neon-amber/10 hover:border-neon-amber/30 border border-cyber-700/50 transition-colors disabled:opacity-50"
                              aria-label={src.enabled ? 'Disable' : 'Enable'}
                            >
                              <Power className={`w-4 h-4 ${src.enabled ? 'text-neon-amber' : 'text-cyber-400'}`} />
                            </button>
                            <button
                              onClick={() => deleteSource(src)}
                              disabled={busy}
                              className="p-2 rounded-lg bg-cyber-800/50 hover:bg-red-500/10 hover:border-red-500/30 border border-cyber-700/50 transition-colors disabled:opacity-50"
                              aria-label="Delete"
                            >
                              <Trash2 className="w-4 h-4 text-red-400" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {filteredSources.length === 0 && (
              <div className="p-12 text-center">
                <GitBranch className="w-16 h-16 mx-auto mb-4 text-cyber-700" />
                <h3 className="text-lg font-medium text-cyber-300 mb-2">No repositories found</h3>
                <p className="text-cyber-500 mb-4">Configure a webhook source to start monitoring</p>
                <button className="btn-cyber-magenta" onClick={() => setShowAddModal(true)}>
                  Add Repository
                </button>
              </div>
            )}
          </div>

          {/* Mobile cards */}
          <div className="grid grid-cols-1 gap-3 md:hidden">
            {filteredSources.map((src) => (
              <div key={src.id} className="card-cyber p-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-cyber-800 flex items-center justify-center flex-shrink-0">
                    <GitBranch className="w-5 h-5 text-neon-cyan" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <Link to={`/repositories/${src.id}`} className="block">
                      <p className="font-medium text-white truncate">{src.name}</p>
                      <p className="text-xs text-cyber-400 font-mono mt-0.5">{src.channel}</p>
                    </Link>
                    <div className="flex items-center gap-2 mt-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-mono ${
                        src.enabled ? 'bg-neon-green/20 text-neon-green border border-neon-green/30' : 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30'
                      }`}>
                        {src.enabled ? 'Active' : 'Idle'}
                      </span>
                      <span className="text-xs text-cyber-400 font-mono truncate">{src.url_tail || 'No endpoint'}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-cyber-700/50">
                  <Link to={`/repositories/${src.id}`} className="btn-cyber-sm flex-1 items-center justify-center gap-1.5 bg-cyber-800/50 border border-cyber-700/50 text-cyber-200 hover:bg-cyber-700/50">
                    <Eye className="w-4 h-4" /> View
                  </Link>
                  <button
                    onClick={() => toggleEnabled(src)}
                    disabled={busy}
                    className="btn-cyber-sm flex-1 items-center justify-center gap-1.5 bg-cyber-800/50 border border-cyber-700/50 text-cyber-200 hover:bg-cyber-700/50 disabled:opacity-50"
                  >
                    <Power className="w-4 h-4" /> {src.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button
                    onClick={() => deleteSource(src)}
                    disabled={busy}
                    className="btn-cyber-sm items-center justify-center bg-cyber-800/50 border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
            {filteredSources.length === 0 && (
              <div className="card-cyber p-10 text-center">
                <GitBranch className="w-16 h-16 mx-auto mb-4 text-cyber-700" />
                <h3 className="text-lg font-medium text-cyber-300 mb-2">No repositories found</h3>
                <button className="btn-cyber-magenta" onClick={() => setShowAddModal(true)}>
                  Add Repository
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <p className="text-cyber-400 text-sm">Showing {filteredSources.length} of {sources.length} repositories</p>
          </div>
        </>
      )}

      {/* Add repository modal */}
      {showAddModal && (
        <AddSourceModal
          onClose={() => setShowAddModal(false)}
          onSaved={() => { setShowAddModal(false); load() }}
        />
      )}
    </div>
  )
}

function AddSourceModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState('')
  const [kind, setKind] = useState('slack')
  const [url, setUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    setSaving(true)
    setError(null)
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch('/api/v1/integrations/webhooks', {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, kind, url }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`)
      onSaved()
    } catch (e: any) {
      setError(e.message || 'Failed to save source')
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" role="dialog" aria-modal="true">
      <div className="card-cyber w-full max-w-md p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-lg bg-cyber-800/50 hover:bg-red-500/10 transition-colors"
          aria-label="Close"
        >
          <X className="w-4 h-4 text-cyber-400" />
        </button>
        <h2 className="text-xl font-bold font-display mb-1 flex items-center gap-2">
          <span className="text-neon-magenta">{'>_'}</span> Add Repository
        </h2>
        <p className="text-cyber-400 text-sm mb-6">Register a webhook endpoint as a monitored source.</p>

        <form onSubmit={(e) => { e.preventDefault(); submit() }} className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">{error}</div>
          )}
          <div>
            <label className="block text-xs font-mono text-cyber-400 uppercase tracking-wider mb-1.5" htmlFor="src-name">Name</label>
            <input
              id="src-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. slack-pr-reviews"
              className="input-cyber"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-mono text-cyber-400 uppercase tracking-wider mb-1.5" htmlFor="src-kind">Kind</label>
            <select id="src-kind" value={kind} onChange={(e) => setKind(e.target.value)} className="input-cyber">
              <option value="slack">Slack</option>
              <option value="discord">Discord</option>
              <option value="custom">Custom Webhook</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-mono text-cyber-400 uppercase tracking-wider mb-1.5" htmlFor="src-url">Webhook URL</label>
            <input
              id="src-url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://hooks.slack.com/services/…"
              className="input-cyber"
              required
            />
            <p className="text-cyber-500 text-xs mt-1">Only http(s) endpoints are accepted.</p>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-cyber-sm flex-1 bg-cyber-800/50 border border-cyber-700/50 text-cyber-200 hover:bg-cyber-700/50"
            >
              Cancel
            </button>
            <button type="submit" disabled={saving} className="btn-cyber-magenta flex-1 disabled:opacity-60">
              {saving ? 'Saving…' : 'Add & Test'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}