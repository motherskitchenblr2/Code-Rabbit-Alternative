import { useState, useEffect, useCallback } from 'react'
import { ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2, Scale, FileText } from 'lucide-react'

const statusColors: Record<string, string> = {
  compliant: 'text-neon-green',
  partial: 'text-neon-amber',
  non_compliant: 'text-red-400',
  not_assessed: 'text-cyber-500',
}
const statusBadge: Record<string, string> = {
  compliant: 'bg-neon-green/20 text-neon-green border border-neon-green/30',
  partial: 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30',
  non_compliant: 'bg-red-500/20 text-red-400 border border-red-500/30',
  not_assessed: 'bg-cyber-800 text-cyber-500 border border-cyber-700/50',
}

interface FrameworkSummary {
  framework: string
  name: string
  status: string
  score: number
  total: number
  compliant?: number
  partial?: number
  non_compliant?: number
  findings?: number
}

export default function ComplianceReport() {
  const [summary, setSummary] = useState<{ frameworks: FrameworkSummary[]; overall: any } | null>(null)
  const [selected, setSelected] = useState<string>('gdpr')
  const [report, setReport] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const headers = useCallback((): Record<string, string> => {
    const token = localStorage.getItem('access_token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [])

  useEffect(() => {
    fetch('/api/v1/compliance/summary', { headers: headers() })
      .then(r => r.json())
      .then(data => {
        setSummary(data)
        if (data.frameworks?.length && !data.frameworks.some((f: any) => f.framework === selected)) {
          setSelected(data.frameworks[0].framework)
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [headers])

  useEffect(() => {
    if (!selected) return
    setLoadingDetail(true)
    fetch(`/api/v1/compliance/report?framework=${selected}`, { headers: headers() })
      .then(r => r.json())
      .then(data => setReport(data))
      .catch(() => setReport(null))
      .finally(() => setLoadingDetail(false))
  }, [selected, headers])

  if (loading) {
    return (
      <div className="card-cyber p-12 text-center">
        <div className="w-8 h-8 border-2 border-neon-magenta border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-cyber-400 font-mono tracking-wider">LOADING COMPLIANCE…</p>
      </div>
    )
  }

  const overall = summary?.overall

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> Compliance Report
          </h1>
          <p className="text-cyber-400 mt-1">
            Automated posture assessment across {summary?.frameworks?.length || 0} frameworks · window: {overall?.window_days || 90} days
          </p>
        </div>
      </div>

      {error && (
        <div className="card-cyber flex items-center gap-3 p-4 border-red-500/30">
          <ShieldAlert className="w-5 h-5 text-red-400 shrink-0" />
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Overall stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card-cyber p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-neon-green/10 flex items-center justify-center">
              <ShieldCheck className="w-6 h-6 text-neon-green" />
            </div>
            <div>
              <p className="text-xs font-mono text-cyber-400 uppercase tracking-wider">Average Score</p>
              <p className="text-3xl font-bold font-display text-white">{overall?.avg_score != null ? `${overall.avg_score}%` : '—'}</p>
            </div>
          </div>
        </div>
        <div className="card-cyber p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-neon-cyan/10 flex items-center justify-center">
              <Scale className="w-6 h-6 text-neon-cyan" />
            </div>
            <div>
              <p className="text-xs font-mono text-cyber-400 uppercase tracking-wider">Frameworks Assessed</p>
              <p className="text-3xl font-bold font-display text-white">
                {overall?.assessed || 0}/{overall?.total || 0}
              </p>
            </div>
          </div>
        </div>
        <div className="card-cyber p-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center">
              <AlertTriangle className="w-6 h-6 text-red-400" />
            </div>
            <div>
              <p className="text-xs font-mono text-cyber-400 uppercase tracking-wider">Non-Compliant Frameworks</p>
              <p className="text-3xl font-bold font-display text-white">{overall?.critical_findings || 0}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Framework summary table */}
        <div className="card-cyber p-6">
          <h2 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-4">Frameworks</h2>
          <div className="space-y-2">
            {(summary?.frameworks || []).map((fw) => (
              <button
                key={fw.framework}
                onClick={() => setSelected(fw.framework)}
                className={`w-full text-left p-3 rounded-lg border transition-all ${
                  selected === fw.framework
                    ? 'bg-neon-magenta/10 border-neon-magenta/30'
                    : 'bg-cyber-800/30 border-cyber-700/50 hover:border-cyber-600/50'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-white">{fw.name}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${statusBadge[fw.status] || statusBadge.not_assessed}`}>
                    {fw.status.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-cyber-400">{fw.total} controls</span>
                  <span className={`text-sm font-bold font-mono ${statusColors[fw.status] || 'text-cyber-400'}`}>{fw.score}%</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Detail panel */}
        <div className="card-cyber p-6 lg:col-span-2">
          <h2 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4" />
            {report?.name || selected.toUpperCase()} — Detailed Report
            {report && <span className={`ml-auto px-2 py-0.5 rounded-full text-[10px] font-mono ${statusBadge[report.status] || ''}`}>{report.status}</span>}
          </h2>

          {loadingDetail ? (
            <div className="py-16 text-center">
              <div className="w-8 h-8 border-2 border-neon-magenta border-t-transparent rounded-full animate-spin mx-auto" />
            </div>
          ) : report ? (
            <div className="space-y-6">
              {/* Score breakdown */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Stat label="Score" value={`${report.score}%`} />
                <Stat label="Compliant" value={String(report.compliant ?? 0)} />
                <Stat label="Partial" value={String(report.partial ?? 0)} />
                <Stat label="Non-Compliant" value={String(report.non_compliant ?? 0)} />
              </div>

              {/* Executive summary */}
              {report.executive_summary && (
                <div>
                  <h3 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-2">Executive Summary</h3>
                  <p className="text-cyber-200 text-sm whitespace-pre-line leading-relaxed">{report.executive_summary}</p>
                </div>
              )}

              {/* Controls */}
              <div>
                <h3 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-3">Controls ({report.controls?.length || 0})</h3>
                <div className="space-y-2 max-h-72 overflow-y-auto pr-2">
                  {(report.controls || []).map((control: any) => (
                    <div key={control.id} className="flex items-start gap-3 p-3 rounded-lg bg-cyber-800/30 border border-cyber-700/40">
                      <div className={`mt-0.5 ${statusColors[control.status] || 'text-cyber-500'}`}>
                        {control.status === 'compliant'
                          ? <CheckCircle2 className="w-4 h-4" />
                          : control.status === 'not_assessed'
                            ? <ShieldAlert className="w-4 h-4" />
                            : <AlertTriangle className="w-4 h-4" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-neon-cyan whitespace-nowrap">{control.id}</span>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono ${statusBadge[control.status] || statusBadge.not_assessed}`}>
                            {control.status.replace('_', ' ')}
                          </span>
                        </div>
                        <p className="text-sm text-cyber-200 mt-1">{control.title}</p>
                        {control.category && (
                          <p className="text-xs text-cyber-500 font-mono mt-1">category: {control.category}</p>
                        )}
                      </div>
                    </div>
                  ))}
                  {(!report.controls || report.controls.length === 0) && (
                    <p className="text-cyber-500 font-mono text-sm">No controls assessed for this framework.</p>
                  )}
                </div>
              </div>

              {/* Recommendations */}
              {report.recommendations && report.recommendations.length > 0 && (
                <div>
                  <h3 className="text-sm font-mono text-cyber-400 uppercase tracking-wider mb-3">
                    Recommendations ({report.recommendations.length})
                  </h3>
                  <ul className="space-y-2">
                    {report.recommendations.map((rec: any, i: number) => (
                      <li key={i} className="flex items-start gap-3 p-3 rounded-lg bg-neon-amber/5 border border-neon-amber/20">
                        <AlertTriangle className="w-4 h-4 text-neon-amber mt-0.5 shrink-0" />
                        <span className="text-sm text-cyber-200">{typeof rec === 'string' ? rec : rec.title || JSON.stringify(rec)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="py-16 text-center text-cyber-500 font-mono tracking-wider">
              NO REPORT AVAILABLE FOR THIS FRAMEWORK
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 rounded-lg bg-cyber-800/30 border border-cyber-700/40">
      <p className="text-xs font-mono text-cyber-400 uppercase tracking-wider">{label}</p>
      <p className="text-xl font-bold font-mono text-white mt-1">{value}</p>
    </div>
  )
}