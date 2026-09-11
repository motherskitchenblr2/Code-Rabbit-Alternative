import { useState, useEffect, useRef, useCallback, FormEvent } from 'react'
import {
  Users,
  Send,
  Square,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  AlertOctagon,
  Loader2,
  User,
  MessageSquare,
} from 'lucide-react'

// ── API helper (mirrors Admin.tsx) ──────────────────────────────────────────

async function api<T>(url: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ message: `HTTP ${res.status}` }))
    throw new Error(body.message || body.error || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

// ── Types ───────────────────────────────────────────────────────────────────

interface AgentStatus {
  status: 'idle' | 'working' | 'done'
  turns: number
  last_at: number | null
  note: string | null
}

interface TranscriptEntry {
  id: string
  kind: 'user' | 'agent' | 'system'
  agent_id: string
  name: string
  title: string
  content: string
  at: number
  synth: boolean
  mentions: string[]
}

interface Session {
  id: string
  request: string
  status: 'running' | 'awaiting_user' | 'done' | 'error'
  phase: string
  created_at: number
  updated_at: number
  error: string | null
  verdict: { level: string; summary: string; advice: string }
  statuses: Record<string, AgentStatus>
  transcript: TranscriptEntry[]
}

interface Agent {
  id: string
  name: string
  title: string
  tagline: string
}

const AGENT_ICONS: Record<string, string> = {
  ceo: '👔',
  orchestrator: '🎯',
  planner: '📋',
  lead: '🚀',
  coder: '💻',
  engineer: '⚙️',
  designer: '🎨',
  devadmin: '🛠️',
  seo: '🔍',
  qa: '🧪',
}

const VERDICT_STYLES: Record<string, { bg: string; border: string; text: string; icon: React.ReactNode }> = {
  safe: {
    bg: 'bg-neon-green/5',
    border: 'border-neon-green/30',
    text: 'text-neon-green',
    icon: <ShieldCheck className="w-5 h-5" />,
  },
  risk: {
    bg: 'bg-neon-amber/5',
    border: 'border-neon-amber/30',
    text: 'text-neon-amber',
    icon: <ShieldAlert className="w-5 h-5" />,
  },
  break: {
    bg: 'bg-red-500/5',
    border: 'border-red-500/30',
    text: 'text-red-400',
    icon: <AlertOctagon className="w-5 h-5" />,
  },
}

// ── Component ───────────────────────────────────────────────────────────────

export default function AgentTeam() {
  const [session, setSession] = useState<Session | null>(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [roster, setRoster] = useState<Agent[]>([])
  const [pollTick, setPollTick] = useState(0)
  const transcriptEnd = useRef<HTMLDivElement>(null)

  // Load roster once
  useEffect(() => {
    api<{ agents: Agent[] }>('/api/v1/agents/roster').then(
      (r) => setRoster(r.agents),
      () => {},
    )
  }, [])

  // Poll session while running
  useEffect(() => {
    if (!session || session.status === 'done') return
    const id = setInterval(() => setPollTick((k) => k + 1), 1200)
    return () => clearInterval(id)
  }, [session?.id, session?.status])

  useEffect(() => {
    if (!session) return
    if (session.status === 'done') return
    api<{ session: Session }>(`/api/v1/agents/sessions/${session.id}`).then(
      (r) => setSession(r.session),
      () => {},
    )
  }, [pollTick])

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEnd.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [session?.transcript.length, session?.status])

  // ── Actions ─────────────────────────────────────────────────────────────

  const handleStart = useCallback(async () => {
    const text = input.trim()
    if (!text) return
    setLoading(true)
    setError(null)
    try {
      const res = await api<{ session: Session }>('/api/v1/agents/sessions', {
        method: 'POST',
        body: JSON.stringify({ request: text }),
      })
      setSession(res.session)
      setInput('')
      setPollTick(0)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to start session')
    } finally {
      setLoading(false)
    }
  }, [input])

  const handleReply = useCallback(async (message: string) => {
    if (!session || !message.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await api<{ session: Session }>(
        `/api/v1/agents/sessions/${session.id}/message`,
        { method: 'POST', body: JSON.stringify({ message: message.trim() }) },
      )
      setSession(res.session)
      setInput('')
      setPollTick(0)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to send message')
    } finally {
      setLoading(false)
    }
  }, [session?.id])

  const handleStop = useCallback(async () => {
    if (!session) return
    try {
      const res = await api<{ session: Session }>(
        `/api/v1/agents/sessions/${session.id}/stop`,
        { method: 'POST' },
      )
      setSession(res.session)
    } catch {
      // ignore
    }
  }, [session?.id])

  const handleReset = useCallback(() => {
    setSession(null)
    setError(null)
    setInput('')
  }, [])

  // ── Derived state ────────────────────────────────────────────────────────

  const isRunning = session?.status === 'running'
  const isAwaiting = session?.status === 'awaiting_user'
  const isDone = session?.status === 'done'
  const isError = session?.status === 'error'
  const verdict = session?.verdict?.level ?? 'review'
  const verdictStyle = VERDICT_STYLES[verdict] ?? VERDICT_STYLES.risk
  const activeAgents = session?.statuses
    ? Object.entries(session.statuses)
        .filter(([, st]) => st.status === 'working')
        .map(([id]) => id)
    : []

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (isAwaiting || isDone || isError) {
      handleReply(input)
    } else {
      handleStart()
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> Agent Team
          </h1>
          <p className="text-cyber-400 mt-1 flex items-center gap-2">
            <Users className="w-4 h-4 text-neon-cyan" />
            Collaborative AI agents that work your request together — live.
          </p>
        </div>
        {session && (
          <button
            onClick={handleReset}
            className="btn-cyber-secondary px-4 py-2 flex items-center gap-2 text-sm"
          >
            <RefreshCw className="w-4 h-4" />
            New Session
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="card-cyber bg-red-500/5 border border-red-500/30 p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Agent status grid */}
      {session && (
        <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-10 gap-2">
          {roster.map((agent) => {
            const st = session.statuses?.[agent.id]
            const status = st?.status ?? 'idle'
            const isActive = status === 'working'
            const isDoneSt = status === 'done'
            return (
              <div
                key={agent.id}
                className={`card-cyber p-2 text-center transition-all duration-300 ${
                  isActive
                    ? 'border-neon-magenta/60 bg-neon-magenta/5 shadow-[0_0_16px_rgba(255,0,255,0.15)] animate-pulse'
                    : isDoneSt
                    ? 'border-neon-green/30 bg-neon-green/5'
                    : 'border-cyber-700/40 bg-cyber-800/30'
                }`}
              >
                <div className="text-lg mb-0.5">{AGENT_ICONS[agent.id] ?? '🤖'}</div>
                <div className="text-[10px] font-mono font-medium text-cyber-200 truncate">
                  {agent.name.split(' ')[0]}
                </div>
                {isActive && (
                  <div className="mt-1 flex justify-center">
                    <Loader2 className="w-3 h-3 text-neon-magenta animate-spin" />
                  </div>
                )}
                {isDoneSt && st?.turns ? (
                  <div className="mt-1 text-[9px] font-mono text-neon-green">
                    {st.turns}x
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      )}

      {/* Verdict banner */}
      {session && verdict !== 'review' && (
        <div
          className={`card-cyber ${verdictStyle.bg} ${verdictStyle.border} p-4 flex items-start gap-3`}
        >
          <div className={`mt-0.5 ${verdictStyle.text}`}>{verdictStyle.icon}</div>
          <div className="flex-1 min-w-0">
            <div className={`text-sm font-bold font-mono uppercase ${verdictStyle.text}`}>
              VERDICT: {verdict}
            </div>
            {session.verdict.summary && (
              <p className="text-cyber-300 text-sm mt-1 leading-relaxed">
                {session.verdict.summary}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Transcript */}
      {session && (
        <div className="card-cyber border-cyber-700/40 bg-cyber-900/60">
          <div className="px-4 py-3 border-b border-cyber-700/40 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-cyber-300 font-medium">
              <MessageSquare className="w-4 h-4 text-neon-cyan" />
              Transcript
              {isRunning && (
                <span className="badge-cyber bg-neon-magenta/10 text-neon-magenta text-[10px] animate-pulse ml-2">
                  {activeAgents.length} working
                </span>
              )}
              {isAwaiting && (
                <span className="badge-cyber bg-neon-amber/10 text-neon-amber text-[10px] ml-2">
                  awaiting you
                </span>
              )}
              {isDone && (
                <span className="badge-cyber bg-neon-green/10 text-neon-green text-[10px] ml-2">
                  complete
                </span>
              )}
            </div>
            {isRunning && (
              <button
                onClick={handleStop}
                className="text-[10px] font-mono text-red-400 hover:text-red-300 flex items-center gap-1 cursor-pointer"
              >
                <Square className="w-3 h-3" /> stop
              </button>
            )}
          </div>
          <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto" role="log" aria-live="polite">
            {session.transcript.length === 0 && (
              <p className="text-cyber-500 text-sm text-center py-8">Waiting for agents to start...</p>
            )}
            {session.transcript.map((entry) => (
              <TranscriptBubble key={entry.id} entry={entry} />
            ))}
            <div ref={transcriptEnd} />
          </div>
        </div>
      )}

      {/* Input area */}
      <form onSubmit={handleSubmit} className="card-cyber border-cyber-700/40 bg-cyber-800/30 p-4">
        <div className="flex items-center gap-3">
          {!session && <Users className="w-5 h-5 text-neon-magenta shrink-0" />}
          {session && !isRunning && (
            <User className="w-5 h-5 text-neon-cyan shrink-0" />
          )}
          {isRunning && (
            <Loader2 className="w-5 h-5 text-neon-magenta animate-spin shrink-0" />
          )}
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isRunning}
            placeholder={
              isRunning
                ? 'Team is working...'
                : isAwaiting || isDone || isError
                ? 'Type your reply...'
                : 'Describe what you want the team to build or fix...'
            }
            className="flex-1 input-cyber py-3 text-sm"
            autoFocus
          />
          {isRunning ? (
            <button
              type="button"
              onClick={handleStop}
              className="btn-cyber-secondary px-4 py-3 flex items-center gap-2 text-sm"
            >
              <Square className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="btn-cyber-primary px-4 py-3 flex items-center gap-2 text-sm disabled:opacity-50"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              {(isAwaiting || isDone || isError) ? 'Reply' : 'Start'}
            </button>
          )}
        </div>
        {!session && (
          <p className="text-cyber-500 text-[11px] font-mono mt-2">
            All {roster.length || 10} agents will discuss your request. CEO first, Q&A last. You can reply to steer the team.
          </p>
        )}
      </form>
    </div>
  )
}

// ── Transcript bubble sub-component ─────────────────────────────────────────

function TranscriptBubble({ entry }: { entry: TranscriptEntry }) {
  const [expanded, setExpanded] = useState(true)
  const isUser = entry.kind === 'user'
  const isSystem = entry.kind === 'system'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm shrink-0 ${
          isUser
            ? 'bg-neon-cyan/10 text-neon-cyan'
            : isSystem
            ? 'bg-cyber-700/50 text-cyber-400'
            : 'bg-neon-magenta/10 text-neon-magenta'
        }`}
      >
        {isUser ? '👤' : isSystem ? '📢' : AGENT_ICONS[entry.agent_id] ?? '🤖'}
      </div>

      {/* Content */}
      <div
        className={`flex-1 min-w-0 ${
          isUser ? 'text-right' : ''
        }`}
      >
        <div className="flex items-center gap-2 mb-1">
          {!isUser && (
            <span className="text-[11px] font-mono font-medium text-cyber-300">
              {entry.name}
            </span>
          )}
          {isUser && (
            <span className="text-[11px] font-mono font-medium text-neon-cyan">You</span>
          )}
          {entry.synth && (
            <span className="badge-cyber bg-cyber-700 text-cyber-500 text-[9px]">
              template
            </span>
          )}
          {isSystem && (
            <span className="text-[10px] text-cyber-500 font-mono">
              {new Date(entry.at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
        <div
          className={`rounded-xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? 'bg-neon-cyan/10 text-cyber-100 border border-neon-cyan/20'
              : isSystem
              ? 'bg-cyber-800/40 text-cyber-400 border border-cyber-700/30 text-center'
              : 'bg-cyber-800/60 text-cyber-200 border border-cyber-700/40'
          }`}
        >
          {expanded || entry.content.length < 500
            ? entry.content
            : entry.content.slice(0, 500) + '...'}
          {entry.content.length >= 500 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="block mt-2 text-[10px] text-neon-magenta hover:text-neon-magenta/80 font-mono cursor-pointer"
            >
              {expanded ? 'show less' : 'show full'}
            </button>
          )}
        </div>
        {!isUser && !isSystem && entry.mentions.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1 justify-start">
            {entry.mentions.map((m) => (
              <span key={m} className="text-[9px] font-mono text-neon-magenta/70">
                @{m}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}