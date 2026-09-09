import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useWebSocket } from '../contexts/WebSocketContext'
import {
  User,
  Shield,
  Bell,
  Palette,
  Globe,
  Key,
  Terminal,
  Save,
  CheckCircle,
  AlertCircle,
  Sparkles,
  GitBranch,
  Server,
  Database,
  Wifi,
  WifiOff,
} from 'lucide-react'

export default function Settings() {
  const { user, logout } = useAuth()
  const { theme, toggleTheme, setTheme } = useTheme()
  const { isConnected } = useWebSocket()

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
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">>_</span> Settings
          </h1>
          <p className="text-cyber-400 mt-1">Configure your Git-Fix experience</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-cyber-magenta flex items-center gap-2"
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
        {/* Sidebar Navigation */}
        <div className="flex">
          <nav className="w-56 border-r border-cyber-700/50 p-4 space-y-1" aria-label="Settings sections">
            {sections.map((section) => {
              const Icon = section.icon
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id as any)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left text-sm font-medium transition-all ${
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
            {activeSection === 'appearance' && <AppearanceSection theme={theme} setTheme={setTheme} />}
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
  const [formData, setFormData] = useState({
    username: user?.username || '',
    email: user?.email || '',
    fullName: '',
    bio: '',
    company: '',
    location: '',
    website: '',
  })

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-6">
        <div className="w-24 h-24 rounded-xl bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 font-bold text-2xl">
          {user?.username?.charAt(0).toUpperCase() || 'U'}
        </div>
        <div>
          <h3 className="text-2xl font-bold font-display text-white">{user?.username}</h3>
          <p className="text-cyber-400">{user?.email}</p>
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
        <button className="btn-cyber-ghost text-red-400 hover:text-red-300 hover:bg-red-500/10 border-red-500/30">
          <span className="w-4 h-4 mr-2">🗑</span>
          Delete Account
        </button>
      </div>
    </div>
  )
}

// Security Section
function SecuritySection() {
  const [twoFA, setTwoFA] = useState(false)
  const [sessions, setSessions] = useState([
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
        </h3>
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

  const toggle = (key: string) => {
    setPrefs(prev => ({ ...prev, [key]: !prev[key] }))
  }

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
function AppearanceSection({ theme, setTheme }: { theme: 'dark' | 'light'; setTheme: (t: 'dark' | 'light') => void }) {
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
                <span className="text-3xl">{t === 'dark' ? '🌙' : '☀️'}</span>
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
        <div className="grid grid-cols-4 gap-4">
          {[
            { name: 'Magenta', value: '#ff00ff', css: 'neon-magenta' },
            { name: 'Cyan', value: '#00ffff', css: 'neon-cyan' },
            { name: 'Amber', value: '#ff8c00', css: 'neon-amber' },
            { name: 'Green', value: '#00ff00', css: 'neon-green' },
          ].map((color) => (
            <button
              key={color.name}
              className={`p-4 rounded-xl border-2 transition-all ${theme === 'dark' ? 'bg-cyber-800' : 'bg-white'}`}
            >
              <div className="w-full h-12 rounded-lg mb-3" style={{ backgroundColor: color.value }} />
              <p className="font-medium text-white capitalize">{color.name}</p>
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

// Integrations Section
function IntegrationsSection() {
  const integrations = [
    { name: 'GitHub', connected: true, desc: 'Source control & PR reviews', icon: GitBranch },
    { name: 'GitLab', connected: false, desc: 'Alternative Git hosting', icon: GitBranch },
    { name: 'Slack', connected: false, desc: 'Team notifications', icon: Globe },
    { name: 'Discord', connected: false, desc: 'Community notifications', icon: Globe },
    { name: 'Jira', connected: false, desc: 'Issue tracking', icon: Globe },
    { name: 'Linear', connected: false, desc: 'Project management', icon: Globe },
    { name: 'Datadog', connected: false, desc: 'Monitoring & APM', icon: Server },
    { name: 'Sentry', connected: false, desc: 'Error tracking', icon: Bug },
    { name: 'PostgreSQL', connected: false, desc: 'Primary database', icon: Database },
    { name: 'Redis', connected: false, desc: 'Cache & queue', icon: Database },
    { name: 'Qdrant', connected: false, desc: 'Vector database', icon: Database },
    { name: 'Prometheus', connected: false, desc: 'Metrics & alerting', icon: Server },
  ]

  return (
    <div className="space-y-4">
      {integrations.map((integration) => (
        <div key={integration.name} className="card-cyber p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-cyber-800 flex items-center justify-center">
              <integration.icon className="w-6 h-6 text-neon-cyan" />
            </div>
            <div>
              <p className="font-medium text-white">{integration.name}</p>
              <p className="text-xs text-cyber-400">{integration.desc}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`badge-cyber ${integration.connected ? 'bg-neon-green/20 text-neon-green border-neon-green/30' : 'bg-cyber-700 text-cyber-400'}`}>
              {integration.connected ? 'Connected' : 'Available'}
            </span>
            <button className={`btn-cyber-${integration.connected ? 'ghost' : 'magenta'} text-sm`}>
              {integration.connected ? 'Manage' : 'Connect'}
            </button>
          </div>
        </div>
      ))}
    </div>
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

export default Settings