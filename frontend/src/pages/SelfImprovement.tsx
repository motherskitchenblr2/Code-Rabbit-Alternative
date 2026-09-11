import React, { useState, useEffect, useCallback } from 'react'
import {
  Brain,
  Cpu,
  Database,
  BookOpen,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Activity,
  Zap,
  Target,
  Sparkles,
  Wrench,
  Ghost,
} from 'lucide-react'

interface Skill {
  name: string
  level: string
  xp: number
  prereqs_met: boolean
}

interface MemoryStats {
  total_memories: number
  by_type?: Record<string, number>
  avg_importance?: number
}

interface Lesson {
  id: number
  subject: string
  rule: string
  confidence: number
  source: string
  applications: number
}

interface Reflex {
  error_type: string
  source_pattern: string
  strategy: string
  max_attempts: number
  backoff_seconds: number
  message: string
}

interface RecentError {
  id: string
  source: string
  error_type: string
  severity: string
  strategy: string
  recovered: boolean
  message?: string
  timestamp?: number
}

interface PlanItem {
  skill: string
  action: string
  reason?: string
  priority?: string
}

interface Goal {
  id: string
  name: string
  description: string
  status: string
  progress?: number
}

interface MemoryEntry {
  id: number
  type: string
  key: string
  content: string
  importance: number
  timestamp?: number
}

interface StatusData {
  status: string
  uptime_seconds: number
  memory: MemoryStats
  skills: Skill[]
  improvement_plan: PlanItem[]
}

interface CortexSnapshot {
  status: StatusData | null
  lessons: Lesson[]
  reflexes: Reflex[]
  errors: RecentError[]
  goals: Goal[]
  memories: MemoryEntry[]
  loading: boolean
  lastUpdated: number | null
}

const LEVEL_ORDER: Record<string, number> = {
  novice: 0,
  competent: 25,
  proficient: 50,
  expert: 100,
}

const LEVEL_COLORS: Record<string, string> = {
  novice: 'bg-cyber-500',
  competent: 'bg-neon-cyan',
  proficient: 'bg-neon-magenta',
  expert: 'bg-neon-amber',
}

