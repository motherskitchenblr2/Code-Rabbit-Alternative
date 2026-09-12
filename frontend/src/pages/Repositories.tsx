import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  GitBranch,
  Lock,
  BookMarked,
  ExternalLink,
  Search,
  RefreshCw,
  ScanSearch,
  AlertTriangle,
  Archive,
  Settings2,
} from 'lucide-react'

interface ScanSummary {
  scanned_at?: string
  status: string
  summary?: {
    total?: number
    critical?: number
    high?: number
    medium?: number
    low?: number
    info?: number
  }
  files_scanned?: number
}

interface Repo {
  owner: string
  name: string
  full_name: string
  private: boolean
  fork: boolean
  archived: boolean
  language: string | null
  description: string | null
  html_url: string
  default_branch: string
  updated_at?: string
  pushed_at?: string
  size_kb?: number
  scan: ScanSummary | null
}

interface RepoListResponse {
  configured: boolean
  synced_at: number
  private: number
  public: number
  total: number
  repos: Repo[]
  detail?: string
}

function scanLink(repo: Repo) {
  return `/repositories/${repo.owner}/${repo.name}/scan`
}

export default function Repositories() {
  const [data, setData] = useState<RepoListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState<'all' | 'public' | 'private'>('all')
  const [scanningRepos, setScanningRepos] = useState<Record<string, boolean>>({})

  const headers = useCallback((): Record<string, string> => {
    const token = localStorage.getItem('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [])

  const load = useCallback(async (opts?: { refresh?: boolean }) => {
    const url = opts?.refresh
      ? '/api/v1/github/repos/refresh'
      : '/api/v1/github/repos'
    try {
      if (opts?.refresh) setRefreshing(true)
      const response = await fetch(url, {
        method: opts?.refresh ? 'POST' : 'GET',
        headers: headers(),
        ...(opts?.refresh ? {} : {}),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const json = await response.json()
      setData(json)
      setError(null)
    } catch (e: any) {
      setError(e.message || 'Failed to load repositories')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [headers])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!data?.repos?.length) return
    const hasActive = data.repos.some(r => scanningRepos[r.full_name] || r.scan?.status === 'error')
    if (!hasActive) return
    const timer = setTimeout(() => load(), 5000)
    return () => clearTimeout(timer)
  }, [data, scanningRepos, load])

  const startScan = async (repo: Repo) => {
    setScanningRepos(prev => ({ ...prev, [repo.full_name]: true }))
    try {
      const response = await fetch(`/api/v1/github/repos/${repo.owner}/${repo.name}/scan`, {
        method: 'POST',
        headers: headers(),
      })
      if (response.status === 409) return
      if (!response.ok) {
        const json = await response.json().catch(() => ({}))
        throw new Error(json.error || `HTTP ${response.status}`)
      }
      setTimeout(() => load(), 3000)
    } catch (e: any) {
      setError(e.message || 'Failed to start scan')
      setScanningRepos(prev => ({ ...prev, [repo.full_name]: false }))
    }
  }

  const visibleRepos = (data?.repos || [])
    .filter(r => tab === 'all' || (tab === 'public' ? !r.private : r.private))
    .filter(r => {
      if (!search) return true
      const q = search.toLowerCase()
      return r.full_name.toLowerCase().includes(q) ||
        (r.description || '').toLowerCase().includes(q) ||
        (r.language || '').toLowerCase().includes(q)
    })
    .sort((a, b) => String(b.pushed_at || '').localeCompare(String(a.pushed_at || '')))

  const repos = data?.repos || []
  const counts = { all: data?.total ?? 0, public: data?.public ?? 0, private: data?.private ?? 0 }

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> Repositories
          </h1>
          <p className="text-cyber-400 mt-1">GitHub repositories · deterministic scan, no AI</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="badge-cyber bg-cyber-800 text-cyber-300 border border-cyber-600/50 font-mono text-xs">
            {counts.all} total · {counts.public} public · {counts.private} private
          </span>
          <button
            onClick={() => load({ refresh: true })}
            disabled={refreshing}
            className="btn-cyber-sm gap-2 disabled:opacity-50 bg-cyber-800/50 border border-cyber-700/50 text-cyber-200 hover:bg-cyber-700/50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {!loading && data && !data.configured && (
        <div className="card-cyber p-8 border-neon-amber/30">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-neon-amber/10 flex items-center justify-center shrink-0">
              <BookMarked className="w-6 h-6 text-neon-amber" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-display font-bold text-white mb-1">Connect a GitHub token</h2>
              <p className="text-cyber-400 text-sm leading-relaxed">
                {data.detail || 'Save a GitHub personal access token under Settings → Integrations to load your repositories.'}
              </p>
            </div>
            <Link to="/settings" className="btn-cyber-sm gap-2 self-start sm:self-auto">
              <Settings2 className="w-4 h-4" /> Open Settings
            </Link>
          </div>
        </div>
      )}

      <div className="card-cyber p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-cyber-500" />
            <input
              type="text"
              placeholder="Search owner, repo, description…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-cyber pl-10"
            />
          </div>
          <div className="flex items-center gap-1 bg-cyber-900 rounded-lg p-1 border border-cyber-700/50">
            {(['all', 'public', 'private'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1.5 rounded-md text-sm font-mono transition-colors capitalize ${
                  tab === t ? 'bg-neon-cyan/20 text-neon-cyan' : 'text-cyber-400 hover:text-cyber-200'
                }`}
              >
                {t} <span className="opacity-70">({counts[t]})</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="card-cyber flex items-start gap-3 p-4 border-red-500/30">
          <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
          <div>
            <p className="text-red-400 font-medium mb-1">Failed to load repositories</p>
            <p className="text-cyber-400 text-sm">{error}. Check the backend log.</p>
          </div>
        </div>
      )}

      {loading ? (
        <div className="card-cyber p-12 text-center">
          <div className="w-8 h-8 border-2 border-neon-magenta border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-cyber-400 font-mono tracking-wider">LOADING REPOSITORIES…</p>
        </div>
      ) : data && data.configured && repos.length === 0 ? (
        <div className="card-cyber p-12 text-center">
          <GitBranch className="w-16 h-16 mx-auto mb-4 text-cyber-700" />
          <h3 className="text-lg font-medium text-cyber-300 mb-2">No repositories found</h3>
          <p className="text-cyber-500 mb-4">The token has access to 0 repositories. Refresh to re-sync from GitHub.</p>
          <button onClick={() => load({ refresh: true })} className="btn-cyber-magenta gap-2">
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      ) : data && data.configured ? (
        <>
          {/* Desktop table */}
          <div className="card-cyber overflow-hidden hidden md:block">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-cyber-700/50">
                    <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Repository</th>
                    <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Visibility</th>
                    <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Last Scan</th>
                    <th className="px-4 py-3 text-right text-xs font-mono text-cyber-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRepos.map((repo) => (
                    <tr key={repo.full_name} className="border-b border-cyber-800/50 hover:bg-cyber-800/30 transition-colors">
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-cyber-800 flex items-center justify-center flex-shrink-0">
                            {repo.private ? <Lock className="w-5 h-5 text-neon-amber" /> : <GitBranch className="w-5 h-5 text-neon-cyan" />}
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-white truncate">{repo.full_name}</p>
                              {repo.archived && (
                                <span className="badge-cyber bg-cyber-800 text-cyber-400 border border-cyber-600/50 inline-flex items-center gap-1 text-[10px]">
                                  <Archive className="w-3 h-3" /> archived
                                </span>
                              )}
                              {repo.fork && (
                                <span className="badge-cyber bg-cyber-800 text-cyber-400 border border-cyber-600/50 text-[10px]">fork</span>
                              )}
                            </div>
                            {repo.description && <p className="text-xs text-cyber-400 truncate max-w-[28rem] mt-0.5">{repo.description}</p>}
                            <p className="text-[11px] font-mono text-cyber-500 mt-0.5">
                              {repo.language || 'n/a'} · pushed {repo.pushed_at ? new Date(repo.pushed_at).toLocaleDateString() : '—'}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`badge-cyber text-xs ${
                          repo.private
                            ? 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30'
                            : 'bg-neon-green/20 text-neon-green border border-neon-green/30'
                        }`}>
                          {repo.private ? 'Private' : 'Public'}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        {scanningRepos[repo.full_name] ? (
                          <span className="inline-flex items-center gap-2 text-xs font-mono text-neon-cyan">
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" /> scanning
                          </span>
                        ) : repo.scan ? (
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {repo.scan.summary?.critical ? <span className="badge-critical">C{repo.scan.summary.critical}</span> : null}
                            {repo.scan.summary?.high ? <span className="badge-high">H{repo.scan.summary.high}</span> : null}
                            {repo.scan.summary?.medium ? <span className="badge-medium">M{repo.scan.summary.medium}</span> : null}
                            {!repo.scan.summary?.critical && !repo.scan.summary?.high && !repo.scan.summary?.medium && (
                              <span className="text-xs font-mono text-cyber-500">
                                {repo.scan.status === 'error' ? 'failed' : 'clean'}
                              </span>
                            )}
                            {repo.scan.scanned_at && (
                              <span className="text-[10px] font-mono text-cyber-500 block w-full">
                                {new Date(repo.scan.scanned_at).toLocaleString()}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs font-mono text-cyber-500">Not scanned</span>
                        )}
                      </td>
                      <td className="px-4 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => startScan(repo)}
                            disabled={Boolean(scanningRepos[repo.full_name])}
                            className="p-2 rounded-lg bg-cyber-800/50 hover:bg-neon-magenta/10 hover:border-neon-magenta/30 border border-cyber-700/50 transition-colors disabled:opacity-40"
                            aria-label={`Scan ${repo.full_name}`}
                          >
                            <ScanSearch className={`w-4 h-4 ${scanningRepos[repo.full_name] ? 'text-neon-magenta animate-pulse' : 'text-cyber-200'}`} />
                          </button>
                          {repo.scan && (
                            <Link to={scanLink(repo)} className="p-2 rounded-lg bg-cyber-800/50 hover:bg-neon-cyan/10 hover:border-neon-cyan/30 border border-cyber-700/50 transition-colors" aria-label="View report">
                              <BookMarked className="w-4 h-4 text-cyber-400 hover:text-neon-cyan" />
                            </Link>
                          )}
                          <a href={`https://github.com/${repo.full_name}`} target="_blank" rel="noopener noreferrer" className="p-2 rounded-lg bg-cyber-800/50 hover:bg-neon-cyan/10 hover:border-neon-cyan/30 border border-cyber-700/50 transition-colors" aria-label="Open on GitHub">
                            <ExternalLink className="w-4 h-4 text-cyber-400" />
                          </a>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {visibleRepos.length === 0 && (
              <div className="p-12 text-center">
                <Search className="w-14 h-14 mx-auto mb-3 text-cyber-700" />
                <p className="text-cyber-400">No repositories match this filter.</p>
              </div>
            )}
          </div>

          {/* Mobile cards */}
          <div className="grid grid-cols-1 gap-3 md:hidden">
            {visibleRepos.map((repo) => (
              <div key={repo.full_name} className="card-cyber p-4">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-cyber-800 flex items-center justify-center flex-shrink-0">
                    {repo.private ? <Lock className="w-5 h-5 text-neon-amber" /> : <GitBranch className="w-5 h-5 text-neon-cyan" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white truncate">{repo.full_name}</p>
                    {repo.description && <p className="text-xs text-cyber-400 truncate mt-0.5">{repo.description}</p>}
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      <span className={`badge-cyber text-[10px] ${
                        repo.private
                          ? 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30'
                          : 'bg-neon-green/20 text-neon-green border border-neon-green/30'
                      }`}>
                        {repo.private ? 'Private' : 'Public'}
                      </span>
                      <span className="text-[11px] font-mono text-cyber-500">{repo.language || 'n/a'}</span>
                      {repo.scan?.summary?.critical ? <span className="badge-critical">C{repo.scan.summary.critical}</span> : null}
                      {repo.scan?.summary?.high ? <span className="badge-high">H{repo.scan.summary.high}</span> : null}
                      {repo.scan?.summary?.medium ? <span className="badge-medium">M{repo.scan.summary.medium}</span> : null}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-3 pt-3 border-t border-cyber-700/50">
                  <button
                    onClick={() => startScan(repo)}
                    disabled={Boolean(scanningRepos[repo.full_name])}
                    className="btn-cyber-sm flex-1 items-center justify-center gap-1.5 bg-cyber-800/50 border border-cyber-700/50 text-cyber-200 hover:bg-cyber-700/50 disabled:opacity-50"
                  >
                    <ScanSearch className="w-4 h-4" /> {scanningRepos[repo.full_name] ? 'Scanning…' : 'Scan'}
                  </button>
                  {repo.scan && (
                    <Link to={scanLink(repo)} className="btn-cyber-sm flex-1 items-center justify-center gap-1.5 bg-cyber-800/50 border border-cyber-700/50 text-cyber-200 hover:bg-cyber-700/50">
                      <BookMarked className="w-4 h-4" /> Results
                    </Link>
                  )}
                  <a href={`https://github.com/${repo.full_name}`} target="_blank" rel="noopener noreferrer" className="p-2 rounded-lg bg-cyber-800/50 border border-cyber-700/50 hover:bg-cyber-700/50 text-cyber-400" aria-label="Open on GitHub">
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </div>
            ))}
            {visibleRepos.length === 0 && (
              <div className="card-cyber p-10 text-center">
                <Search className="w-10 h-10 mx-auto mb-3 text-cyber-700" />
                <p className="text-cyber-400 text-sm">No repositories match this filter.</p>
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  )
}