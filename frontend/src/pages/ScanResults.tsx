import { useState, useEffect, useCallback, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Bug,
  ShieldAlert,
  Lock,
  FileCode2,
  FlaskConical,
  ScanSearch,
  AlertTriangle,
  Fingerprint,
  Boxes,
  RefreshCw,
} from 'lucide-react'

interface Finding {
  id: string
  category: string
  severity: string
  file: string
  line: number
  message: string
  remediation?: string
}

interface Summary {
  total: number
  critical?: number
  high?: number
  medium?: number
  low?: number
  info?: number
}

interface Report {
  full_name: string
  scanner: string
  ref: string
  scanned_at?: string
  duration?: number
  status: string
  error?: string | null
  files_scanned?: number
  truncated?: boolean
  summary: Summary
  findings: Finding[]
}

const severityBadge: Record<string, string> = {
  critical: 'badge-critical',
  high: 'badge-high',
  medium: 'badge-medium',
  low: 'badge-low',
  info: 'badge-cyber bg-cyber-700/60 text-cyber-300 border border-cyber-600/40',
}

const categoryIcon: Record<string, any> = {
  secret: Fingerprint,
  vulnerability: ShieldAlert,
  security: Lock,
  bug: Bug,
  dependency: Boxes,
  best_practice: FlaskConical,
}

