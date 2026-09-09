import React, { useState } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import { useAuth } from '../contexts/AuthContext'
import { useWebSocket } from '../contexts/WebSocketContext'
import {
  LayoutDashboard,
  GitBranch,
  Settings,
  LogOut,
  Sun,
  Moon,
  Wifi,
  WifiOff,
  Menu,
  X,
  ChevronDown,
  User,
  Terminal,
  Sparkles,
} from 'lucide-react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/repositories', label: 'Repositories', icon: GitBranch },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export default function Layout() {
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()
  const { isConnected } = useWebSocket()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-cyber-900 flex flex-col">
      {/* Background grid */}
      <div className="fixed inset-0 bg-grid pointer-events-none opacity-30" />

      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-cyber-900/80 border-b border-cyber-700/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="h-16 flex items-center justify-between">
            {/* Logo */}
            <NavLink to="/" className="flex items-center gap-3" aria-label="Git-Fix Home">
              <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 shadow-lg shadow-neon-magenta/20">
                <Sparkles className="w-6 h-6" />
              </div>
              <div className="hidden sm:block">
                <span className="font-bold text-lg text-white tracking-tight font-display">Git-Fix</span>
                <span className="text-xs bg-neon-magenta/10 text-neon-magenta border border-neon-magenta/30 px-2 py-0.5 rounded-full font-mono">v1.0</span>
              </div>
            </NavLink>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-1" aria-label="Main navigation">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path))
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
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyber-800/50 border border-cyber-700/50">
                <span className={`w-2 h-2 rounded-full transition-colors ${isConnected ? 'bg-neon-green' : 'bg-neon-amber'}`} />
                <span className="text-xs font-mono text-cyber-400">{isConnected ? 'LIVE' : 'OFFLINE'}</span>
              </div>

              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg bg-cyber-800/50 border border-cyber-700/50 hover:bg-cyber-700/50 hover:border-neon-magenta/50 transition-all duration-200"
                aria-label="Toggle theme"
              >
                {theme === 'dark' ? <Sun className="w-5 h-5 text-neon-amber" /> : <Moon className="w-5 h-5 text-neon-cyan" />}
              </button>

              {/* User Menu */}
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-cyber-800/50 border border-cyber-700/50 hover:bg-cyber-700/50 hover:border-neon-magenta/50 transition-all duration-200"
                  aria-label="User menu"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 font-bold text-sm">
                    {user?.username?.charAt(0).toUpperCase() || 'U'}
                  </div>
                  <span className="hidden sm:block text-sm font-medium text-cyber-200">{user?.username || 'User'}</span>
                  <ChevronDown className="w-4 h-4 text-cyber-400" />
                </button>

                {userMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setUserMenuOpen(false)} />
                    <div className="absolute right-0 mt-2 w-56 z-50 card-cyber-glow py-2 animate-in fade-in zoom-in-95 duration-200">
                      <div className="px-4 py-3 border-b border-cyber-700/50">
                        <p className="font-medium text-cyber-100">{user?.username}</p>
                        <p className="text-xs text-cyber-400 font-mono">{user?.email}</p>
                        <span className="badge-cyber bg-cyber-700 text-cyber-300 capitalize">{user?.role}</span>
                      </div>
                      <NavLink
                        to="/settings"
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-2 px-4 py-2 text-cyber-300 hover:text-neon-cyan hover:bg-cyber-800/50 transition-colors"
                      >
                        <Settings className="w-4 h-4" />
                        Settings
                      </NavLink>
                      <button
                        onClick={() => { logout(); setUserMenuOpen(false); }}
                        className="flex items-center gap-2 w-full px-4 py-2 text-red-400 hover:text-red-300 hover:bg-cyber-800/50 transition-colors"
                      >
                        <LogOut className="w-4 h-4" />
                        Logout
                      </button>
                    </div>
                  </>
                )}
              </div>

              {/* Mobile Menu Button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden p-2 rounded-lg bg-cyber-800/50 border border-cyber-700/50 hover:bg-cyber-700/50"
                aria-label="Toggle menu"
              >
                {mobileMenuOpen ? <X className="w-6 h-6 text-cyber-200" /> : <Menu className="w-6 h-6 text-cyber-200" />}
              </button>
            </div>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <div className="md:hidden card-cyber mt-4 animate-in slide-in-from-top-2 duration-200">
              <nav className="py-2 space-y-1">
                {navItems.map((item) => {
                  const Icon = item.icon
                  const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path))
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded-lg text-base font-medium transition-all ${
                        isActive
                          ? 'bg-neon-magenta/10 text-neon-magenta border-l-4 border-neon-magenta'
                          : 'text-cyber-300 hover:text-neon-cyan hover:bg-cyber-800/50'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                      {item.label}
                    </NavLink>
                  )
                })}
              </nav>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-cyber-900 border-t border-cyber-700/50 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-cyber-400">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-neon-magenta" />
              <span className="text-cyber-300 font-semibold font-display">Git-Fix</span>
              <span>• Cyberpunk Code Review Engine</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-cyber-500 font-mono">No external dependencies beyond open standards</span>
              <NavLink to="/" className="text-neon-magenta hover:underline">Back to top</NavLink>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default Layout