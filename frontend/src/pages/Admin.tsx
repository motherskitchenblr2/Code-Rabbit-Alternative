import { useState, useEffect, useRef, useCallback, FormEvent } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  ShieldCheck,
  Server,
  Brain,
  KeyRound,
  Plus,
  Trash2,
  RefreshCw,
  TestTube2,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Bot,
  GitFork,
  Gitlab,
  Boxes,
  Cloud,
  Zap,
  Cpu,
  Triangle,
  Network,
  CloudCog,
  Kanban,
  Activity,
  Database,
  MemoryStick,
  Container,
  Gauge,
  Shield,
} from 'lucide-react'

// ── API helpers ─────────────────────────────────────────────────────────────

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

interface Provider {
  id: string
  name: string
  base_url: string
  multimodal: boolean
  enabled: boolean
  model: string
  api_key_set: boolean
  api_key_tail: string
  created_at?: number
  updated_at?: number
}

interface McpServer {
  id: string
  name: string
  transport: string
  command: string
  args: string[]
  url: string
  env_set: boolean
  enabled: boolean
  created_at?: number
  updated_at?: number
}

interface TokenRecord {
  id: string
  name: string
  platform: string
  scopes: string[]
  enabled: boolean
  token_set: boolean
  token_tail: string
  created_at?: number
  updated_at?: number
}

interface Overview {
  ai_providers: { total: number; enabled: number; configured: number }
  mcp_servers: { total: number; enabled: number }
  access_tokens: { total: number; enabled: number; configured: number }
  auth_enabled: boolean
}

interface ProbeResult {
  ok: boolean
  status?: number | null
  detail: string
}

const KNOWN_PROVIDERS = [
  { id: 'openai', name: 'OpenAI', multimodal: true, url: 'https://api.openai.com/v1', icon: Bot },
  { id: 'nvidia', name: 'NVIDIA', multimodal: false, url: 'https://integrate.api.nvidia.com/v1', icon: Cpu },
  { id: 'anthropic', name: 'Anthropic', multimodal: true, url: 'https://api.anthropic.com/v1', icon: Brain },
  { id: 'google', name: 'Google Gemini', multimodal: true, url: 'https://generativelanguage.googleapis.com/v1beta', icon: Zap },
  { id: 'groq', name: 'Groq', multimodal: false, url: 'https://api.groq.com/openai/v1', icon: Zap },
  { id: 'together', name: 'Together AI', multimodal: true, url: 'https://api.together.xyz/v1', icon: Cpu },
  { id: 'huggingface', name: 'Hugging Face', multimodal: true, url: 'https://api-inference.huggingface.co', icon: Bot },
  { id: 'openrouter', name: 'OpenRouter', multimodal: true, url: 'https://openrouter.ai/api/v1', icon: Cpu },
  { id: 'mistral', name: 'Mistral AI', multimodal: false, url: 'https://api.mistral.ai/v1', icon: Brain },
  { id: 'deepseek', name: 'DeepSeek', multimodal: false, url: 'https://api.deepseek.com', icon: Zap },
  { id: 'perplexity', name: 'Perplexity', multimodal: false, url: 'https://api.perplexity.ai', icon: Zap },
  { id: 'ollama', name: 'Ollama (Local)', multimodal: true, url: 'http://localhost:11434', icon: Server },
]

const PLATFORM_ICONS: Record<string, any> = {
  github: GitFork,
  gitlab: Gitlab,
  bitbucket: Boxes,
  azure_devops: Cloud,
  vercel: Triangle,
  netlify: Network,
  cloudflare: CloudCog,
  huggingface: Bot,
  codeberg: GitFork,
  jira: Kanban,
  linear: Zap,
  datadog: Activity,
  sentry: Shield,
  postgresql: Database,
  redis: MemoryStick,
  qdrant: Container,
  prometheus: Gauge,
}

const TRANSPORTS = [
  { id: 'stdio', label: 'Stdio (local command)' },
  { id: 'http', label: 'HTTP / SSE (remote URL)' },
]

// ── Small UI primitives ─────────────────────────────────────────────────────

function Stat({ label, value, sub, accent }: { label: string; value: number; sub?: string; accent?: string }) {
  return (
    <div className="card-cyber p-4">
      <p className="text-xs text-cyber-400 font-mono uppercase tracking-wider">{label}</p>
      <p className={`text-3xl font-bold font-display mt-1 ${accent || 'text-white'}`}>{value}</p>
      {sub && <p className="text-xs text-cyber-400 mt-1">{sub}</p>}
    </div>
  )
}

