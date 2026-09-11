import { useState } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import { useAuth } from '../contexts/AuthContext'
import { useWebSocket } from '../contexts/WebSocketContext'
import MobileNav from './MobileNav'
import {
  LayoutDashboard,
  GitBranch,
  Settings,
  LogOut,
  Sun,
  Moon,
  ChevronDown,
  Terminal,
  Sparkles,
  Brain,
  ShieldCheck,
  Users,
} from 'lucide-react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/repositories', label: 'Repositories', icon: GitBranch },
  { path: '/self-improvement', label: 'Self-Improvement', icon: Brain },
  { path: '/agents', label: 'AI Agents', icon: Users, adminOnly: true },
  { path: '/admin', label: 'Admin Panel', icon: ShieldCheck, adminOnly: true },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export default function Layout() {
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()
  const { isConnected } = useWebSocket()
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-cyber-900 flex flex-col">
      {/* Background grid */}
      <div className="fixed inset-0 bg-grid pointer-events-none opacity-30" />

      {/* ═══ DESKTOP HEADER ═══ */}
      <header className="hidden md:block sticky top-0 z-50 backdrop-blur-md bg-cyber-900/80 border-b border-cyber-700/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="h-16 flex items-center justify-between">
            {/* Logo */}
            <NavLink to="/" className="flex items-center gap-3" aria-label="Git-Fix Home">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 shadow-lg shadow-neon-magenta/20">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <span className="font-bold text-lg text-white tracking-tight font-display">Git-Fix</span>
                <span className="text-xs bg-neon-magenta/10 text-neon-magenta border border-neon-magenta/30 px-2 py-0.5 rounded-full font-mono ml-2">v1.0</span>
              </div>
            </NavLink>

            {/* Desktop Navigation */}
            <nav className="flex items-center space-x-1" aria-label="Main navigation">
              {navItems
                .filter((item) => !item.adminOnly || user?.role === 'admin')
                .map((item) => {
                  const Icon = item.icon
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={({ isActive }) =>
                        `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                          isActive
                            ? 'bg-neon-magenta/10 text-neon-magenta border border-neon-magenta/30'
                            : 'text-cyber-300 hover:text-neon-cyan hover:bg-cyber-800/50'
                        }`
                      }
                    >
                      <Icon className="w-4 h-4" />
                      {item.label}
                    </NavLink>
                  )
                })}
            </nav>

            {/* Right Side Actions */}
            <div className="flex items-center gap-3">
              {/* WebSocket Status */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
                <span className={`w-2 h-2 rounded-full transition-colors ${isConnected ? 'bg-neon-green' : 'bg-neon-amber'}`} />
                <span className="text-xs font-mono text-cyber-400">{isConnected ? 'LIVE' : 'OFFLINE'}</span>
              </div>

              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg bg-cyber-800/50 border border-cyber-700/50 hover:bg-cyber-700/50 hover:border-neon-magenta/50 transition-all duration-200 min-h-[44px] min-w-[44px] flex items-center justify-center cursor-pointer"
                aria-label="Toggle theme"
              >
                {theme === 'dark' ? <Sun className="w-5 h-5 text-neon-amber" /> : <Moon className="w-5 h-5 text-neon-cyan" />}
              </button>

              {/* User Menu */}
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyber-800/50 border border-cyber-700/50 hover:bg-cyber-700/50 hover:border-neon-magenta/50 transition-all duration-200 min-h-[44px] cursor-pointer"
                  aria-label="User menu"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 font-bold text-sm">
                    {user?.username?.charAt(0).toUpperCase() || 'U'}
                  </div>
                  <span className="text-sm font-medium text-cyber-200">{user?.username || 'User'}</span>
                  <ChevronDown className="w-4 h-4 text-cyber-400" />
                </button>

                {userMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                    <div className="absolute right-0 mt-2 w-56 z-50 card-cyber-glow py-2 animate-in fade-in zoom-in-95 duration-200">
                      <div className="px-4 py-3 border-b border-cyber-700/50">
                        <p className="font-medium text-cyber-100">{user?.username}</p>
                        <p className="text-xs text-cyber-400 font-mono">{user?.email}</p>
                        <span className="badge-cyber bg-cyber-700 text-cyber-300 capitalize mt-1 inline-block">{user?.role}</span>
                      </div>
                      <NavLink
                        to="/settings"
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-2 px-4 py-3 text-cyber-300 hover:text-neon-cyan hover:bg-cyber-800/50 transition-colors min-h-[44px]"
                      >
                        <Settings className="w-4 h-4" />
                        Settings
                      </NavLink>
                      <button
                        onClick={() => { logout(); setUserMenuOpen(false); }}
                        className="flex items-center gap-2 w-full px-4 py-3 text-red-400 hover:text-red-300 hover:bg-cyber-800/50 transition-colors min-h-[44px] cursor-pointer"
                      >
                        <LogOut className="w-4 h-4" />
                        Logout
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* ═══ MOBILE HEADER (compact) ═══ */}
      <header className="md:hidden sticky top-0 z-50 backdrop-blur-md bg-cyber-900/90 border-b border-cyber-700/50">
        <div className="flex items-center justify-between px-4 h-14">
          {/* Logo compact */}
          <NavLink to="/" className="flex items-center gap-2" aria-label="Git-Fix Home">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 shadow-lg shadow-neon-magenta/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <span className="font-bold text-base text-white tracking-tight font-display">Git-Fix</span>
          </NavLink>

          {/* Right actions: WS status + theme + avatar */}
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-neon-green' : 'bg-neon-amber'}`} />
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-cyber-800/50 transition-all duration-200 min-h-[44px] min-w-[44px] flex items-center justify-center cursor-pointer"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun className="w-5 h-5 text-neon-amber" /> : <Moon className="w-5 h-5 text-neon-cyan" />}
            </button>
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="w-9 h-9 rounded-full bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 font-bold text-sm min-h-[44px] min-w-[44px] cursor-pointer"
                aria-label="User menu"
              >
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </button>
              {userMenuOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                  <div className="absolute right-0 mt-2 w-48 z-50 card-cyber-glow py-2 animate-in fade-in zoom-in-95 duration-200">
                    <div className="px-4 py-3 border-b border-cyber-700/50">
                      <p className="font-medium text-cyber-100 text-sm">{user?.username}</p>
                      <span className="badge-cyber bg-cyber-700 text-cyber-300 capitalize mt-1 inline-block text-[10px]">{user?.role}</span>
                    </div>
                    <button
                      onClick={() => { logout(); setUserMenuOpen(false); }}
                      className="flex items-center gap-2 w-full px-4 py-3 text-red-400 hover:text-red-300 hover:bg-cyber-800/50 transition-colors min-h-[44px] cursor-pointer"
                    >
                      <LogOut className="w-4 h-4" />
                      Logout
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content — clearance for mobile bottom nav */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 md:py-8 pb-mobile-nav">
        <Outlet />
      </main>

      {/* Footer — hidden on mobile (bottom nav replaces it) */}
      <footer className="hidden md:block bg-cyber-900 border-t border-cyber-700/50 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-cyber-400">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-neon-magenta" />
              <span className="text-cyber-300 font-semibold font-display">Git-Fix</span>
              <span className="hidden sm:inline">• Cyberpunk Code Review Engine</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-cyber-500 font-mono">No external dependencies beyond open standards</span>
              <NavLink to="/" className="text-neon-magenta hover:underline">Back to top</NavLink>
            </div>
          </div>
        </div>
      </footer>

      {/* Mobile Bottom Navigation */}
      <MobileNav />
    </div>
  )
}
