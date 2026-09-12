import { useState, useEffect, useCallback, FormEvent, type ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import {
  User,
  Shield,
  Bell,
  Palette,
  Globe,
  Terminal,
  Save,
  CheckCircle,
  Sparkles,
  GitBranch,
  Plus,
  Trash2,
  Moon,
  Sun,
  Slack,
  MessageSquare,
  Loader2,
  X,
  Send,
  RefreshCw,
  KeyRound,
  AlertCircle,
  CheckCircle2,
  Gitlab,
  GitFork,
  Boxes,
  Cloud,
  Triangle,
  Network,
  CloudCog,
  Bot,
  Kanban,
  Zap,
  Activity,
  Database,
  MemoryStick,
  Container,
  Gauge,
  Copy,
  LogOut,
} from 'lucide-react'

// ── API helper (mirrors Admin.tsx / AgentTeam.tsx) ───────────────────────────

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

export default function Settings() {
  const { user } = useAuth()
  const { theme, setTheme, accent, setAccent } = useTheme()

  const [activeSection, setActiveSection] = useState<'profile' | 'security' | 'notifications' | 'appearance' | 'integrations' | 'advanced'>('profile')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const sections = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'integrations', label: 'Integrations', icon: Globe },
    { id: 'advanced', label: 'Advanced', icon: Terminal },
  ]

  const handleSave = async () => {
    setSaving(true)
    await new Promise(resolve => setTimeout(resolve, 1000))
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> Settings
          </h1>
          <p className="text-cyber-400 mt-1">Configure your Git-Fix experience</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-cyber-magenta flex items-center gap-2 self-start"
        >
          {saving ? (
            <span className="flex items-center gap-2">
              <div className="w-5 h-5 border-2 border-neon-cyan border-t-transparent rounded-full animate-spin" />
              Saving...
            </span>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Save Changes
            </>
          )}
        </button>
      </div>

      {saved && (
        <div className="mb-6 p-4 rounded-lg bg-neon-green/20 border border-neon-green/30 flex items-center gap-3 text-neon-green animate-in slide-in-from-top-2">
          <CheckCircle className="w-5 h-5" />
          <span className="font-medium">Settings saved successfully!</span>
        </div>
      )}

      <div className="card-cyber overflow-hidden">
        {/* Sidebar Navigation — desktop */}
        <div className="hidden md:flex">
          <nav className="w-56 border-r border-cyber-700/50 p-4 space-y-1" aria-label="Settings sections">
            {sections.map((section) => {
              const Icon = section.icon
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id as any)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left text-sm font-medium transition-all min-h-[44px] cursor-pointer ${
                    activeSection === section.id
                      ? 'bg-neon-magenta/20 text-neon-magenta border-r-2 border-neon-magenta'
                      : 'text-cyber-400 hover:text-cyber-200 hover:bg-cyber-800/50'
                  }`}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {section.label}
                </button>
              )
            })}
          </nav>

          {/* Content Area */}
          <div className="flex-1 p-8 overflow-y-auto">
            {activeSection === 'profile' && <ProfileSection user={user} />}
            {activeSection === 'security' && <SecuritySection />}
            {activeSection === 'notifications' && <NotificationsSection />}
            {activeSection === 'appearance' && <AppearanceSection theme={theme} setTheme={setTheme} accent={accent} setAccent={setAccent} />}
            {activeSection === 'integrations' && <IntegrationsSection />}
            {activeSection === 'advanced' && <AdvancedSection />}
          </div>
        </div>

        {/* Mobile: horizontal scroll tabs + stacked content */}
        <div className="md:hidden">
          <div className="scroll-snap-x flex gap-1.5 overflow-x-auto px-2 py-3 border-b border-cyber-700/50 scrollbar-hide">
            {sections.map((section) => {
              const Icon = section.icon
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id as any)}
                  className={`scroll-snap-start flex flex-col items-center justify-center gap-1 px-4 py-2 rounded-lg text-xs font-medium transition-all min-h-[56px] min-w-[72px] cursor-pointer flex-shrink-0 ${
                    activeSection === section.id
                      ? 'bg-neon-magenta/20 text-neon-magenta border border-neon-magenta/30'
                      : 'text-cyber-400 hover:text-cyber-200 hover:bg-cyber-800/50 border border-transparent'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {section.label}
                </button>
              )
            })}
          </div>
          <div className="p-4 sm:p-6">
            {activeSection === 'profile' && <ProfileSection user={user} />}
            {activeSection === 'security' && <SecuritySection />}
            {activeSection === 'notifications' && <NotificationsSection />}
            {activeSection === 'appearance' && <AppearanceSection theme={theme} setTheme={setTheme} accent={accent} setAccent={setAccent} />}
            {activeSection === 'integrations' && <IntegrationsSection />}
            {activeSection === 'advanced' && <AdvancedSection />}
          </div>
        </div>
      </div>
    </div>
  )
}

// Profile Section
function ProfileSection({ user }: { user: any }) {
  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4 md:gap-6">
        <div className="w-20 h-20 md:w-24 md:h-24 rounded-xl bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 font-bold text-2xl flex-shrink-0">
          {user?.username?.charAt(0).toUpperCase() || 'U'}
        </div>
        <div className="min-w-0">
          <h3 className="text-xl md:text-2xl font-bold font-display text-white truncate">{user?.username}</h3>
          <p className="text-cyber-400 text-sm truncate">{user?.email}</p>
          <span className="badge-cyber bg-cyber-700 text-cyber-300 capitalize mt-2 inline-block">{user?.role}</span>
        </div>
      </div>

      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-6 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          Profile Information
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="label-cyber">Username</label>
            <input type="text" defaultValue={user?.username} className="input-cyber font-mono" disabled />
            <p className="text-xs text-cyber-500 mt-1">Cannot be changed</p>
          </div>
          <div>
            <label className="label-cyber">Email</label>
            <input type="email" defaultValue={user?.email} className="input-cyber" disabled />
            <p className="text-xs text-cyber-500 mt-1">Contact support to change</p>
          </div>
          <div>
            <label className="label-cyber">Full Name</label>
            <input type="text" className="input-cyber" placeholder="John Doe" />
          </div>
          <div>
            <label className="label-cyber">Company</label>
            <input type="text" className="input-cyber" placeholder="Git-Fix Inc." />
          </div>
          <div className="md:col-span-2">
            <label className="label-cyber">Bio</label>
            <textarea className="input-cyber min-h-[100px] resize-y" placeholder="Tell us about yourself..." />
          </div>
          <div>
            <label className="label-cyber">Location</label>
            <input type="text" className="input-cyber" placeholder="San Francisco, CA" />
          </div>
          <div>
            <label className="label-cyber">Website</label>
            <input type="url" className="input-cyber" placeholder="https://github.com/username" />
          </div>
        </div>
      </div>

      <div className="card-cyber p-6 border-t border-cyber-700/50">
        <h3 className="text-lg font-bold font-display text-white mb-4">Danger Zone</h3>
        <button className="btn-cyber-ghost text-red-400 hover:text-red-300 hover:bg-red-500/10 border-red-500/30 flex items-center">
          <Trash2 className="w-4 h-4 mr-2" />
          Delete Account
        </button>
      </div>
    </div>
  )
}