function SectionCard({ title, icon: Icon, desc, children, onAdd, addLabel }: {
  title: string
  icon: any
  desc: string
  children: React.ReactNode
  onAdd?: () => void
  addLabel?: string
}) {
  return (
    <div className="card-cyber-glow p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
            <Icon className="w-5 h-5 text-neon-cyan" />
            {title}
          </h3>
          <p className="text-xs text-cyber-400 mt-1">{desc}</p>
        </div>
        {onAdd && (
          <button className="btn-cyber-cyan text-sm" onClick={onAdd}>
            <Plus className="w-4 h-4 mr-2" />
            {addLabel || 'Add'}
          </button>
        )}
      </div>
      {children}
    </div>
  )
}

function TestButton({ onTest, loading }: { onTest: () => void; loading: boolean }) {
  return (
    <button
      className="btn-cyber-ghost text-sm"
      onClick={onTest}
      disabled={loading}
      aria-label="Test connection"
    >
      {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <TestTube2 className="w-4 h-4 mr-2" />}
      Test
    </button>
  )
}

function ProbeBanner({ result }: { result: ProbeResult | null }) {
  if (!result) return null
  const ok = result.ok
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm mt-3 ${
      ok ? 'bg-neon-green/10 border border-neon-green/30 text-neon-green' : 'bg-red-500/10 border border-red-500/30 text-red-300'
    }`}>
      {ok ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" /> : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
      <span className="font-mono text-xs">{result.detail}</span>
    </div>
  )
}

const inputCls = 'input-cyber w-full'
const inputRow = 'flex flex-col gap-1'

// ── Main page ───────────────────────────────────────────────────────────────

type Section = 'overview' | 'providers' | 'mcp' | 'tokens' | 'router'

export default function Admin() {
  const { user } = useAuth()
  const [section, setSection] = useState<Section>('overview')
  const [isAdmin, setIsAdmin] = useState(false)
  const [overview, setOverview] = useState<Overview | null>(null)
  const [providers, setProviders] = useState<Provider[]>([])
  const [servers, setServers] = useState<McpServer[]>([])
  const [tokens, setTokens] = useState<TokenRecord[]>([])
  const [platforms, setPlatforms] = useState<Record<string, { name: string; hint: string }>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    setIsAdmin(user?.role === 'admin')
  }, [user])

  const loadAll = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [ov, pr, sr, tk] = await Promise.all([
        api<Overview>('/api/v1/admin/overview'),
        api<{ providers: Provider[] }>('/api/v1/admin/providers'),
        api<{ servers: McpServer[] }>('/api/v1/admin/mcp/servers'),
        api<{ tokens: TokenRecord[]; platforms: Record<string, { name: string; hint: string }> }>('/api/v1/admin/tokens'),
      ])
      setOverview(ov)
      setProviders(pr.providers)
      setServers(sr.servers)
      setTokens(tk.tokens)
      setPlatforms(tk.platforms)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load admin data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isAdmin) loadAll()
  }, [isAdmin, loadAll, refreshKey])

  const sections: { id: Section; label: string; icon: any }[] = [
    { id: 'overview', label: 'Overview', icon: ShieldCheck },
    { id: 'providers', label: 'AI APIs', icon: Brain },
    { id: 'router', label: 'AI Router', icon: Zap },
    { id: 'mcp', label: 'MCP Servers', icon: Server },
    { id: 'tokens', label: 'Access Tokens', icon: KeyRound },
  ]

  if (!isAdmin) {
    return (
      <div className="card-cyber p-8 text-center">
        <ShieldCheck className="w-12 h-12 text-neon-magenta mx-auto mb-4" />
        <h1 className="text-2xl font-bold font-display text-white">Restricted Area</h1>
        <p className="text-cyber-400 mt-2">The Admin Panel is only available to accounts with the <span className="text-neon-magenta font-mono">admin</span> role.</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <ShieldCheck className="text-neon-magenta w-7 h-7" />
            Admin Panel
          </h1>
          <p className="text-cyber-400 mt-1 flex items-center gap-2">
            <KeyRound className="w-4 h-4 text-neon-cyan" />
            Multi-platform integrations — AI providers, MCP servers, and access tokens.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn-cyber-ghost" onClick={() => setRefreshKey(k => k + 1)} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-3 text-red-300">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Section tabs */}
      <div className="flex flex-wrap gap-2">
        {sections.map((s) => {
          const Icon = s.icon
          return (
            <button
              key={s.id}
              onClick={() => setSection(s.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-all ${
                section === s.id
                  ? 'bg-neon-magenta/10 text-neon-magenta border-neon-magenta/40'
                  : 'bg-cyber-800/50 text-cyber-300 border-cyber-700/50 hover:border-neon-cyan/40 hover:text-neon-cyan'
              }`}
            >
              <Icon className="w-4 h-4" />
              {s.label}
            </button>
          )
        })}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="w-10 h-10 text-neon-cyan animate-spin" />
        </div>
      ) : (
        <>
          {section === 'overview' && overview && (
            <OverviewSection overview={overview} />
          )}
          {section === 'providers' && (
            <ProvidersSection providers={providers} onChanged={() => setRefreshKey(k => k + 1)} />
          )}
          {section === 'router' && (
            <RouterSection />
          )}
          {section === 'mcp' && (
            <McpSection servers={servers} onChanged={() => setRefreshKey(k => k + 1)} />
          )}
          {section === 'tokens' && (
            <TokensSection tokens={tokens} platforms={platforms} onChanged={() => setRefreshKey(k => k + 1)} />
          )}
        </>
      )}
    </div>
  )
}