export default function ScanResults() {
  const { owner = '', name = '' } = useParams()
  const fullName = `${owner}/${name}`
  const [report, setReport] = useState<Report | null>(null)
  const [scanning, setScanning] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openedRows, setOpenedRows] = useState<Set<number>>(new Set())
  const pollTimer = useRef<any>(null)

  const headers = useCallback((): Record<string, string> => {
    const token = localStorage.getItem('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [])

  const load = useCallback(async () => {
    try {
      const response = await fetch(`/api/v1/github/repos/${owner}/${name}/scan`, { headers: headers() })
      if (response.status === 404) throw new Error('Repository not found in the cached list. Go back and refresh repositories.')
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      setScanning(Boolean(data.scanning))
      setReport(data.report || null)
      setError(null)
    } catch (e: any) {
      setError(e.message || 'Failed to load scan results')
    } finally {
      setLoading(false)
    }
  }, [owner, name, headers])

  useEffect(() => {
    load()
    return () => { if (pollTimer.current) clearTimeout(pollTimer.current) }
  }, [load])

  useEffect(() => {
    if (scanning) {
      pollTimer.current = setTimeout(() => load(), 3000)
    }
    return () => { if (pollTimer.current) clearTimeout(pollTimer.current) }
  }, [scanning, load])

  const startScan = async () => {
    setError(null)
    try {
      const response = await fetch(`/api/v1/github/repos/${owner}/${name}/scan`, {
        method: 'POST',
        headers: headers(),
      })
      if (response.status === 409) { setScanning(true); return }
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.error || `HTTP ${response.status}`)
      }
      setScanning(true)
      setLoading(true)
      load()
    } catch (e: any) {
      setError(e.message || 'Failed to start scan')
    }
  }

  const toggleRow = (i: number) => {
    setOpenedRows(prev => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  const summary = report?.summary
  const ordering: Array<[string, number | undefined]> = [
    ['critical', summary?.critical], ['high', summary?.high], ['medium', summary?.medium],
    ['low', summary?.low], ['info', summary?.info],
  ]
  const categories = Array.from(new Set((report?.findings || []).map(f => f.category)))

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Link to="/repositories" className="inline-flex items-center gap-1.5 text-sm text-cyber-400 hover:text-neon-cyan transition-colors mb-2">
            <ArrowLeft className="w-4 h-4" /> Repositories
          </Link>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> {fullName}
          </h1>
          <p className="text-cyber-400 mt-1 font-mono text-sm">Deterministic rule scan · no AI · v{report?.scanner || '—'}</p>
        </div>
        <div className="flex items-center gap-2">
          {scanning && (
            <span className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-neon-cyan/10 border border-neon-cyan/30 text-neon-cyan text-sm font-mono">
              <RefreshCw className="w-4 h-4 animate-spin" /> SCANNING
            </span>
          )}
          <button onClick={startScan} disabled={scanning} className="btn-cyber-magenta inline-flex items-center gap-2 disabled:opacity-60">
            <ScanSearch className="w-4 h-4" /> Scan Again
          </button>
        </div>
      </div>

      {error && !report && (
        <div className="card-cyber p-6 border-red-500/30">
          <p className="text-red-400 font-medium mb-1">Scan unavailable</p>
          <p className="text-cyber-400 text-sm">{error}</p>
        </div>
      )}

      {loading && !report ? (
        <div className="card-cyber p-16 text-center">
          <div className="w-8 h-8 border-2 border-neon-magenta border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-cyber-400 font-mono tracking-wider">LOADING SCAN…</p>
        </div>
      ) : report ? (
        <>
          {report.status === 'error' && (
            <div className="card-cyber p-4 border-red-500/30">
              <p className="text-red-400 font-medium mb-1">Scan failed</p>
              <p className="text-cyber-400 text-sm font-mono">{report.error}</p>
            </div>
          )}

          {report.status === 'completed' && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {ordering.map(([sev, count]) => (
                  <div key={sev} className="card-cyber p-4 text-center">
                    <span className={`badge-cyber ${severityBadge[sev]} mb-2`}>{sev}</span>
                    <p className={`text-3xl font-bold font-display mt-2 ${
                      sev === 'critical' ? 'text-red-400' : sev === 'high' ? 'text-orange-300' :
                      sev === 'medium' ? 'text-amber-300' : sev === 'low' ? 'text-green-300' : 'text-cyber-300'
                    }`}>{count || 0}</p>
                  </div>
                ))}
              </div>

              <div className="card-cyber p-5">
                <div className="flex flex-wrap gap-2 items-center">
                  {categories.map(cat => {
                    const Icon = categoryIcon[cat] || FileCode2
                    return (
                      <span key={cat} className="badge-cyber bg-cyber-800 text-cyber-300 border border-cyber-600/50 inline-flex items-center gap-1.5">
                        <Icon className="w-3.5 h-3.5" /> {cat.replace('_', ' ')}
                      </span>
                    )
                  })}
                  <span className="ml-auto text-xs font-mono text-cyber-500">
                    {report.files_scanned ?? 0} files · {(report.duration ?? 0).toFixed(1)}s · {report.ref}
                    {report.truncated ? ' · truncated' : ''}
                  </span>
                </div>
              </div>

              <div className="card-cyber p-4 md:p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-display font-bold text-lg flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-neon-amber" /> Findings
                  </h2>
                  <span className="text-xs font-mono text-cyber-400">{summary?.total || 0} total</span>
                </div>

                {report.findings.length === 0 ? (
                  <div className="p-10 text-center">
                    <ShieldAlert className="w-14 h-14 mx-auto mb-3 text-neon-green/60" />
                    <p className="text-cyber-300 font-medium">No issues detected</p>
                    <p className="text-cyber-500 text-sm mt-1">This scan of {fullName} came back clean.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {report.findings.map((f, i) => {
                      const Icon = categoryIcon[f.category] || FileCode2
                      const open = openedRows.has(i)
                      return (
                        <button
                          key={`${f.id}-${i}`}
                          onClick={() => toggleRow(i)}
                          className="w-full text-left rounded-xl bg-cyber-800/40 border border-cyber-700/50 hover:border-cyber-600/60 transition-colors p-3 sm:p-4"
                        >
                          <div className="flex items-start gap-3">
                            <span className={`badge-cyber ${severityBadge[f.severity]} shrink-0 mt-0.5`}>{f.severity}</span>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm text-white leading-snug">{f.message}</p>
                              <p className="text-[11px] font-mono text-cyber-500 mt-1 truncate">{f.file}{f.line ? `:${f.line}` : ''}</p>
                            </div>
                            <Icon className="w-4 h-4 text-cyber-500 shrink-0 mt-1" />
                          </div>
                          {open && f.remediation && (
                            <div className="mt-3 ml-9 sm:ml-12 pt-3 border-t border-cyber-700/50">
                              <span className="text-[11px] font-mono text-neon-cyan uppercase tracking-wider">Fix</span>
                              <p className="text-sm text-cyber-300 mt-1 leading-relaxed">{f.remediation}</p>
                            </div>
                          )}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </>
      ) : null}
    </div>
  )
}