// ── Security Section ───────────────────────────────────────────────────────

interface ApiKeyRecord {
  id: string
  name: string
  tail: string
  created_at?: number
  last_used_at?: number | null
}

interface SessionRecord {
  id: string
  device: string
  current: boolean
  created_at?: number
  last_active?: number
  expires_at?: number
  revoked?: boolean
}

interface TfaState {
  enabled: boolean
  secret?: string | null
  otpauth_uri?: string | null
  digits?: number
  period?: number
}

function timeAgo(ts?: number | null): string {
  if (!ts) return '—'
  const s = Math.floor(Date.now() / 1000 - ts)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  if (s < 604800) return `${Math.floor(s / 86400)}d ago`
  return new Date(ts * 1000).toLocaleDateString()
}

function CopyButton({ text, label = 'copy' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch { /* clipboard unavailable */ }
  }
  return (
    <button
      onClick={copy}
      type="button"
      aria-label={`Copy ${label}`}
      className="p-1.5 rounded-lg text-cyber-400 hover:text-white hover:bg-cyber-800 transition-colors flex-shrink-0"
    >
      {copied ? <CheckCircle2 className="w-4 h-4 text-neon-green" /> : <Copy className="w-4 h-4" />}
    </button>
  )
}

function SecuritySection() {
  const [tfa, setTfa] = useState<TfaState>({ enabled: false })
  const [apiKeys, setApiKeys] = useState<ApiKeyRecord[]>([])
  const [sessions, setSessions] = useState<SessionRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tfaModal, setTfaModal] = useState<{ mode: 'setup'; secret: string; uri: string } | { mode: 'disable' } | null>(null)
  const [newApiKey, setNewApiKey] = useState<{ name: string; key: string } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [t, k, s] = await Promise.all([
        api<TfaState>('/api/v1/auth/2fa/status'),
        api<{ keys: ApiKeyRecord[] }>('/api/v1/auth/api-keys'),
        api<{ sessions: SessionRecord[] }>('/api/v1/auth/sessions'),
      ])
      setTfa(t)
      setApiKeys(k.keys || [])
      setSessions(s.sessions || [])
    } catch (e: any) {
      setError(e?.message || 'Failed to load security settings')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-8">
      {error && <ErrorBanner message={error} onRetry={load} />}

      {loading ? (
        <div className="card-cyber p-10 flex flex-col items-center justify-center gap-2 text-cyber-400">
          <Loader2 className="w-6 h-6 text-neon-cyan animate-spin" />
          <span className="text-sm">Loading security settings…</span>
        </div>
      ) : (
        <>
          <PasswordCard onChanged={() => { }} />
          <TfaCard enabled={tfa.enabled} onEnable={startTfaSetup} onDisable={() => setTfaModal({ mode: 'disable' })} />
          <ApiKeysCard keys={apiKeys} onCreated={load} />
          <SessionsCard sessions={sessions} onChanged={load} />
        </>
      )}

      {tfaModal?.mode === 'setup' && (
        <TfaSetupModal
          secret={tfaModal.secret}
          uri={tfaModal.uri}
          onClose={() => setTfaModal(null)}
          onEnabled={() => { setTfaModal(null); load() }}
        />
      )}
      {tfaModal?.mode === 'disable' && (
        <TfaDisableModal onClose={() => setTfaModal(null)} onDisabled={() => { setTfaModal(null); load() }} />
      )}
      {newApiKey && (
        <NewApiKeyModal
          name={newApiKey.name}
          keyValue={newApiKey.key}
          onClose={() => { setNewApiKey(null); load() }}
        />
      )}
    </div>
  )

  async function startTfaSetup() {
    setError(null)
    try {
      const res = await api<TfaState & { secret: string; otpauth_uri: string }>('/api/v1/auth/2fa/setup', { method: 'POST' })
      setTfaModal({ mode: 'setup', secret: res.secret, uri: res.otpauth_uri })
    } catch (e: any) {
      setError(e?.message || 'Failed to start 2FA setup')
    }
  }
}

// ── 2FA ─────────────────────────────────────────────────────────────────────

function TfaCard({ enabled, onEnable, onDisable }: { enabled: boolean; onEnable: () => void; onDisable: () => void }) {
  return (
    <div className="card-cyber p-6">
      <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
        <Shield className="w-5 h-5 text-neon-magenta" />
        Two-Factor Authentication
      </h3>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <p className="font-medium text-white">
            {enabled ? '2FA is on' : 'Enable 2FA'}
          </p>
          <p className="text-cyber-400 text-sm">
            {enabled
              ? 'Every login requires a 6-digit authenticator code'
              : 'Add an extra layer of security to your account (TOTP, Authy / Google Authenticator)'}
          </p>
        </div>
        {enabled
          ? <button onClick={onDisable} className="btn-cyber-ghost text-sm flex items-center gap-2"><Shield className="w-4 h-4" /> Disable</button>
          : <button onClick={onEnable} className="btn-cyber-magenta text-sm flex items-center gap-2"><Shield className="w-4 h-4" /> Enable 2FA</button>}
      </div>
    </div>
  )
}

function TfaSetupModal({ secret, uri, onClose, onEnabled }: {
  secret: string
  uri: string
  onClose: () => void
  onEnabled: () => void
}) {
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!/^\d{6}$/.test(code.trim())) { setError('Enter the 6-digit code from your authenticator app'); return }
    setBusy(true)
    setError(null)
    try {
      await api('/api/v1/auth/2fa/enable', { method: 'POST', body: JSON.stringify({ code: code.trim() }) })
      onEnabled()
    } catch (err: any) {
      setError(err?.message || 'Failed to enable 2FA')
    } finally {
      setBusy(false)
    }
  }

  return (
    <ModalShell title="Enable two-factor authentication" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-cyber-400">
          Scan this with your authenticator app, or enter the secret manually (this screen cannot display a QR image):
        </p>
        <div>
          <label className="label-cyber">Secret</label>
          <div className="flex items-center gap-2">
            <code className="flex-1 p-2.5 rounded-lg bg-cyber-800/70 border border-cyber-700/50 font-mono text-neon-cyan break-all">{secret}</code>
            <CopyButton text={secret} label="secret" />
          </div>
        </div>
        <div>
          <label className="label-cyber">or copy otpauth:// link</label>
          <div className="flex items-center gap-2">
            <code className="flex-1 p-2.5 rounded-lg bg-cyber-800/70 border border-cyber-700/50 font-mono text-xs text-cyber-400 break-all leading-relaxed">{uri}</code>
            <CopyButton text={uri} label="otpauth link" />
          </div>
        </div>
        <div>
          <label className="label-cyber" htmlFor="tfa-code">6-digit code</label>
          <input
            id="tfa-code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            className="input-cyber font-mono tracking-widest"
            placeholder="000000"
            autoFocus
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="flex items-center gap-3 pt-1">
          <button type="submit" disabled={busy} className="btn-cyber-magenta flex items-center gap-2">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            Enable 2FA
          </button>
          <button type="button" onClick={onClose} className="btn-cyber-ghost">Cancel</button>
        </div>
      </form>
    </ModalShell>
  )
}

