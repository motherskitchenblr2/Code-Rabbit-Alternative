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
  Plug,
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

// Security Section
function SecuritySection() {
  const [twoFA, setTwoFA] = useState(false)
  const [sessions] = useState([
    { id: '1', device: 'Chrome on macOS', location: 'San Francisco, US', current: true, lastActive: 'Now' },
    { id: '2', device: 'Firefox on Linux', location: 'New York, US', current: false, lastActive: '2 days ago' },
    { id: '3', device: 'Safari on iOS', location: 'London, UK', current: false, lastActive: '1 week ago' },
  ])

  return (
    <div className="space-y-8">
      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          Two-Factor Authentication
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-white">Enable 2FA</p>
            <p className="text-cyber-400 text-sm">Add an extra layer of security to your account</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" checked={twoFA} onChange={(e) => setTwoFA(e.target.checked)} className="sr-only peer" />
            <div className="w-11 h-6 bg-cyber-700 peer-focus-visible:ring-2 peer-focus-visible:ring-neon-cyan rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-neon-magenta after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-neon-magenta"></div>
          </label>
        </div>
      </div>

      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          API Keys
        </h3>
        <p className="text-cyber-400 mb-4">Manage API keys for CI/CD and integrations</p>
        <button className="btn-cyber-magenta">
          <Plus className="w-4 h-4 mr-2" />
          Generate New API Key
        </button>
      </div>

      <div className="card-cyber p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold font-display text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-neon-magenta" />
            Active Sessions
          </h3>
          <button className="btn-cyber-ghost text-sm">Revoke All</button>
        </div>
        <div className="space-y-3">
          {sessions.map((session) => (
            <div key={session.id} className="flex items-center justify-between p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-cyber-800 flex items-center justify-center">
                  <Terminal className="w-5 h-5 text-neon-cyan" />
                </div>
                <div>
                  <p className="font-medium text-white">{session.device}</p>
                  <p className="text-xs text-cyber-400">{session.location} • {session.lastActive}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {session.current && <span className="badge-cyber bg-neon-green/20 text-neon-green border-neon-green/30 text-xs">Current</span>}
                {!session.current && (
                  <button className="text-red-400 hover:text-red-300 text-sm font-mono">Revoke</button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card-cyber p-6">
        <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-neon-magenta" />
          Password
        </h3>
        <button className="btn-cyber-magenta">
          Change Password
        </button>
      </div>
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

const TOKEN_INTEGRATIONS: Array<{ platform: string; name: string; desc: string; hint: string; icon: ReactNode }> = [
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
    icon: <GitBranch className="w-6 h-6 text-neon-cyan" />,
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

const COMING_SOON = ['Jira', 'Linear', 'Datadog', 'Sentry', 'PostgreSQL', 'Redis', 'Qdrant', 'Prometheus']

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

          <div className="card-cyber p-4 border border-dashed border-cyber-700/50">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-cyber-800/50 flex items-center justify-center flex-shrink-0">
                <Plug className="w-6 h-6 text-cyber-500" />
              </div>
              <div>
                <p className="font-medium text-white">More integrations coming soon</p>
                <p className="text-xs text-cyber-400 mt-0.5">{COMING_SOON.join(' · ')}</p>
              </div>
            </div>
          </div>
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
        body: JSON.stringify({ name: label.trim() || meta?.name, platform, token: token.trim() }),
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
          <label className="label-cyber">Access Token</label>
          <textarea
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="input-cyber min-h-[90px] resize-y font-mono"
            placeholder="ghp_… / glpat-…"
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
                <p className="text-xs text-cyber-400 font-mono mt-1">{rec.token_tail || 'No token saved'}</p>
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