// ── Overview ────────────────────────────────────────────────────────────────

function OverviewSection({ overview }: { overview: Overview }) {
  const statusItems = [
    { label: 'Auth Enforcement', ok: overview.auth_enabled, okText: 'Enabled', badText: 'Disabled' },
    { label: 'AI Providers', ok: overview.ai_providers.configured > 0, okText: `${overview.ai_providers.configured} configured`, badText: 'None configured' },
    { label: 'MCP Servers', ok: overview.mcp_servers.total > 0, okText: `${overview.mcp_servers.total} registered`, badText: 'None registered' },
    { label: 'Access Tokens', ok: overview.access_tokens.configured > 0, okText: `${overview.access_tokens.configured} stored`, badText: 'None stored' },
  ]
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="AI Providers" value={overview.ai_providers.total} sub={`${overview.ai_providers.enabled} enabled`} accent="text-neon-cyan" />
        <Stat label="MCP Servers" value={overview.mcp_servers.total} sub={`${overview.mcp_servers.enabled} enabled`} accent="text-neon-magenta" />
        <Stat label="Access Tokens" value={overview.access_tokens.total} sub={`${overview.access_tokens.enabled} enabled`} accent="text-neon-amber" />
        <Stat label="Security Posture" value={overview.auth_enabled ? 1 : 0} sub={overview.auth_enabled ? 'Auth enforced' : 'Auth OFF — review!'} accent={overview.auth_enabled ? 'text-neon-green' : 'text-red-400'} />
      </div>

      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-neon-magenta" />
          System Status
        </h3>
        <div className="space-y-3">
          {statusItems.map((item) => (
            <div key={item.label} className="flex items-center justify-between p-3 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <span className="text-sm text-cyber-200">{item.label}</span>
              <span className={`flex items-center gap-2 text-sm font-mono ${item.ok ? 'text-neon-green' : 'text-neon-amber'}`}>
                <span className={`w-2 h-2 rounded-full ${item.ok ? 'bg-neon-green' : 'bg-neon-amber'} animate-pulse`} />
                {item.ok ? item.okText : item.badText}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── AI Router (auto-rotation) ───────────────────────────────────────────────

interface RouterProvider {
  id: string
  name: string
  enabled: boolean
  configured: boolean
  multimodal: boolean
  healthy: boolean
  failures: number
  last_error: string | null
}

interface RouteCandidate {
  provider: string
  model: string
  status: 'prima' | 'fallback' | 'degraded'
}

interface RouterSnapshot {
  providers: RouterProvider[]
  routing: Record<string, { label: string; candidates: RouteCandidate[] }>
  catalog_providers: { id: string; name: string }[]
}

function RouterSection() {
  const [snap, setSnap] = useState<RouterSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const hasLoaded = useRef(false)

  useEffect(() => {
    let cancelled = false
    if (hasLoaded.current) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setErr(null)
    api<RouterSnapshot>('/api/v1/llm/status')
      .then((d) => {
        if (!cancelled) {
          hasLoaded.current = true
          setSnap(d)
        }
      })
      .catch((e) => { if (!cancelled) setErr(e instanceof Error ? e.message : 'Failed to load router status') })
      .finally(() => { if (!cancelled) { setLoading(false); setRefreshing(false) } })
    return () => { cancelled = true }
  }, [refreshKey])

  if (loading) {
    return (
      <div className="card-cyber-glow p-8 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-neon-cyan animate-spin" />
      </div>
    )
  }

  if (!snap) {
    return (
      <div className="card-cyber-glow p-6">
        <p className="text-red-400 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" /> {err || 'Router status unavailable'}
        </p>
      </div>
    )
  }

  const statusColor = (healthy: boolean, failures: number) => {
    if (!healthy) return 'bg-red-500/10 border-red-500/30 text-red-300'
    if (failures > 0) return 'bg-neon-amber/10 border-neon-amber/30 text-neon-amber'
    return 'bg-neon-green/10 border-neon-green/30 text-neon-green'
  }
  const routeColor = (s: string) =>
    s === 'prima' ? 'text-neon-green'
      : s === 'degraded' ? 'text-neon-amber'
      : 'text-cyber-400'

  return (
    <div className="space-y-6 card-cyber-glow p-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-neon-amber" />
            Auto-Rotation Router
          </h3>
          <p className="text-xs text-cyber-400 mt-1">
            Every request is routed to the strongest configured provider for its task, with automatic failover on error or rate-limit. Circuit breaker trips after 3 failures (60s cooldown).
          </p>
        </div>
        <button className="btn-cyber-ghost text-sm flex items-center shrink-0 whitespace-nowrap" onClick={() => setRefreshKey(k => k + 1)}>
          <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Providers */}
      <div>
        <p className="text-xs font-mono uppercase tracking-wider text-cyber-400 mb-3">Connected Providers</p>
        <div className="space-y-2">
          {snap.providers.map((p) => (
            <div key={p.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-cyber-800 flex items-center justify-center">
                  {(() => {
                    const Icon = KNOWN_PROVIDERS.find(k => k.id === p.id)?.icon || Cpu
                    return <Icon className="w-4 h-4 text-neon-cyan" />
                  })()}
                </div>
                <div>
                  <p className="text-sm font-medium text-white flex items-center gap-2">
                    {p.name}
                    {p.multimodal && <span className="badge-cyber text-xs text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30">multimodal</span>}
                  </p>
                  <p className="text-xs text-cyber-400 font-mono">{p.id} · {p.configured ? 'key configured' : 'no key'}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`badge-cyber text-xs ${statusColor(p.healthy, p.failures)}`}>
                  {p.healthy ? (p.failures > 0 ? 'degraded' : 'healthy') : 'cooling down'}
                </span>
                {!p.enabled && <span className="badge-cyber text-xs bg-cyber-700 text-cyber-400 border-cyber-600">disabled</span>}
              </div>
            </div>
          ))}
          {snap.providers.length === 0 && (
            <p className="text-center text-cyber-500 font-mono py-4">No providers configured yet — add an API key under the AI APIs tab.</p>
          )}
        </div>
      </div>

      {/* Routing table */}
      <div>
        <p className="text-xs font-mono uppercase tracking-wider text-cyber-400 mb-3">Task Routing (top candidate is served first)</p>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {Object.entries(snap.routing).map(([task, info]) => (
            <div key={task} className="p-3 rounded-lg bg-cyber-900/40 border border-cyber-700/50">
              <p className="text-xs font-mono text-neon-magenta mb-2">{info.label}</p>
              <div className="flex flex-wrap gap-2">
                {info.candidates.map((c) => (
                  <span key={c.provider} className={`badge-cyber text-xs ${routeColor(c.status)}`}>
                    {c.provider} → <span className="font-mono">{c.model}</span>
                    {c.status === 'prima' && <span className="ml-1">★</span>}
                  </span>
                ))}
                {info.candidates.length === 0 && (
                  <span className="badge-cyber text-xs bg-cyber-700 text-cyber-400 border-cyber-600">no provider</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── AI Providers ────────────────────────────────────────────────────────────

function ProvidersSection({ providers, onChanged }: { providers: Provider[]; onChanged: () => void }) {
  const [editing, setEditing] = useState<Provider | null>(null)
  const [creating, setCreating] = useState(false)

  return (
    <SectionCard
      title="AI API Providers"
      icon={Brain}
      desc="Multimodal LLM providers — keys are stored server-side and masked."
      onAdd={() => { setCreating(true); setEditing(null) }}
    >
      {creating && <ProviderForm provider={null} onDone={onChanged} onCancel={() => setCreating(false)} />}

      <div className="space-y-3">
        {providers.map((p) => (
          <div key={p.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-cyber-800 flex items-center justify-center">
                {(() => {
                  const Icon = KNOWN_PROVIDERS.find(k => k.id === p.id)?.icon || Cpu
                  return <Icon className="w-6 h-6 text-neon-cyan" />
                })()}
              </div>
              <div>
                <p className="font-medium text-white flex items-center gap-2">
                  {p.name}
                  {p.multimodal && (
                    <span className="badge-cyber text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30 text-xs">multimodal</span>
                  )}
                </p>
                <p className="text-xs text-cyber-400 font-mono truncate max-w-[260px]">{p.base_url}</p>
                {p.model && <p className="text-xs text-neon-amber font-mono mt-0.5">model: {p.model}</p>}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className={`badge-cyber ${p.api_key_set ? 'bg-neon-green/20 text-neon-green border-neon-green/30' : 'bg-cyber-700 text-cyber-400 border-cyber-600'}`}>
                {p.api_key_set ? `key ${p.api_key_tail}` : 'no key'}
              </span>
              <span className={`badge-cyber ${p.enabled ? 'bg-neon-green/20 text-neon-green border-neon-green/30' : 'bg-cyber-700 text-cyber-400 border-cyber-600'}`}>
                {p.enabled ? 'enabled' : 'disabled'}
              </span>
              <button className="btn-cyber-ghost text-sm" onClick={() => { setEditing(p); setCreating(false) }}>
                Configure
              </button>
            </div>
          </div>
        ))}
      </div>

      {providers.length === 0 && !creating && (
        <p className="text-center text-cyber-500 font-mono py-8">No AI providers configured yet.</p>
      )}

      {editing && <ProviderForm provider={editing} onDone={onChanged} onCancel={() => setEditing(null)} />}
    </SectionCard>
  )
}

function ProviderForm({ provider, onDone, onCancel }: { provider: Provider | null; onDone: () => void; onCancel: () => void }) {
  const isNew = !provider
  const defaults = provider
    ? { id: provider.id, name: provider.name, base_url: provider.base_url, model: provider.model || '' }
    : { id: '', name: '', base_url: '', model: '' }
  const [form, setForm] = useState(defaults)
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [probe, setProbe] = useState<ProbeResult | null>(null)
  const [testing, setTesting] = useState(false)

  const save = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setErr(null)
    try {
      const res = await api<{ probe?: ProbeResult }>('/api/v1/admin/providers', {
        method: 'POST',
        body: JSON.stringify({ ...form, api_key: apiKey }),
      })
      if (res.probe) setProbe(res.probe)
      onDone()
      onCancel()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const test = async () => {
    setTesting(true)
    setProbe(null)
    try {
      if (isNew) await saveNoClose()
      const res = await api<{ result: ProbeResult }>(`/api/v1/admin/providers/${form.id}/test`, { method: 'POST', body: '{}' })
      setProbe(res.result)
    } catch (e) {
      setProbe({ ok: false, detail: e instanceof Error ? e.message : 'Test failed' })
    } finally {
      setTesting(false)
    }
  }

  const saveNoClose = async () => {
    await api('/api/v1/admin/providers', {
      method: 'POST',
      body: JSON.stringify({ ...form, api_key: apiKey }),
    })
  }

  const pickKnown = (pid: string) => {
    const k = KNOWN_PROVIDERS.find(x => x.id === pid)
    if (k) setForm(f => ({ ...f, id: k.id, name: k.name, base_url: k.url }))
  }

  return (
    <form onSubmit={save} className="mb-6 p-5 rounded-lg bg-cyber-900/60 border border-neon-cyan/30 space-y-4 animate-in slide-in-from-top-2">
      <div className="flex items-center justify-between">
        <h4 className="font-display font-bold text-white">{isNew ? 'Add AI Provider' : `Configure ${provider!.name}`}</h4>
        <button type="button" onClick={onCancel} className="text-cyber-400 hover:text-white text-sm">Close</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className={inputRow}>
          <label className="label-cyber">Provider ID</label>
          {isNew && (
            <select className={inputCls} value={form.id} onChange={(e) => pickKnown(e.target.value)}>
              <option value="">— select known provider —</option>
              {KNOWN_PROVIDERS.map(k => <option key={k.id} value={k.id}>{k.name}</option>)}
            </select>
          )}
          <input
            className={inputCls}
            value={form.id}
            disabled={!isNew}
            placeholder="e.g. openai"
            onChange={(e) => setForm(f => ({ ...f, id: e.target.value }))}
          />
        </div>
        <div className={inputRow}>
          <label className="label-cyber">Display Name</label>
          <input className={inputCls} value={form.name} placeholder="OpenAI" onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} />
        </div>
        <div className={inputRow}>
          <label className="label-cyber">Base URL</label>
          <input className={inputCls} value={form.base_url} placeholder="https://api.openai.com/v1" onChange={(e) => setForm(f => ({ ...f, base_url: e.target.value }))} />
        </div>
        <div className={inputRow}>
          <label className="label-cyber">Default Model</label>
          <input className={inputCls} value={form.model} placeholder="gpt-4o" onChange={(e) => setForm(f => ({ ...f, model: e.target.value }))} />
        </div>
        <div className={`${inputRow} md:col-span-2`}>
          <label className="label-cyber">API Key {provider?.api_key_set && <span className="text-cyber-400 text-xs">(leave blank to keep {provider.api_key_tail})</span>}</label>
          <input
            className={inputCls}
            type="password"
            value={apiKey}
            autoComplete="off"
            placeholder={provider?.api_key_set ? '••••••••••••' : 'sk-…'}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </div>
      </div>

      {err && <p className="text-xs text-red-400">{err}</p>}
      <ProbeBanner result={probe} />

      <div className="flex flex-wrap gap-3">
        <button type="submit" className="btn-cyber-magenta" disabled={saving}>
          {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
          {isNew ? 'Add Provider' : 'Save Changes'}
        </button>
        <TestButton onTest={test} loading={testing} />
        {!isNew && (
          <DeleteAction
            label="Remove Provider"
            onDelete={async () => {
              await api(`/api/v1/admin/providers/${provider!.id}`, { method: 'DELETE' })
              onDone(); onCancel()
            }}
          />
        )}
      </div>
    </form>
  )
}

// ── MCP Servers ─────────────────────────────────────────────────────────────

function McpSection({ servers, onChanged }: { servers: McpServer[]; onChanged: () => void }) {
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<McpServer | null>(null)

  return (
    <SectionCard
      title="MCP Servers"
      icon={Server}
      desc="Model Context Protocol servers — stdio commands or remote HTTP/SSE endpoints."
      onAdd={() => { setCreating(true); setEditing(null) }}
    >
      {creating && <McpForm server={null} onDone={onChanged} onCancel={() => setCreating(false)} />}

      <div className="space-y-3">
        {servers.map((s) => (
          <div key={s.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-cyber-800 flex items-center justify-center">
                <Server className="w-6 h-6 text-neon-magenta" />
              </div>
              <div>
                <p className="font-medium text-white">{s.name}</p>
                <p className="text-xs text-cyber-400 font-mono truncate max-w-[280px]">
                  {s.transport === 'stdio' ? s.command : s.url}
                </p>
                <span className="badge-cyber bg-cyber-700 text-cyber-300 mt-1 text-xs">{s.transport}</span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className={`badge-cyber ${s.enabled ? 'bg-neon-green/20 text-neon-green border-neon-green/30' : 'bg-cyber-700 text-cyber-400 border-cyber-600'}`}>
                {s.enabled ? 'enabled' : 'disabled'}
              </span>
              <button className="btn-cyber-ghost text-sm" onClick={() => { setEditing(s); setCreating(false) }}>
                Configure
              </button>
            </div>
          </div>
        ))}
      </div>

      {servers.length === 0 && !creating && (
        <p className="text-center text-cyber-500 font-mono py-8">No MCP servers registered yet.</p>
      )}

      {editing && <McpForm server={editing} onDone={onChanged} onCancel={() => setEditing(null)} />}
    </SectionCard>
  )
}

function McpForm({ server, onDone, onCancel }: { server: McpServer | null; onDone: () => void; onCancel: () => void }) {
  const isNew = !server
  const [form, setForm] = useState(
    server
      ? { name: server.name, transport: server.transport, command: server.command, url: server.url, env: '' }
      : { name: '', transport: 'stdio', command: '', url: '', env: '' }
  )
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [probe, setProbe] = useState<ProbeResult | null>(null)
  const [testing, setTesting] = useState(false)

  const save = async (e: FormEvent | null, close = true) => {
    if (e) e.preventDefault()
    setSaving(true)
    setErr(null)
    try {
      const env: Record<string, string> = {}
      form.env.split('\n').forEach(line => {
        const idx = line.indexOf('=')
        if (idx > 0) env[line.slice(0, idx).trim()] = line.slice(idx + 1).trim()
      })
      await api('/api/v1/admin/mcp/servers', {
        method: 'POST',
        body: JSON.stringify({ id: server?.id, ...form, env }),
      })
      onDone()
      if (close) onCancel()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const test = async () => {
    setTesting(true)
    setProbe(null)
    try {
      await save(null, false)
      const id = server?.id || form.name
      const res = await api<{ result: ProbeResult }>(`/api/v1/admin/mcp/servers/${id}/test`, { method: 'POST', body: '{}' })
      setProbe(res.result)
    } catch (e) {
      setProbe({ ok: false, detail: e instanceof Error ? e.message : 'Test failed' })
    } finally {
      setTesting(false)
    }
  }

  return (
    <form onSubmit={(e) => save(e, true)} className="mb-6 p-5 rounded-lg bg-cyber-900/60 border border-neon-cyan/30 space-y-4 animate-in slide-in-from-top-2">
      <div className="flex items-center justify-between">
        <h4 className="font-display font-bold text-white">{isNew ? 'Add MCP Server' : `Configure ${server!.name}`}</h4>
        <button type="button" onClick={onCancel} className="text-cyber-400 hover:text-white text-sm">Close</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className={inputRow}>
          <label className="label-cyber">Name</label>
          <input className={inputCls} value={form.name} placeholder="GitHub MCP" onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} />
        </div>
        <div className={inputRow}>
          <label className="label-cyber">Transport</label>
          <div className="flex gap-2">
            {TRANSPORTS.map(t => (
              <button
                key={t.id}
                type="button"
                onClick={() => setForm(f => ({ ...f, transport: t.id }))}
                className={`flex-1 px-3 py-2 rounded-lg border text-sm transition-all ${
                  form.transport === t.id
                    ? 'bg-neon-cyan/10 text-neon-cyan border-neon-cyan/40'
                    : 'bg-cyber-800 text-cyber-400 border-cyber-700/50'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {form.transport === 'stdio' ? (
          <div className={`${inputRow} md:col-span-2`}>
            <label className="label-cyber">Command</label>
            <input className={inputCls} value={form.command} placeholder="npx @modelcontextprotocol/server-github" onChange={(e) => setForm(f => ({ ...f, command: e.target.value }))} />
          </div>
        ) : (
          <div className={`${inputRow} md:col-span-2`}>
            <label className="label-cyber">Endpoint URL</label>
            <input className={inputCls} value={form.url} placeholder="https://mcp.example.com/sse" onChange={(e) => setForm(f => ({ ...f, url: e.target.value }))} />
          </div>
        )}

        <div className={`${inputRow} md:col-span-2`}>
          <label className="label-cyber">Environment Variables <span className="text-cyber-400 text-xs">(one per line: KEY=value)</span></label>
          <textarea
            className="input-cyber w-full min-h-[70px] font-mono text-sm"
            value={form.env}
            placeholder={"GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...\nANTHROPIC_API_KEY=sk-ant-..."}
            onChange={(e) => setForm(f => ({ ...f, env: e.target.value }))}
          />
        </div>
      </div>

      {err && <p className="text-xs text-red-400">{err}</p>}
      <ProbeBanner result={probe} />

      <div className="flex flex-wrap gap-3">
        <button type="submit" className="btn-cyber-magenta" disabled={saving}>
          {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
          {isNew ? 'Add Server' : 'Save Changes'}
        </button>
        <TestButton onTest={test} loading={testing} />
        {!isNew && (
          <DeleteAction
            label="Remove Server"
            onDelete={async () => {
              await api(`/api/v1/admin/mcp/servers/${server!.id}`, { method: 'DELETE' })
              onDone(); onCancel()
            }}
          />
        )}
      </div>
    </form>
  )
}

// ── Access Tokens ───────────────────────────────────────────────────────────

function TokensSection({ tokens, platforms, onChanged }: {
  tokens: TokenRecord[]
  platforms: Record<string, { name: string; hint: string }>
  onChanged: () => void
}) {
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<TokenRecord | null>(null)

  return (
    <SectionCard
      title="Access Tokens"
      icon={KeyRound}
      desc="Credentials for Git hosts, cloud platforms, databases, and observability tools."
      onAdd={() => { setCreating(true); setEditing(null) }}
    >
      {creating && <TokenForm token={null} platforms={platforms} onDone={onChanged} onCancel={() => setCreating(false)} />}

      <div className="space-y-3">
        {tokens.map((t) => {
          const Icon = PLATFORM_ICONS[t.platform] || KeyRound
          return (
            <div key={t.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-cyber-800 flex items-center justify-center">
                  <Icon className="w-6 h-6 text-neon-amber" />
                </div>
                <div>
                  <p className="font-medium text-white">{t.name}</p>
                  <p className="text-xs text-cyber-400 font-mono">{platforms[t.platform]?.name || t.platform}</p>
                  {t.scopes.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {t.scopes.slice(0, 4).map(s => (
                        <span key={s} className="badge-cyber bg-cyber-700 text-cyber-300 text-xs">{s}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`badge-cyber ${t.token_set ? 'bg-neon-green/20 text-neon-green border-neon-green/30' : 'bg-cyber-700 text-cyber-400 border-cyber-600'}`}>
                  {t.token_set ? `token ${t.token_tail}` : 'no token'}
                </span>
                <span className={`badge-cyber ${t.enabled ? 'bg-neon-green/20 text-neon-green border-neon-green/30' : 'bg-cyber-700 text-cyber-400 border-cyber-600'}`}>
                  {t.enabled ? 'enabled' : 'disabled'}
                </span>
                <button className="btn-cyber-ghost text-sm" onClick={() => { setEditing(t); setCreating(false) }}>
                  Configure
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {tokens.length === 0 && !creating && (
        <p className="text-center text-cyber-500 font-mono py-8">No access tokens stored yet.</p>
      )}

      {editing && <TokenForm token={editing} platforms={platforms} onDone={onChanged} onCancel={() => setEditing(null)} />}
    </SectionCard>
  )
}

function TokenForm({ token, platforms, onDone, onCancel }: {
  token: TokenRecord | null
  platforms: Record<string, { name: string; hint: string }>
  onDone: () => void
  onCancel: () => void
}) {
  const [form, setForm] = useState(
    token
      ? { name: token.name, platform: token.platform, scopes: token.scopes.join(', ') }
      : { name: '', platform: 'github', scopes: '' }
  )
  const [tokenValue, setTokenValue] = useState('')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [probe, setProbe] = useState<ProbeResult | null>(null)
  const [testing, setTesting] = useState(false)

  const save = async (e: FormEvent | null, close = true) => {
    if (e) e.preventDefault()
    setSaving(true)
    setErr(null)
    try {
      await api('/api/v1/admin/tokens', {
        method: 'POST',
        body: JSON.stringify({
          id: token?.id,
          name: form.name,
          platform: form.platform,
          scopes: form.scopes.split(',').map(s => s.trim()).filter(Boolean),
          token: tokenValue,
        }),
      })
      onDone()
      if (close) onCancel()
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const test = async () => {
    setTesting(true)
    setProbe(null)
    try {
      await save(null, false)
      const id = token?.id || form.name
      const res = await api<{ result: ProbeResult }>(`/api/v1/admin/tokens/${encodeURIComponent(id)}/test`, { method: 'POST', body: '{}' })
      setProbe(res.result)
    } catch (e) {
      setProbe({ ok: false, detail: e instanceof Error ? e.message : 'Test failed' })
    } finally {
      setTesting(false)
    }
  }

  return (
    <form onSubmit={(e) => save(e, true)} className="mb-6 p-5 rounded-lg bg-cyber-900/60 border border-neon-cyan/30 space-y-4 animate-in slide-in-from-top-2">
      <div className="flex items-center justify-between">
        <h4 className="font-display font-bold text-white">{token ? `Configure ${token.name}` : 'Add Access Token'}</h4>
        <button type="button" onClick={onCancel} className="text-cyber-400 hover:text-white text-sm">Close</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className={inputRow}>
          <label className="label-cyber">Name</label>
          <input className={inputCls} value={form.name} placeholder="Production PAT" onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} />
        </div>
        <div className={inputRow}>
          <label className="label-cyber">Platform</label>
          <select
            className={inputCls}
            value={form.platform}
            disabled={!!token}
            onChange={(e) => setForm(f => ({ ...f, platform: e.target.value }))}
          >
            {Object.entries(platforms).map(([id, p]) => (
              <option key={id} value={id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div className={`${inputRow} md:col-span-2`}>
          <label className="label-cyber">Token {token?.token_set && <span className="text-cyber-400 text-xs">(leave blank to keep {token.token_tail})</span>}</label>
          <input
            className={inputCls}
            type="password"
            autoComplete="off"
            value={tokenValue}
            placeholder={token?.token_set ? '••••••••••••' : 'ghp_...'}
            onChange={(e) => setTokenValue(e.target.value)}
          />
          {platforms[form.platform] && (
            <p className="text-xs text-cyber-500 mt-1">{platforms[form.platform].hint}</p>
          )}
        </div>
        <div className={`${inputRow} md:col-span-2`}>
          <label className="label-cyber">Scopes <span className="text-cyber-400 text-xs">(comma-separated)</span></label>
          <input className={inputCls} value={form.scopes} placeholder="repo, read:org" onChange={(e) => setForm(f => ({ ...f, scopes: e.target.value }))} />
        </div>
      </div>

      {err && <p className="text-xs text-red-400">{err}</p>}
      <ProbeBanner result={probe} />

      <div className="flex flex-wrap gap-3">
        <button type="submit" className="btn-cyber-magenta" disabled={saving}>
          {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
          {token ? 'Save Changes' : 'Add Token'}
        </button>
        {token && <TestButton onTest={test} loading={testing} />}
        {token && (
          <DeleteAction
            label="Remove Token"
            onDelete={async () => {
              await api(`/api/v1/admin/tokens/${token.id}`, { method: 'DELETE' })
              onDone(); onCancel()
            }}
          />
        )}
      </div>
    </form>
  )
}

// ── Delete button ───────────────────────────────────────────────────────────

function DeleteAction({ label, onDelete }: { label: string; onDelete: () => Promise<void> }) {
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  return (
    <button
      type="button"
      className="btn-cyber-ghost text-sm text-red-400 hover:text-red-300 border-red-500/30"
      onClick={async () => {
        if (!confirming) { setConfirming(true); setTimeout(() => setConfirming(false), 4000); return }
        setBusy(true)
        try { await onDelete() } finally { setBusy(false) }
      }}
    >
      <Trash2 className="w-4 h-4 mr-2" />
      {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
      {confirming ? 'Confirm?' : label}
    </button>
  )
}