function TfaDisableModal({ onClose, onDisabled }: { onClose: () => void; onDisabled: () => void }) {
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api('/api/v1/auth/2fa/disable', { method: 'POST', body: JSON.stringify({ code: code.trim() }) })
      onDisabled()
    } catch (err: any) {
      setError(err?.message || 'Failed to disable 2FA')
    } finally {
      setBusy(false)
    }
  }

  return (
    <ModalShell title="Disable two-factor authentication" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <p className="text-sm text-cyber-400">Enter your current authenticator code to confirm.</p>
        <div>
          <label className="label-cyber" htmlFor="tfa-disable-code">6-digit code</label>
          <input
            id="tfa-disable-code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            className="input-cyber font-mono tracking-widest"
            placeholder="000000"
            autoFocus
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="flex items-center gap-3 pt-1">
          <button type="submit" disabled={busy} className="btn-cyber-magenta flex items-center gap-2">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            Disable 2FA
          </button>
          <button type="button" onClick={onClose} className="btn-cyber-ghost">Cancel</button>
        </div>
      </form>
    </ModalShell>
  )
}

// ── API keys ────────────────────────────────────────────────────────────────

function ApiKeysCard({ keys, onCreated }: { keys: ApiKeyRecord[]; onCreated: () => void }) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [revealed, setRevealed] = useState<{ name: string; key: string } | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  async function create(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) { setError('Give the key a name'); return }
    setBusy(true)
    setError(null)
    try {
      const res = await api<{ record: ApiKeyRecord; key: string }>('/api/v1/auth/api-keys', {
        method: 'POST',
        body: JSON.stringify({ name: name.trim() }),
      })
      setRevealed({ name: res.record.name, key: res.key })
      setName('')
      onCreated()
    } catch (err: any) {
      setError(err?.message || 'Failed to create API key')
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    setDeleting(id)
    setError(null)
    try {
      await api(`/api/v1/auth/api-keys/${id}`, { method: 'DELETE' })
      onCreated()
    } catch (err: any) {
      setError(err?.message || 'Failed to delete API key')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="card-cyber p-6">
      <h3 className="text-lg font-bold font-display text-white mb-1 flex items-center gap-2">
        <KeyRound className="w-5 h-5 text-neon-magenta" />
        API Keys
      </h3>
      <p className="text-cyber-400 text-sm mb-4">Use these keys to authenticate CI/CD and external integrations. Keys are only shown once after creation.</p>

      <form onSubmit={create} className="flex flex-col sm:flex-row gap-3 mb-5">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="input-cyber flex-1"
          placeholder="Key name, e.g. ci-runner"
          maxLength={80}
          aria-label="API key name"
        />
        <button type="submit" disabled={busy} className="btn-cyber-magenta flex items-center justify-center gap-2">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          Generate New API Key
        </button>
      </form>

      {error && <p className="text-sm text-red-400 mb-3">{error}</p>}

      {keys.length === 0 ? (
        <p className="text-sm text-cyber-500">No API keys yet.</p>
      ) : (
        <div className="space-y-2">
          {keys.map((k) => (
            <div key={k.id} className="flex items-center justify-between gap-3 p-3.5 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <div className="min-w-0">
                <p className="font-medium text-white flex items-center gap-2">
                  {k.name}
                  <span className="badge-cyber bg-cyber-700 text-cyber-400 text-xs font-mono">{'••••••••••••'}{k.tail}</span>
                </p>
                <p className="text-xs text-cyber-500 mt-0.5">
                  Created {timeAgo(k.created_at)}{k.last_used_at ? ` · last used ${timeAgo(k.last_used_at)}` : ''}
                </p>
              </div>
              <button
                onClick={() => remove(k.id)}
                disabled={deleting === k.id}
                className="p-2 rounded-lg text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
                aria-label={`Revoke key ${k.name}`}
              >
                {deleting === k.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              </button>
            </div>
          ))}
        </div>
      )}

      {revealed && (
        <NewApiKeyModal
          name={revealed.name}
          keyValue={revealed.key}
          onClose={() => setRevealed(null)}
        />
      )}
    </div>
  )
}

function NewApiKeyModal({ name, keyValue, onClose }: { name: string; keyValue: string; onClose: () => void }) {
  return (
    <ModalShell title="API key created" onClose={onClose}>
      <div className="space-y-4">
        <p className="text-sm text-cyber-400">
          <span className="text-white font-medium">{name}</span> — copy this key now. It will not be shown again.
        </p>
        <div>
          <label className="label-cyber">API Key</label>
          <div className="flex items-center gap-2">
            <code className="flex-1 p-2.5 rounded-lg bg-cyber-800/70 border border-cyber-700/50 font-mono text-neon-magenta break-all">{keyValue}</code>
            <CopyButton text={keyValue} label="api key" />
          </div>
        </div>
        <p className="text-xs text-cyber-500">
          Authenticate with <code className="font-mono text-cyan-300">X-API-Key: {keyValue.slice(0, 8)}...</code> or <code className="font-mono text-cyan-300">?api_key=</code> on supported endpoints.
        </p>
        <button onClick={onClose} className="btn-cyber-ghost w-full">Done</button>
      </div>
    </ModalShell>
  )
}

// ── Active sessions ─────────────────────────────────────────────────────────

function SessionsCard({ sessions, onChanged }: { sessions: SessionRecord[]; onChanged: () => void }) {
  const [busy, setBusy] = useState<string | '' | 'all' | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function run(endpoint: string, body?: Record<string, unknown>, id?: string) {
    setBusy(id ?? '')
    setError(null)
    try {
      await api(endpoint, { method: 'POST', body: body ? JSON.stringify(body) : undefined })
      onChanged()
    } catch (err: any) {
      setError(err?.message || 'Request failed')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="card-cyber p-6">
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
          <Shield className="w-5 h-5 text-neon-magenta" />
          Active Sessions
        </h3>
        {sessions.length > 1 && (
          <button
            onClick={() => run('/api/v1/auth/sessions/revoke-all', {}, 'all')}
            disabled={busy !== null}
            className="btn-cyber-ghost text-sm flex items-center gap-2"
          >
            {busy === 'all' ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogOut className="w-4 h-4" />}
            Revoke All
          </button>
        )}
      </div>

      {error && <p className="text-sm text-red-400 mb-3">{error}</p>}

      {sessions.length === 0 ? (
        <p className="text-sm text-cyber-500">No active sessions.</p>
      ) : (
        <div className="space-y-3">
          {sessions.map((session) => (
            <div key={session.id} className="flex items-center justify-between gap-3 p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 rounded-lg bg-cyber-800 flex items-center justify-center flex-shrink-0">
                  <Terminal className="w-5 h-5 text-neon-cyan" />
                </div>
                <div className="min-w-0">
                  <p className="font-medium text-white truncate">{session.device}</p>
                  <p className="text-xs text-cyber-400">
                    {session.current ? 'This device · ' : ''}Last active {timeAgo(session.last_active)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {session.current
                  ? <span className="badge-cyber bg-neon-green/20 text-neon-green border-neon-green/30 text-xs">Current</span>
                  : (
                    <button
                      onClick={() => run('/api/v1/auth/sessions/revoke', { id: session.id }, session.id)}
                      disabled={busy !== null}
                      className="text-red-400 hover:text-red-300 text-sm font-mono flex items-center gap-1"
                      aria-label={`Revoke session on ${session.device}`}
                    >
                      {busy === session.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <LogOut className="w-3.5 h-3.5" />}
                      Revoke
                    </button>
                  )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Password ────────────────────────────────────────────────────────────────

function PasswordCard({ onChanged }: { onChanged: () => void }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState(false)

  function reset() {
    setCurrent('')
    setNext('')
    setConfirm('')
    setOk(false)
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setOk(false)
    if (next.length < 8) { setError('New password must be at least 8 characters'); return }
    if (next !== confirm) { setError('New passwords do not match'); return }
    setBusy(true)
    setError(null)
    try {
      await api('/api/v1/auth/password', {
        method: 'POST',
        body: JSON.stringify({ current_password: current, new_password: next }),
      })
      reset()
      setOk(true)
      onChanged()
    } catch (err: any) {
      setError(err?.message || 'Failed to change password')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card-cyber p-6">
      <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
        <KeyRound className="w-5 h-5 text-neon-magenta" />
        Password
      </h3>
      <form onSubmit={submit} className="space-y-4 max-w-md">
        <div>
          <label className="label-cyber" htmlFor="pw-current">Current password</label>
          <input
            id="pw-current"
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            className="input-cyber"
            autoComplete="current-password"
            required
          />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label-cyber" htmlFor="pw-new">New password</label>
            <input
              id="pw-new"
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              className="input-cyber"
              autoComplete="new-password"
              minLength={8}
              required
            />
          </div>
          <div>
            <label className="label-cyber" htmlFor="pw-confirm">Confirm new password</label>
            <input
              id="pw-confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="input-cyber"
              autoComplete="new-password"
              minLength={8}
              required
            />
          </div>
        </div>
        <p className="text-xs text-cyber-500">Minimum 8 characters. Once set, this replaces the GITFIX_ADMIN_PASSWORD boot credential.</p>
        {error && <p className="text-sm text-red-400">{error}</p>}
        {ok && (
          <p className="text-sm text-neon-green flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" /> Password updated successfully
          </p>
        )}
        <div>
          <button type="submit" disabled={busy} className="btn-cyber-magenta flex items-center gap-2">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Change Password
          </button>
        </div>
      </form>
    </div>
  )
}

// Notifications Section
function NotificationsSection() {
  const [prefs, setPrefs] = useState({
    email: true,
    push: true,
    slack: false,
    discord: false,
    webhook: false,
    critical: true,
    high: true,
    medium: false,
    low: false,
    dailyDigest: true,
    weeklyReport: false,
  })

  return (
    <div className="space-y-8">
      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          Notification Channels
        </h3>
        <div className="space-y-4">
          {[
            { key: 'email', label: 'Email', desc: 'Receive notifications via email' },
            { key: 'push', label: 'Push Notifications', desc: 'Browser push notifications' },
            { key: 'slack', label: 'Slack', desc: 'Post to Slack channels' },
            { key: 'discord', label: 'Discord', desc: 'Post to Discord channels' },
            { key: 'webhook', label: 'Custom Webhook', desc: 'Send to custom HTTP endpoint' },
          ].map((ch) => (
            <label key={ch.key} className="flex items-center justify-between p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={prefs[ch.key as keyof typeof prefs]}
                  onChange={(e) => setPrefs(prev => ({ ...prev, [ch.key]: e.target.checked }))}
                  className="w-5 h-5 accent-neon-magenta"
                />
                <div>
                  <p className="font-medium text-white">{ch.label}</p>
                  <p className="text-xs text-cyber-400">{ch.desc}</p>
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          Severity Filters
        </h3>
        <p className="text-cyber-400 mb-4">Only notify for findings at or above this severity</p>
        <div className="space-y-4">
          {[
            { key: 'critical', label: 'Critical', color: 'red' },
            { key: 'high', label: 'High', color: 'orange' },
            { key: 'medium', label: 'Medium', color: 'amber' },
            { key: 'low', label: 'Low', color: 'green' },
          ].map((sev) => (
            <label key={sev.key} className="flex items-center justify-between p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={prefs[sev.key as keyof typeof prefs]}
                  onChange={(e) => setPrefs(prev => ({ ...prev, [sev.key]: e.target.checked }))}
                  className="w-5 h-5 accent-neon-magenta"
                />
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: sev.color }} />
                  <p className="font-medium text-white capitalize">{sev.label}</p>
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          Digest Settings
        </h3>
        <div className="space-y-4">
          {[
            { key: 'dailyDigest', label: 'Daily Digest', desc: 'Summary of all findings each morning' },
            { key: 'weeklyReport', label: 'Weekly Report', desc: 'Comprehensive weekly security report' },
          ].map((opt) => (
            <label key={opt.key} className="flex items-center justify-between p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={prefs[opt.key as keyof typeof prefs]}
                  onChange={(e) => setPrefs(prev => ({ ...prev, [opt.key]: e.target.checked }))}
                  className="w-5 h-5 accent-neon-magenta"
                />
                <div>
                  <p className="font-medium text-white">{opt.label}</p>
                  <p className="text-xs text-cyber-400">{opt.desc}</p>
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}

// Appearance Section
function AppearanceSection({ theme, setTheme, accent, setAccent }: {
  theme: 'dark' | 'light'
  setTheme: (t: 'dark' | 'light') => void
  accent: 'magenta' | 'cyan' | 'amber' | 'green'
  setAccent: (a: 'magenta' | 'cyan' | 'amber' | 'green') => void
}) {
  return (
    <div className="space-y-8">
      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          Theme
        </h3>
        <div className="grid grid-cols-2 gap-4">
          {['dark', 'light'].map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t as 'dark' | 'light')}
              className={`p-6 rounded-xl border-2 transition-all ${
                theme === t
                  ? 'border-neon-magenta bg-neon-magenta/10 shadow-[0_0_20px_rgba(255,0,255,0.2)]'
                  : 'border-cyber-700/50 hover:border-neon-magenta/50'
              }`}
            >
              <div className="w-16 h-16 rounded-xl mx-auto mb-4 flex items-center justify-center" style={{
                background: t === 'dark' 
                  ? 'linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%)'
                  : 'linear-gradient(135deg, #ffffff 0%, #f0f0f0 100%)'
              }}>
                {t === 'dark' ? <Moon className="w-8 h-8 text-cyber-300" /> : <Sun className="w-8 h-8 text-amber-500" />}
              </div>
              <p className="font-medium text-white capitalize">{t}</p>
              <p className="text-xs text-cyber-400 mt-1">
                {t === 'dark' ? 'Easy on the eyes' : 'Bright and clean'}
              </p>
            </button>
          ))}
        </div>
      </div>

      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          Accent Color
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { name: 'Magenta', value: '#ff00ff', key: 'magenta' },
            { name: 'Cyan', value: '#00ffff', key: 'cyan' },
            { name: 'Amber', value: '#ff8c00', key: 'amber' },
            { name: 'Green', value: '#00ff00', key: 'green' },
          ].map((color) => (
            <button
              key={color.name}
              onClick={() => setAccent(color.key as 'magenta' | 'cyan' | 'amber' | 'green')}
              aria-pressed={accent === color.key}
              className={`p-4 rounded-xl border-2 transition-all cursor-pointer ${
                accent === color.key
                  ? 'border-neon-magenta bg-neon-magenta/10 shadow-[0_0_20px_rgba(255,0,255,0.15)]'
                  : 'border-cyber-700/50 hover:border-neon-magenta/50'
              } ${theme === 'dark' ? 'bg-cyber-800' : 'bg-white'}`}
            >
              <div className="w-full h-12 rounded-lg mb-3" style={{ backgroundColor: color.value }} />
              <p className={`font-medium ${accent === color.key ? 'text-neon-magenta' : 'text-white'} capitalize`}>{color.name}</p>
              <p className="text-xs text-cyber-400 font-mono mt-1">{color.value}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          Animations
        </h3>
        <div className="space-y-4">
          {[
            { key: 'reducedMotion', label: 'Reduce Motion', desc: 'Disable non-essential animations' },
            { key: 'particleEffects', label: 'Particle Effects', desc: 'Background particle animations' },
            { key: 'glowEffects', label: 'Glow Effects', desc: 'Neon glow on interactive elements' },
          ].map((opt) => (
            <label key={opt.key} className="flex items-center justify-between p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <div className="flex items-center gap-3">
                <input type="checkbox" defaultChecked className="w-5 h-5 accent-neon-magenta" />
                <div>
                  <p className="font-medium text-white">{opt.label}</p>
                  <p className="text-xs text-cyber-400">{opt.desc}</p>
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Integrations Section ─────────────────────────────────────────────────────

interface TokenRecord {
  id: string
  name: string
  platform: string
  scopes: string[]
  enabled: boolean
  token_set: boolean
  token_tail: string
  endpoint_set?: boolean
  endpoint_tail?: string
  created_at?: number
  updated_at?: number
}

interface WebhookRecord {
  id: string
  name: string
  kind: string
  channel: string
  url_set: boolean
  url_tail: string
  enabled: boolean
  created_at?: number
  updated_at?: number
}

interface ProbeResult {
  ok: boolean
  status?: number | null
  detail: string
}

type ModalState =
  | { kind: 'token'; platform: string; mode: 'connect' | 'manage' }
  | { kind: 'webhook'; key: string; mode: 'connect' | 'manage' }
  | null

type TokenIntegrationMeta = {
  platform: string
  name: string
  desc: string
  hint: string
  icon: ReactNode
  credentialLabel?: string
  placeholder?: string
  endpointOptional?: boolean
  endpointHint?: string
}

const TOKEN_INTEGRATIONS: TokenIntegrationMeta[] = [
  {
    platform: 'github',
    name: 'GitHub',
    desc: 'Source control & PR reviews',
    hint: 'Fine-grained PAT (ghp_) or classic PAT — scopes: repo, read:org',
    icon: <GitBranch className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'gitlab',
    name: 'GitLab',
    desc: 'Alternative Git hosting',
    hint: 'Personal access token (glpat-) scoped to api',
    icon: <Gitlab className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'bitbucket',
    name: 'Bitbucket',
    desc: 'Repo hosting & pipelines',
    hint: 'Store as username:app-password with repo read access',
    icon: <Boxes className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'azure_devops',
    name: 'Azure DevOps',
    desc: 'Microsoft repo hosting & boards',
    hint: 'PAT with Code Read scope',
    icon: <Cloud className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'vercel',
    name: 'Vercel',
    desc: 'Frontend deploys & previews',
    hint: 'API token from vercel.com/account/tokens (read scope)',
    credentialLabel: 'API Token',
    placeholder: 'Vercel API token',
    icon: <Triangle className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'netlify',
    name: 'Netlify',
    desc: 'Static site deploys & forms',
    hint: 'Personal access token from app.netlify.com/user/applications',
    credentialLabel: 'Personal Access Token',
    placeholder: 'Netlify access token',
    icon: <Network className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'cloudflare',
    name: 'Cloudflare',
    desc: 'CDN, DNS & Workers',
    hint: 'API token from dash.cloudflare.com/profile/api-tokens',
    credentialLabel: 'API Token',
    placeholder: 'Cloudflare API token',
    icon: <CloudCog className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'huggingface',
    name: 'Hugging Face',
    desc: 'Models, Spaces & datasets',
    hint: 'Access token from huggingface.co/settings/tokens',
    placeholder: 'hf_…',
    icon: <Bot className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'codeberg',
    name: 'Codeberg',
    desc: 'Community Git hosting',
    hint: 'Token from codeberg.org/user/settings/applications',
    placeholder: 'Codeberg token',
    icon: <GitFork className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'jira',
    name: 'Jira',
    desc: 'Issue tracking & boards',
    hint: 'Store as email:your-api-token (Atlassian API token); set your site URL in Endpoint',
    credentialLabel: 'Email:API token',
    placeholder: 'you@company.com:your-api-token',
    endpointOptional: true,
    endpointHint: 'Atlassian site URL, e.g. https://your-domain.atlassian.net',
    icon: <Kanban className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'linear',
    name: 'Linear',
    desc: 'Issue tracking for product teams',
    hint: 'Personal API key from linear.app/settings/api',
    credentialLabel: 'API Key',
    placeholder: 'Linear API key',
    icon: <Zap className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'datadog',
    name: 'Datadog',
    desc: 'Monitoring & observability',
    hint: 'Datadog API key; override Endpoint for a regional site (https://api.eu.datadoghq.com etc.)',
    credentialLabel: 'API Key',
    placeholder: 'Datadog API key',
    endpointOptional: true,
    endpointHint: 'Regional API endpoint, e.g. https://api.us3.datadoghq.com',
    icon: <Activity className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'sentry',
    name: 'Sentry',
    desc: 'Error tracking & releases',
    hint: 'Auth token from sentry.io/settings/auth-tokens (or your self-hosted Sentry)',
    credentialLabel: 'Auth Token',
    placeholder: 'sntrys_…',
    endpointOptional: true,
    endpointHint: 'Sentry base URL, e.g. https://sentry.io or https://sentry.example.com',
    icon: <Shield className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'postgresql',
    name: 'PostgreSQL',
    desc: 'Relational database',
    hint: 'postgresql://user:pass@host:5432/dbname — reachability only, credentials are not checked',
    credentialLabel: 'Connection string',
    placeholder: 'postgresql://user:pass@host:5432/dbname',
    icon: <Database className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'redis',
    name: 'Redis',
    desc: 'In-memory cache & queue',
    hint: 'redis://:password@host:6379 — reachability only, credentials are not checked',
    credentialLabel: 'Connection string',
    placeholder: 'redis://:password@host:6379',
    icon: <MemoryStick className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'qdrant',
    name: 'Qdrant',
    desc: 'Vector database',
    hint: 'Full Qdrant base URL, e.g. http://localhost:6333',
    credentialLabel: 'Endpoint URL',
    placeholder: 'http://localhost:6333',
    icon: <Container className="w-6 h-6 text-neon-cyan" />,
  },
  {
    platform: 'prometheus',
    name: 'Prometheus',
    desc: 'Metrics & alerting',
    hint: 'Prometheus base URL, e.g. http://localhost:9090',
    credentialLabel: 'Endpoint URL',
    placeholder: 'http://localhost:9090',
    icon: <Gauge className="w-6 h-6 text-neon-cyan" />,
  },
]

const WEBHOOK_INTEGRATIONS: Array<{ kind: string; name: string; desc: string; hint: string; icon: ReactNode }> = [
  {
    kind: 'slack',
    name: 'Slack',
    desc: 'Team notifications via incoming webhook',
    hint: 'Incoming webhook URL from Slack (https://hooks.slack.com/...)',
    icon: <Slack className="w-6 h-6 text-neon-cyan" />,
  },
  {
    kind: 'discord',
    name: 'Discord',
    desc: 'Community notifications via incoming webhook',
    hint: 'Incoming webhook URL from Discord (https://discord.com/api/webhooks/...)',
    icon: <MessageSquare className="w-6 h-6 text-neon-cyan" />,
  },
]

function IntegrationsSection() {
  const [tokenList, setTokenList] = useState<TokenRecord[]>([])
  const [webhookList, setWebhookList] = useState<WebhookRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modal, setModal] = useState<ModalState>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [t, w] = await Promise.all([
        api<{ tokens: TokenRecord[] }>('/api/v1/admin/tokens'),
        api<{ webhooks: WebhookRecord[] }>('/api/v1/integrations/webhooks'),
      ])
      setTokenList(t.tokens || [])
      setWebhookList(w.webhooks || [])
    } catch (e: any) {
      setError(e?.message || 'Failed to load integrations')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-4">
      {error && <ErrorBanner message={error} onRetry={load} />}

      <div className="card-cyber p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold font-display text-white">Available integrations</h3>
          {loading && <Loader2 className="w-4 h-4 text-neon-cyan animate-spin" />}
        </div>
        <p className="text-xs text-cyber-400 mt-1">
          Connect code hosting and notification channels. Credentials stay on this server and are never shown in full again.
        </p>
      </div>

      {loading ? (
        <div className="card-cyber p-10 flex flex-col items-center justify-center gap-2 text-cyber-400">
          <Loader2 className="w-6 h-6 text-neon-cyan animate-spin" />
          <span className="text-sm">Loading integrations…</span>
        </div>
      ) : (
        <>
          {TOKEN_INTEGRATIONS.map((it) => {
            const connected = tokenList.some((tk) => tk.platform === it.platform && tk.enabled)
            return (
              <IntegrationRow
                key={it.platform}
                name={it.name}
                desc={it.desc}
                icon={it.icon}
                connected={connected}
                onConnect={() => setModal({ kind: 'token', platform: it.platform, mode: 'connect' })}
                onManage={() => setModal({ kind: 'token', platform: it.platform, mode: 'manage' })}
              />
            )
          })}

          {WEBHOOK_INTEGRATIONS.map((it) => {
            const connected = webhookList.some((wh) => wh.kind === it.kind && wh.enabled)
            return (
              <IntegrationRow
                key={it.kind}
                name={it.name}
                desc={it.desc}
                icon={it.icon}
                connected={connected}
                onConnect={() => setModal({ kind: 'webhook', key: it.kind, mode: 'connect' })}
                onManage={() => setModal({ kind: 'webhook', key: it.kind, mode: 'manage' })}
              />
            )
          })}
        </>
      )}

      {modal && modal.kind === 'token' && (
        modal.mode === 'connect' ? (
          <TokenConnectModal platform={modal.platform} onClose={() => setModal(null)} onSaved={load} />
        ) : (
          <TokenManageModal
            platform={modal.platform}
            records={tokenList.filter((tk) => tk.platform === modal.platform)}
            onClose={() => setModal(null)}
            onChanged={load}
          />
        )
      )}

      {modal && modal.kind === 'webhook' && (
        modal.mode === 'connect' ? (
          <WebhookConnectModal kind={modal.key} onClose={() => setModal(null)} onSaved={load} />
        ) : (
          <WebhookManageModal
            kind={modal.key}
            records={webhookList.filter((wh) => wh.kind === modal.key)}
            onClose={() => setModal(null)}
            onChanged={load}
          />
        )
      )}
    </div>
  )
}

function IntegrationRow({ name, desc, icon, connected, onConnect, onManage }: {
  name: string
  desc: string
  icon: ReactNode
  connected: boolean
  onConnect: () => void
  onManage: () => void
}) {
  return (
    <div className="card-cyber p-4 flex items-center justify-between gap-3">
      <div className="flex items-center gap-4 min-w-0">
        <div className="w-12 h-12 rounded-lg bg-cyber-800 flex items-center justify-center flex-shrink-0">{icon}</div>
        <div className="min-w-0">
          <p className="font-medium text-white">{name}</p>
          <p className="text-xs text-cyber-400">{desc}</p>
        </div>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <span className={`badge-cyber ${connected ? 'bg-neon-green/20 text-neon-green border-neon-green/30' : 'bg-cyber-700 text-cyber-400'}`}>
          {connected ? 'Connected' : 'Available'}
        </span>
        <button onClick={connected ? onManage : onConnect} className={`btn-cyber-${connected ? 'ghost' : 'magenta'} text-sm`}>
          {connected ? 'Manage' : 'Connect'}
        </button>
      </div>
    </div>
  )
}

function ErrorBanner({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center justify-between gap-3">
      <span className="text-sm text-red-400 flex items-center gap-2">
        <AlertCircle className="w-4 h-4 flex-shrink-0" />
        {message}
      </span>
      <button onClick={onRetry} className="btn-cyber-ghost text-xs">Retry</button>
    </div>
  )
}

function ModalShell({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose} role="dialog" aria-modal="true" aria-label={title}>
      <div className="card-cyber w-full max-w-md p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold font-display text-white">{title}</h3>
          <button onClick={onClose} className="p-2 rounded-lg text-cyber-400 hover:text-white hover:bg-cyber-800 transition-colors" aria-label="Close">
            <X className="w-5 h-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

function ProbeMessage({ probe }: { probe: ProbeResult | null }) {
  if (!probe) return null
  return (
    <div className={`flex items-start gap-2 text-sm rounded-lg p-3 border ${probe.ok ? 'bg-neon-green/10 border-neon-green/30 text-neon-green' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
      {probe.ok ? <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" /> : <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />}
      <span>{probe.detail}</span>
    </div>
  )
}

function TokenConnectModal({ platform, onClose, onSaved }: { platform: string; onClose: () => void; onSaved: () => void }) {
  const meta = TOKEN_INTEGRATIONS.find((i) => i.platform === platform)
  const [label, setLabel] = useState('')
  const [token, setToken] = useState('')
  const [endpoint, setEndpoint] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [probe, setProbe] = useState<ProbeResult | null>(null)

  useEffect(() => {
    if (label === '' && meta) setLabel(meta.name)
  }, [label, meta])

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!token.trim()) { setError('Token is required'); return }
    setBusy(true)
    setError(null)
    setProbe(null)
    try {
      const rec = await api<TokenRecord>('/api/v1/admin/tokens', {
        method: 'POST',
        body: JSON.stringify({ name: label.trim() || meta?.name, platform, token: token.trim(), endpoint: endpoint.trim() || undefined }),
      })
      const res = await api<{ result: ProbeResult }>(`/api/v1/admin/tokens/${rec.id}/test`, { method: 'POST' })
      setProbe(res.result)
      if (res.result.ok) {
        await onSaved()
        window.setTimeout(onClose, 1100)
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to save token')
    } finally {
      setBusy(false)
    }
  }

  return (
    <ModalShell title={`Connect ${meta?.name ?? platform}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label-cyber">Connection Name</label>
          <input type="text" value={label} onChange={(e) => setLabel(e.target.value)} className="input-cyber" autoFocus />
        </div>
        <div>
          <label className="label-cyber">{meta?.credentialLabel || 'Access Token'}</label>
          <textarea
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="input-cyber min-h-[90px] resize-y font-mono"
            placeholder={meta?.placeholder || 'ghp_… / glpat-…'}
            spellCheck={false}
            autoComplete="off"
          />
          <p className="text-xs text-cyber-500 mt-1">{meta?.hint}</p>
        </div>
        {meta?.endpointOptional && (
          <div>
            <label className="label-cyber">API Endpoint (optional)</label>
            <input
              type="text"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              className="input-cyber font-mono"
              placeholder={meta?.endpointHint || 'https://…'}
              spellCheck={false}
              autoComplete="off"
            />
            {meta.endpointHint && <p className="text-xs text-cyber-500 mt-1">{meta.endpointHint}</p>}
          </div>
        )}
        {error && <p className="text-sm text-red-400">{error}</p>}
        <ProbeMessage probe={probe} />
        <div className="flex items-center gap-3 pt-1">
          <button type="submit" disabled={busy} className="btn-cyber-magenta flex items-center gap-2">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Save & Validate
          </button>
          <button type="button" onClick={onClose} className="btn-cyber-ghost">Cancel</button>
        </div>
      </form>
    </ModalShell>
  )
}

function TokenManageModal({ platform, records, onClose, onChanged }: {
  platform: string
  records: TokenRecord[]
  onClose: () => void
  onChanged: () => void
}) {
  const meta = TOKEN_INTEGRATIONS.find((i) => i.platform === platform)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, ProbeResult>>({})
  const [error, setError] = useState<string | null>(null)

  async function validate(id: string) {
    setBusyId(id)
    setError(null)
    try {
      const res = await api<{ result: ProbeResult }>(`/api/v1/admin/tokens/${id}/test`, { method: 'POST' })
      setResults((prev) => ({ ...prev, [id]: res.result }))
    } catch (e: any) {
      setError(e?.message || 'Failed to validate')
    } finally {
      setBusyId(null)
    }
  }

  async function disconnect(id: string) {
    setBusyId(id)
    setError(null)
    try {
      await api(`/api/v1/admin/tokens/${id}`, { method: 'DELETE' })
      await onChanged()
    } catch (e: any) {
      setError(e?.message || 'Failed to disconnect')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <ModalShell title={`Manage ${meta?.name ?? platform}`} onClose={onClose}>
      <div className="space-y-3">
        {records.length === 0 && <p className="text-sm text-cyber-400">No {meta?.name ?? platform} tokens configured.</p>}
        {records.map((rec) => (
          <div key={rec.id} className="p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50 space-y-2">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="min-w-0">
                <p className="font-medium text-white flex items-center gap-2">
                  <KeyRound className="w-4 h-4 text-neon-cyan flex-shrink-0" />
                  {rec.name}
                </p>
                <p className="text-xs text-cyber-400 font-mono mt-1">{rec.token_tail || 'No credential saved'}</p>
                {rec.endpoint_set && rec.endpoint_tail && (
                  <p className="text-xs text-cyber-500 font-mono mt-0.5">{rec.endpoint_tail}</p>
                )}
              </div>
              <span className={`badge-cyber ${rec.enabled ? 'bg-neon-green/20 text-neon-green border-neon-green/30' : 'bg-cyber-700 text-cyber-400'} text-xs`}>
                {rec.enabled ? 'Active' : 'Disabled'}
              </span>
            </div>
            <ProbeMessage probe={results[rec.id] ?? null} />
            <div className="flex items-center gap-2">
              <button onClick={() => validate(rec.id)} disabled={busyId !== null} className="btn-cyber-ghost text-sm flex items-center gap-1.5">
                {busyId === rec.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                Validate
              </button>
              <button onClick={() => disconnect(rec.id)} disabled={busyId !== null} className="btn-cyber-ghost text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 border-red-500/30 flex items-center gap-1.5">
                <Trash2 className="w-4 h-4" />
                Disconnect
              </button>
            </div>
          </div>
        ))}
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button onClick={onClose} className="btn-cyber-ghost w-full">Close</button>
      </div>
    </ModalShell>
  )
}

function WebhookConnectModal({ kind, onClose, onSaved }: { kind: string; onClose: () => void; onSaved: () => void }) {
  const meta = WEBHOOK_INTEGRATIONS.find((i) => i.kind === kind)
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [probe, setProbe] = useState<ProbeResult | null>(null)

  useEffect(() => {
    if (name === '' && meta) setName(meta.name)
  }, [name, meta])

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!url.trim()) { setError('Webhook URL is required'); return }
    setBusy(true)
    setError(null)
    setProbe(null)
    try {
      const rec = await api<WebhookRecord & { probe?: ProbeResult }>('/api/v1/integrations/webhooks', {
        method: 'POST',
        body: JSON.stringify({ name: name.trim() || meta?.name, kind, url: url.trim() }),
      })
      setProbe(rec.probe ?? { ok: false, detail: 'No ping result' })
      if (rec.probe?.ok) {
        await onSaved()
        window.setTimeout(onClose, 1100)
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to save webhook')
    } finally {
      setBusy(false)
    }
  }

  return (
    <ModalShell title={`Connect ${meta?.name ?? kind}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label-cyber">Channel Name</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input-cyber" autoFocus />
        </div>
        <div>
          <label className="label-cyber">Incoming Webhook URL</label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="input-cyber font-mono"
            placeholder="https://hooks…"
            spellCheck={false}
            autoComplete="off"
          />
          <p className="text-xs text-cyber-500 mt-1">{meta?.hint}</p>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <ProbeMessage probe={probe} />
        <div className="flex items-center gap-3 pt-1">
          <button type="submit" disabled={busy} className="btn-cyber-magenta flex items-center gap-2">
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Save & Test
          </button>
          <button type="button" onClick={onClose} className="btn-cyber-ghost">Cancel</button>
        </div>
      </form>
    </ModalShell>
  )
}

function WebhookManageModal({ kind, records, onClose, onChanged }: {
  kind: string
  records: WebhookRecord[]
  onClose: () => void
  onChanged: () => void
}) {
  const meta = WEBHOOK_INTEGRATIONS.find((i) => i.kind === kind)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, ProbeResult>>({})
  const [error, setError] = useState<string | null>(null)

  async function validate(id: string) {
    setBusyId(id)
    setError(null)
    try {
      const res = await api<{ result: ProbeResult }>(`/api/v1/integrations/webhooks/${id}/test`, { method: 'POST' })
      setResults((prev) => ({ ...prev, [id]: res.result }))
    } catch (e: any) {
      setError(e?.message || 'Failed to validate')
    } finally {
      setBusyId(null)
    }
  }

  async function disconnect(id: string) {
    setBusyId(id)
    setError(null)
    try {
      await api(`/api/v1/integrations/webhooks/${id}`, { method: 'DELETE' })
      await onChanged()
    } catch (e: any) {
      setError(e?.message || 'Failed to disconnect')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <ModalShell title={`Manage ${meta?.name ?? kind}`} onClose={onClose}>
      <div className="space-y-3">
        {records.length === 0 && <p className="text-sm text-cyber-400">No {meta?.name ?? kind} webhook configured.</p>}
        {records.map((rec) => (
          <div key={rec.id} className="p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50 space-y-2">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="min-w-0">
                <p className="font-medium text-white flex items-center gap-2">
                  <KeyRound className="w-4 h-4 text-neon-cyan flex-shrink-0" />
                  {rec.name}
                </p>
                <p className="text-xs text-cyber-400 font-mono mt-1">{rec.url_tail || 'No URL saved'}</p>
              </div>
              <span className={`badge-cyber ${rec.enabled ? 'bg-neon-green/20 text-neon-green border-neon-green/30' : 'bg-cyber-700 text-cyber-400'} text-xs`}>
                {rec.enabled ? 'Active' : 'Disabled'}
              </span>
            </div>
            <ProbeMessage probe={results[rec.id] ?? null} />
            <div className="flex items-center gap-2">
              <button onClick={() => validate(rec.id)} disabled={busyId !== null} className="btn-cyber-ghost text-sm flex items-center gap-1.5">
                {busyId === rec.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                Test
              </button>
              <button onClick={() => disconnect(rec.id)} disabled={busyId !== null} className="btn-cyber-ghost text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 border-red-500/30 flex items-center gap-1.5">
                <Trash2 className="w-4 h-4" />
                Disconnect
              </button>
            </div>
          </div>
        ))}
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button onClick={onClose} className="btn-cyber-ghost w-full">Close</button>
      </div>
    </ModalShell>
  )
}

// Advanced Section
function AdvancedSection() {
  return (
    <div className="space-y-8">
      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          Developer Options
        </h3>
        <div className="space-y-4">
          {[
            { label: 'Debug Mode', desc: 'Enable debug logging and verbose output', default: false },
            { label: 'API Mocking', desc: 'Use mock responses for API calls', default: false },
            { label: 'Verbose Logging', desc: 'Detailed request/response logging', default: false },
            { label: 'Performance Profiling', desc: 'Collect performance metrics', default: false },
          ].map((opt) => (
            <label key={opt.label} className="flex items-center justify-between p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <div className="flex items-center gap-3">
                <input type="checkbox" className="w-5 h-5 accent-neon-magenta" />
                <div>
                  <p className="font-medium text-white">{opt.label}</p>
                  <p className="text-xs text-cyber-400">{opt.desc}</p>
                </div>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div className="card-cyber p-6 border border-red-500/30">
        <h3 className="text-lg font-bold font-display text-red-400 mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5" />
          Danger Zone
        </h3>
        <div className="space-y-4">
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-red-400">Clear All Data</p>
                <p className="text-xs text-cyber-400">Permanently delete all repositories, findings, and settings</p>
              </div>
              <button className="btn-cyber-ghost text-red-400 hover:text-red-300 border-red-500/30">
                Delete Everything
              </button>
            </div>
          </div>
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-red-400">Reset to Defaults</p>
                <p className="text-xs text-cyber-400">Restore all settings to factory defaults</p>
              </div>
              <button className="btn-cyber-ghost text-red-400 hover:text-red-300 border-red-500/30">
                Reset Settings
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