const TYPE_COLORS: Record<string, string> = {
  episodic: 'bg-neon-magenta',
  semantic: 'bg-neon-cyan',
  procedural: 'bg-neon-green',
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h ${m}m`
  if (h > 0) return `${h}h ${m}m ${seconds % 60}s`
  return `${m}m ${seconds % 60}s`
}

function skillProgress(skill: Skill): number {
  const tiers = [0, 25, 50, 100]
  const idx = LEVEL_ORDER[skill.level] ?? 0
  const curr = tiers[idx] ?? 0
  const next = tiers[idx + 1] ?? curr + 1
  return Math.min(100, Math.round(((skill.xp - curr) / (next - curr)) * 100)) || 0
}

export default function SelfImprovement() {
  const [data, setData] = useState<CortexSnapshot>({
    status: null,
    lessons: [],
    reflexes: [],
    errors: [],
    goals: [],
    memories: [],
    loading: true,
    lastUpdated: null,
  })
  const [refreshKey, setRefreshKey] = useState(0)

  const fetchAll = useCallback(async () => {
    const grab = async <T,>(url: string): Promise<T | null> => {
      try {
        const res = await fetch(url, { headers: { Accept: 'application/json' } })
        if (!res.ok) return null
        return (await res.json()) as T
      } catch {
        return null
      }
    }

    const [status, lessonsRes, reflexesRes, errorsRes, goalsRes, memRes] = await Promise.all([
      grab<StatusData>('/api/self-improvement/status'),
      grab<{ lessons: Lesson[] }>('/api/self-improvement/learning/lessons'),
      grab<{ reflexes: Reflex[] }>('/api/self-improvement/errors/reflexes'),
      grab<{ errors: RecentError[] }>('/api/self-improvement/errors/recent'),
      grab<{ goals: Goal[] }>('/api/self-improvement/goals'),
      grab<{ memories: MemoryEntry[] }>('/api/self-improvement/memory?limit=25'),
    ])

    setData({
      status,
      lessons: lessonsRes?.lessons ?? [],
      reflexes: reflexesRes?.reflexes ?? [],
      errors: errorsRes?.errors ?? [],
      goals: goalsRes?.goals ?? [],
      memories: memRes?.memories ?? [],
      loading: false,
      lastUpdated: Date.now(),
    })
  }, [])

  useEffect(() => {
    fetchAll()
    const timer = setInterval(fetchAll, 15000)
    return () => clearInterval(timer)
  }, [fetchAll, refreshKey])

  const skills = data.status?.skills ?? []
  const memory = data.status?.memory ?? { total_memories: 0, by_type: {} }
  const plan = data.status?.improvement_plan ?? []
  const byType: Record<string, number> = memory.by_type ?? {}
  const memoryTypes = Object.keys(byType).filter((t) => byType[t] > 0)
  const maxType = Math.max(1, ...Object.values(byType))
  const totalXp = skills.reduce((sum, s) => sum + s.xp, 0)
  const recovered = data.errors.filter((e) => e.recovered).length

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> Self-Improvement
          </h1>
          <p className="text-cyber-400 mt-1 flex items-center gap-2">
            <Brain className="w-4 h-4 text-neon-cyan" />
            Autonomous learning layer — Git-Fix gets better with every review.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-cyber-ghost" onClick={() => setRefreshKey((k) => k + 1)}>
            <RefreshCw className={`w-4 h-4 mr-2 ${data.loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <a href="/api/self-improvement/dashboard" target="_blank" rel="noreferrer" className="btn-cyber-cyan">
            <Activity className="w-4 h-4 mr-2" />
            Live Dashboard
          </a>
        </div>
      </div>

      {data.loading ? (
        <div className="flex items-center justify-center h-96">
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-neon-magenta border-t-transparent rounded-full animate-spin" />
            <p className="text-cyber-400 font-mono">Tapping neural cortex...</p>
          </div>
        </div>
      ) : (
        <div className="space-y-8">
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
            <StatCard title="Memories" value={memory.total_memories} icon={Database} color="neon-cyan" />
            <StatCard title="Total XP" value={totalXp} icon={Zap} color="neon-magenta" />
            <StatCard title="Skills Trained" value={skills.length} icon={Cpu} color="neon-amber" />
            <StatCard title="Reflexes" value={data.reflexes.length} icon={ShieldCheck} color="neon-green" />
            <StatCard title="Errors Handled" value={recovered} icon={Activity} color="red" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="card-cyber p-6">
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-neon-cyan" />
                  Skill Cortex
                </h3>
                <span className="badge-cyber bg-neon-green/20 text-neon-green border-neon-green/30 font-mono">
                  {data.status?.status?.toUpperCase() ?? 'IDLE'}
                </span>
              </div>
              <div className="space-y-4">
                {skills.length === 0 && <EmptyState text="No skills practiced yet." />}
                {skills.map((skill) => {
                  const pct = skillProgress(skill)
                  return (
                    <div key={skill.name}>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-medium text-cyber-200 font-mono">{skill.name}</span>
                        <div className="flex items-center gap-2">
                          <span className="badge-cyber bg-cyber-800 text-cyber-300">{skill.level.toUpperCase()}</span>
                          <span className="text-xs text-cyber-400 font-mono">{skill.xp} XP</span>
                        </div>
                      </div>
                      <div className="h-2 rounded-full bg-cyber-800 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${LEVEL_COLORS[skill.level] ?? 'bg-neon-magenta'} transition-all duration-700`}
                          style={{ width: `${Math.max(pct, 3)}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="mt-5 pt-4 border-t border-cyber-700/50 flex items-center gap-2 text-xs text-cyber-400">
                <Target className="w-4 h-4 text-neon-amber" />
                Next tier: competent (25) → proficient (50) → expert (100)
              </div>
            </div>

            <div className="card-cyber p-6">
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
                  <Database className="w-5 h-5 text-neon-magenta" />
                  Memory Cortex
                </h3>
                <span className="badge-cyber bg-cyber-800 text-cyber-300 font-mono">
                  AVG {memory.avg_importance?.toFixed(2) ?? '0.00'}
                </span>
              </div>
              {memoryTypes.length === 0 && <EmptyState text="No memories stored yet." />}
              {memoryTypes.map((type) => (
                <div key={type} className="mb-3">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium text-cyber-200 font-mono capitalize">{type}</span>
                    <span className="text-xs text-cyber-400 font-mono">{byType[type]}</span>
                  </div>
                  <div className="h-2 rounded-full bg-cyber-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${TYPE_COLORS[type] ?? 'bg-cyber-500'} transition-all duration-700`}
                      style={{ width: `${Math.max((byType[type] / maxType) * 100, 3)}%` }}
                    />
                  </div>
                </div>
              ))}
              <div className="mt-6 max-h-56 overflow-y-auto space-y-2">
                {data.memories.slice(0, 10).map((m) => (
                  <div key={m.id} className="p-2.5 rounded-lg bg-cyber-800/50 border border-cyber-700/30">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className={`badge-cyber ${TYPE_COLORS[m.type] ? `bg-${m.type}/10 text-cyber-200` : 'bg-cyber-700 text-cyber-300'}`}>
                        {m.type.toUpperCase()}
                      </span>
                      <span className="text-[10px] text-cyber-500 font-mono">#{m.id}</span>
                    </div>
                    <p className="text-xs text-cyber-300 truncate">{m.content}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card-cyber">
              <div className="p-6 border-b border-cyber-700/50 flex items-center justify-between">
                <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-neon-cyan" />
                  Learned Lessons
                </h3>
                <span className="badge-cyber bg-neon-cyan/20 text-neon-cyan border-neon-cyan/30">{data.lessons.length}</span>
              </div>
              <div className="divide-y divide-cyber-800/50">
                {data.lessons.length === 0 && <EmptyState text="No lessons learned yet." />}
                {data.lessons.slice(0, 8).map((lesson) => (
                  <div key={lesson.id} className="p-4 hover:bg-cyber-800/30 transition-colors">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <p className="text-sm font-medium text-cyber-100">{lesson.subject}</p>
                      <span className={`text-xs font-mono ${lesson.confidence >= 0.7 ? 'text-neon-green' : lesson.confidence >= 0.4 ? 'text-neon-amber' : 'text-cyber-400'}`}>
                        {(lesson.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-cyber-800 overflow-hidden mb-1.5">
                      <div
                        className={`h-full rounded-full ${lesson.confidence >= 0.7 ? 'bg-neon-green' : lesson.confidence >= 0.4 ? 'bg-neon-amber' : 'bg-cyber-500'} transition-all duration-700`}
                        style={{ width: `${Math.min(100, lesson.confidence * 100)}%` }}
                      />
                    </div>
                    <p className="text-xs text-cyber-400">{lesson.rule}</p>
                    <div className="mt-1.5 flex items-center gap-3 text-[10px] text-cyber-500 font-mono">
                      <span>src: {lesson.source}</span>
                      <span>×{lesson.applications} applied</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-6">
              <div className="card-cyber">
                <div className="p-6 border-b border-cyber-700/50 flex items-center justify-between">
                  <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-neon-green" />
                    Error Reflexes
                  </h3>
                  <span className="badge-cyber bg-neon-green/20 text-neon-green border-neon-green/30">{data.reflexes.length}</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-cyber-700/50">
                        <th className="px-4 py-2.5 text-left text-[10px] font-mono text-cyber-400 uppercase tracking-wider">Error</th>
                        <th className="px-4 py-2.5 text-left text-[10px] font-mono text-cyber-400 uppercase tracking-wider">Strategy</th>
                        <th className="px-4 py-2.5 text-left text-[10px] font-mono text-cyber-400 uppercase tracking-wider hidden sm:table-cell">Attempts</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.reflexes.length === 0 && (
                        <tr><td colSpan={3}><EmptyState text="No reflexes registered." /></td></tr>
                      )}
                      {data.reflexes.map((r, i) => (
                        <tr key={i} className="border-b border-cyber-800/50">
                          <td className="px-4 py-2.5">
                            <p className="text-xs font-mono text-cyber-200">{r.error_type}</p>
                            <p className="text-[10px] text-cyber-500 truncate max-w-[180px]">{r.message}</p>
                          </td>
                          <td className="px-4 py-2.5">
                            <span className={`badge-cyber ${STRATEGY_COLOR(r.strategy)}`}>{r.strategy.toUpperCase()}</span>
                          </td>
                          <td className="px-4 py-2.5 hidden sm:table-cell text-xs text-cyber-400 font-mono">{r.max_attempts}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="card-cyber">
                <div className="p-6 border-b border-cyber-700/50 flex items-center justify-between">
                  <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
                    <Target className="w-5 h-5 text-neon-amber" />
                    Improvement Plan
                  </h3>
                  <Wrench className="w-4 h-4 text-neon-amber" />
                </div>
                <div className="divide-y divide-cyber-800/50">
                  {plan.length === 0 && <EmptyState text="No improvement suggestions yet — practice more skills." />}
                  {plan.map((item, i) => (
                    <div key={i} className="p-4 flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg bg-neon-amber/10 flex items-center justify-center flex-shrink-0">
                        <Sparkles className="w-4 h-4 text-neon-amber" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm text-cyber-100 font-mono">{item.action}</p>
                          {item.priority && (
                            <span className={`badge-cyber ${PRIORITY_COLOR(item.priority)}`}>{item.priority.toUpperCase()}</span>
                          )}
                        </div>
                        {item.reason && <p className="text-xs text-cyber-400 mt-0.5">{item.reason}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="card-cyber">
            <div className="p-6 border-b border-cyber-700/50 flex items-center justify-between">
              <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-400" />
                Recent Error Events
              </h3>
              <span className="text-xs text-cyber-500 font-mono">
                {data.lastUpdated ? `synced ${new Date(data.lastUpdated).toLocaleTimeString()}` : ''}
              </span>
            </div>
            {data.errors.length === 0 ? (
              <EmptyState text="Zero recorded failures. The cortex is calm." />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-6 pt-4">
                {data.errors.slice(0, 6).map((err) => (
                  <div key={err.id} className="p-3 rounded-lg bg-cyber-800/50 border border-cyber-700/30">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-xs font-mono text-cyber-200">{err.error_type}</span>
                      <span className={`badge-cyber ${err.recovered ? 'bg-neon-green/20 text-neon-green border-neon-green/30' : 'bg-red-500/20 text-red-400 border-red-500/30'}`}>
                        {err.recovered ? 'RECOVERED' : 'ESCALATED'}
                      </span>
                    </div>
                    <p className="text-[11px] text-cyber-400 font-mono truncate">{err.source}</p>
                    <p className="text-[11px] text-cyber-500 mt-0.5 capitalize">{err.strategy} · sev {err.severity?.toLowerCase?.() ?? 'unknown'}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ title, value, icon: Icon, color }: { title: string; value: number; icon: React.ComponentType<{ className?: string; style?: React.CSSProperties }>; color: string }) {
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
    <div className="card-cyber p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-mono text-cyber-400 uppercase tracking-wider mb-1">{title}</p>
          <p className="text-2xl font-bold font-display text-white">{value.toLocaleString()}</p>
        </div>
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${bgMap[color] || 'bg-neon-magenta/10'}`}>
          <Icon className="w-5 h-5" style={{ color: colorMap[color] || '#ff00ff' }} />
        </div>
      </div>
    </div>
  )
}

function STRATEGY_COLOR(strategy: string): string {
  switch (strategy) {
    case 'retry':
      return 'bg-neon-cyan/20 text-neon-cyan border-neon-cyan/30'
    case 'fallback':
    case 'degrade':
      return 'bg-neon-amber/20 text-neon-amber border-neon-amber/30'
    case 'skip':
      return 'bg-cyber-700 text-cyber-300'
    default:
      return 'bg-red-500/20 text-red-400 border-red-500/30'
  }
}

function PRIORITY_COLOR(priority: string): string {
  switch (priority) {
    case 'high':
      return 'bg-red-500/20 text-red-400 border-red-500/30'
    case 'medium':
      return 'bg-neon-amber/20 text-neon-amber border-neon-amber/30'
    default:
      return 'bg-cyber-700 text-cyber-300'
  }
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center py-8 text-cyber-500">
      <Ghost className="w-10 h-10 mb-2 text-cyber-700" />
      <p className="text-sm font-mono">{text}</p>
    </div>
  )
}