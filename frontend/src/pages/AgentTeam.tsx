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
  MessageSquare,
  Sparkles,
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

const PHASE_LABELS: Record<string, string> = {
  orchestrating: 'Orchestrating the team',
  planning: 'Agents are planning',
  executing: 'Agents are working',
  reviewing: 'Running security review',
  collecting: 'Collecting feedback',
  asking: 'Awaiting your input',
  complete: 'Session complete',
  error: 'Session errored',
}

const SUGGESTIONS = [
  'Suggest security improvements for my backend',
  'Review the auth flow and API design',
  'Plan a refactor of the frontend state handling',
  'Audit the LLM routing configuration',
]

const VERDICT_STYLES: Record<string, { bg: string; border: string; text: string; icon: React.ReactNode }> = {
  safe: {
    bg: 'bg-neon-green/5',
    border: 'border-neon-green/30',
    text: 'text-neon-green',
    icon: <ShieldCheck className="w-4 h-4" />,
  },
  risk: {
    bg: 'bg-neon-amber/5',
    border: 'border-neon-amber/30',
    text: 'text-neon-amber',
    icon: <ShieldAlert className="w-4 h-4" />,
  },
  break: {
    bg: 'bg-red-500/5',
    border: 'border-red-500/30',
    text: 'text-red-400',
    icon: <AlertOctagon className="w-4 h-4" />,
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
  }, [session?.transcript.length, session?.status, session?.verdict?.level])

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
  const workingNames = roster
    .filter((a) => activeAgents.includes(a.id))
    .map((a) => a.name.split(' ')[0])
  const phaseLabel = PHASE_LABELS[session?.phase ?? ''] ?? (session?.phase || 'Team ready')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (isAwaiting || isDone || isError) {
      handleReply(input)
    } else {
      handleStart()
    }
  }

  const agentStatus = (id: string): AgentStatus['status'] => session?.statuses?.[id]?.status ?? 'idle'

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col gap-4 h-[calc(100dvh-13rem)] min-h-[24rem] md:h-[calc(100dvh-11rem)]">
      {/* Page header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 shrink-0 shadow-[0_0_20px_rgba(255,0,255,0.25)]">
            {isRunning ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : isDone ? (
              <ShieldCheck className="w-5 h-5" />
            ) : (
              <Users className="w-5 h-5" />
            )}
          </div>
          <div className="min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold font-display text-white truncate">
              Agent Team
            </h1>
            <p className="text-xs text-cyber-400 truncate">
              Collaborative AI agents that work your request together — live.
            </p>
          </div>
        </div>
        {session && (
          <button
            onClick={handleReset}
            className="btn-cyber-secondary px-3 py-2 flex items-center gap-2 text-sm shrink-0"
          >
            <RefreshCw className="w-4 h-4" />
            <span className="hidden sm:inline">New Session</span>
          </button>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="card-cyber bg-red-500/5 border border-red-500/30 p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Chat window */}
      <div className="card-cyber-glow border-cyber-700/40 flex flex-col overflow-hidden flex-1 min-h-0">
        {/* Chat header bar */}
        <div className="px-4 py-2.5 border-b border-cyber-700/40 flex items-center justify-between gap-3 bg-cyber-900/60">
          <div className="flex items-center gap-2 text-xs text-cyber-300 min-w-0">
            <MessageSquare className="w-4 h-4 text-neon-cyan shrink-0" />
            <span className="font-medium font-mono truncate">{phaseLabel}</span>
            {isRunning && (
              <span className="w-2 h-2 rounded-full bg-neon-magenta animate-pulse shrink-0" />
            )}
            {isAwaiting && (
              <span className="w-2 h-2 rounded-full bg-neon-amber animate-pulse shrink-0" />
            )}
            {isDone && <span className="w-2 h-2 rounded-full bg-neon-green shrink-0" />}
          </div>
          {/* Agent presence strip */}
          <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide">
            {roster.map((agent) => {
              const st = agentStatus(agent.id)
              return (
                <span
                  key={agent.id}
                  title={`${agent.name} — ${st}`}
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0 border transition-colors ${
                    st === 'working'
                      ? 'border-neon-magenta bg-neon-magenta/15 animate-pulse'
                      : st === 'done'
                      ? 'border-neon-green/60 bg-neon-green/10'
                      : 'border-cyber-700 bg-cyber-800/50'
                  }`}
                >
                  {AGENT_ICONS[agent.id] ?? '🤖'}
                </span>
              )
            })}
          </div>
        </div>

        {/* Messages area */}
        <div
          className="flex-1 min-h-0 overflow-y-auto bg-cyber-800/20 p-4 sm:p-6 space-y-5"
          role="log"
          aria-live="polite"
        >
          {!session ? (
            <EmptyChat roster={roster} onPick={setInput} />
          ) : (
            <>
              {session.transcript.length === 0 && (
                <p className="text-cyber-500 text-sm text-center py-10">
                  Waiting for agents to start...
                </p>
              )}
              {session.transcript.map((entry) => (
                <ChatBubble key={entry.id} entry={entry} />
              ))}
              {isError && session.error && (
                <div className="flex justify-center">
                  <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 text-[11px] font-mono">
                    <AlertOctagon className="w-3.5 h-3.5" />
                    {session.error}
                  </div>
                </div>
              )}
              {verdict !== 'review' && (
                <div className="flex justify-center">
                  <div
                    className={`inline-flex items-start gap-2 max-w-[95%] px-4 py-2.5 rounded-2xl border ${verdictStyle.bg} ${verdictStyle.border}`}
                  >
                    <div className={`mt-0.5 ${verdictStyle.text}`}>{verdictStyle.icon}</div>
                    <div className="text-left min-w-0">
                      <div className={`text-xs font-bold font-mono uppercase ${verdictStyle.text}`}>
                        Verdict: {verdict}
                      </div>
                      {session.verdict.summary && (
                        <p className="text-cyber-300 text-xs mt-1 leading-relaxed">
                          {session.verdict.summary}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
              {isRunning && <TypingIndicator names={workingNames} />}
              <div ref={transcriptEnd} />
            </>
          )}
        </div>

        {/* Composer / stop row */}
        {isRunning ? (
          <div className="p-3 border-t border-cyber-700/40 bg-cyber-900/60 flex justify-center">
            <button
              type="button"
              onClick={handleStop}
              className="btn-cyber-secondary px-5 py-2.5 rounded-full text-sm flex items-center gap-2 text-red-300 border-red-500/40 hover:bg-red-500/10"
            >
              <Square className="w-4 h-4" />
              Stop generating
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-3 sm:p-4 border-t border-cyber-700/40 bg-cyber-900/60">
            <div className="flex items-end gap-2">
              <label htmlFor="agent-input" className="sr-only">
                {isAwaiting || isDone || isError ? 'Reply to the team' : 'Describe a task'}
              </label>
              <input
                id="agent-input"
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  isAwaiting || isDone || isError
                    ? 'Type your reply...'
                    : 'Describe what you want the team to build or fix...'
                }
                className="input-cyber flex-1 min-w-0"
                autoFocus
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                aria-label={isAwaiting || isDone || isError ? 'Send reply' : 'Start session'}
                className="w-12 h-12 rounded-full shrink-0 bg-gradient-to-tr from-neon-magenta to-neon-cyan text-cyber-900 flex items-center justify-center shadow-lg shadow-neon-magenta/20 hover:shadow-[0_0_20px_rgba(255,0,255,0.5)] transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </button>
            </div>
            {!session && (
              <p className="text-cyber-500 text-[11px] font-mono mt-2">
                All {roster.length || 10} agents will discuss your request — CEO first, Q&A last.
                You can reply to steer the team.
              </p>
            )}
          </form>
        )}
      </div>
    </div>
  )
}

// ── Empty chat state ────────────────────────────────────────────────────────

function EmptyChat({ roster, onPick }: { roster: Agent[]; onPick: (text: string) => void }) {
  return (
    <div className="h-full flex flex-col items-center justify-center gap-6 px-4 py-10 text-center">
      <div className="relative">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 shadow-[0_0_40px_rgba(255,0,255,0.3)]">
          <Sparkles className="w-8 h-8" />
        </div>
        <div className="absolute -right-2 -bottom-2 w-7 h-7 rounded-full bg-cyber-800 border border-neon-cyan/40 flex items-center justify-center text-sm">
          {roster.length ? AGENT_ICONS[roster[0].id] ?? '🤖' : '🤖'}
        </div>
      </div>
      <div>
        <h2 className="text-lg font-bold font-display text-white">Brief your agent team</h2>
        <p className="text-cyber-400 text-sm mt-1 max-w-md leading-relaxed">
          {roster.length || 10} specialized agents will discuss your request together, then report
          back with a verdict.
        </p>
      </div>
      <div className="grid gap-2 w-full max-w-lg">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="text-left card-cyber px-4 py-2.5 text-sm text-cyber-200 hover:text-white hover:border-neon-magenta/40 transition-colors cursor-pointer"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Typing indicator ────────────────────────────────────────────────────────

function TypingIndicator({ names }: { names: string[] }) {
  const label = names.length
    ? `${names.join(', ')} ${names.length === 1 ? 'is' : 'are'} working`
    : 'Agents are working'
  return (
    <div className="flex items-end gap-2.5">
      <div className="w-9 h-9 rounded-full bg-gradient-to-br from-neon-magenta/25 to-neon-cyan/15 border border-neon-magenta/30 flex items-center justify-center text-base shrink-0">
        🤖
      </div>
      <div className="bg-cyber-800/60 border border-cyber-700/40 rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-1.5">
        <span className="typing-dot bg-neon-magenta" />
        <span className="typing-dot bg-neon-magenta [animation-delay:150ms]" />
        <span className="typing-dot bg-neon-magenta [animation-delay:300ms]" />
      </div>
      <span className="text-[10px] font-mono text-cyber-500 mb-1.5">{label}</span>
    </div>
  )
}

// ── Chat bubble sub-component ───────────────────────────────────────────────

function ChatBubble({ entry }: { entry: TranscriptEntry }) {
  const [expanded, setExpanded] = useState(true)
  const isUser = entry.kind === 'user'
  const isSystem = entry.kind === 'system'
  const time = new Date(entry.at * 1000).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  })
  const body = expanded || entry.content.length < 500
    ? entry.content
    : entry.content.slice(0, 500) + '...'

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyber-800/40 border border-cyber-700/30 text-cyber-500 text-[11px] italic max-w-[95%]">
          <span className="truncate">{entry.content}</span>
          <span className="text-cyber-600 font-mono not-italic">{time}</span>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex gap-2.5 items-start ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`w-9 h-9 rounded-full flex items-center justify-center text-base shrink-0 border ${
          isUser
            ? 'bg-neon-cyan/15 text-neon-cyan border-neon-cyan/30'
            : 'bg-gradient-to-br from-neon-magenta/25 to-neon-cyan/15 text-neon-magenta border-neon-magenta/30'
        }`}
      >
        {isUser ? '👤' : AGENT_ICONS[entry.agent_id] ?? '🤖'}
      </div>

      {/* Content */}
      <div className={`max-w-[85%] sm:max-w-[75%] min-w-0 ${isUser ? 'text-right' : ''}`}>
        {!isUser && (
          <div className="flex items-baseline gap-2 mb-1 pl-1">
            <span className="text-xs font-semibold font-mono text-cyber-100">{entry.name}</span>
            <span className="text-[10px] font-mono text-cyber-500 truncate">{entry.title}</span>
          </div>
        )}
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words ${
            isUser
              ? 'bg-gradient-to-tr from-neon-cyan/25 to-neon-cyan/5 text-cyber-50 border border-neon-cyan/25 rounded-br-md'
              : 'bg-cyber-800/60 text-cyber-200 border border-cyber-700/40 rounded-tl-md'
          }`}
        >
          {body}
          {entry.content.length >= 500 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="block mt-2 text-[10px] text-neon-magenta hover:text-neon-magenta/80 font-mono cursor-pointer"
            >
              {expanded ? 'show less' : 'show full'}
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 mt-1 px-1 justify-start">
          {!isUser && entry.mentions.length > 0 && (
            <span className="flex flex-wrap gap-1">
              {entry.mentions.map((m) => (
                <span key={m} className="text-[9px] font-mono text-neon-magenta/70">
                  @{m}
                </span>
              ))}
            </span>
          )}
          <span className="text-[10px] font-mono text-cyber-500">{time}</span>
          {entry.synth && (
            <span className="badge-cyber bg-cyber-700 text-cyber-500 text-[9px] px-1.5">template</span>
          )}
        </div>
      </div>
    </div>
  )
}