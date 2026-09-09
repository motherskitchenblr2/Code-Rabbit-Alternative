import React from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, Terminal, Home, Search, GitBranch, RefreshCw, ExternalLink } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-cyber-900 flex items-center justify-center p-4">
      {/* Background grid */}
      <div className="fixed inset-0 bg-grid pointer-events-none opacity-30" />

      <div className="relative z-10 text-center max-w-md w-full">
        {/* Logo */}
        <div className="mb-12">
          <Link to="/" className="inline-flex items-center justify-center gap-3 mb-8">
            <div className="h-20 w-20 rounded-2xl bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 shadow-[0_0_60px_rgba(255,0,255,0.4)] animate-pulse-slow">
              <Sparkles className="w-12 h-12" />
            </div>
          </Link>

          {/* 404 Code */}
          <div className="mb-8">
            <span className="text-9xl font-bold font-display text-neon-magenta font-mono tracking-wider">404</span>
            <div className="h-1 w-32 bg-gradient-to-r from-neon-magenta to-neon-cyan mx-auto mt-4 rounded-full" />
          </div>

          <h1 className="text-3xl font-bold font-display text-white mb-4">Sector Not Found</h1>
          <p className="text-cyber-400 text-lg mb-8 max-w-md mx-auto leading-relaxed">
            The sector you're looking for has been lost in the digital void. 
            It may have been moved, deleted, or never existed in this timeline.
          </p>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
            <Link to="/" className="btn-cyber-magenta flex items-center gap-2 px-8 py-3 text-lg">
              <Home className="w-5 h-5" />
              Return to Terminal
            </Link>
            <Link to="/repositories" className="btn-cyber-cyan flex items-center gap-2 px-8 py-3 text-lg">
              <GitBranch className="w-5 h-5" />
              Browse Repositories
            </Link>
          </div>

          {/* Search */}
          <div className="mb-12">
            <p className="text-cyber-500 text-sm mb-4">Or search for a sector:</p>
            <form className="flex flex-col sm:flex-row items-center justify-center gap-3 max-w-md mx-auto">
              <div className="relative w-full sm:w-80">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-cyber-500" />
                <input
                  type="text"
                  placeholder="Search sectors..."
                  className="input-cyber pl-10"
                  placeholder="Enter sector coordinates..."
                />
              </div>
              <button type="submit" className="btn-cyber-magenta">
                <Search className="w-4 h-4 mr-2" />
                Scan
              </button>
            </form>
          </div>

          {/* Quick Links */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-2xl mx-auto mb-12">
            <Link to="/" className="card-cyber p-6 hover:border-neon-magenta/30 transition-all group">
              <Terminal className="w-8 h-8 text-neon-cyan mx-auto mb-3 group-hover:text-neon-magenta transition-colors" />
              <h3 className="font-bold text-white mb-1">Dashboard</h3>
              <p className="text-xs text-cyber-400">System overview & metrics</p>
            </Link>
            <Link to="/repositories" className="card-cyber p-6 hover:border-neon-magenta/30 transition-all group">
              <GitBranch className="w-8 h-8 text-neon-magenta mx-auto mb-3 group-hover:text-neon-cyan transition-colors" />
              <h3 className="font-bold text-white mb-1">Repositories</h3>
              <p className="text-xs text-cyber-400">Browse all sectors</p>
            </Link>
            <Link to="/settings" className="card-cyber p-6 hover:border-neon-magenta/30 transition-all group">
              <Sparkles className="w-8 h-8 text-neon-amber mx-auto mb-3 group-hover:text-neon-cyan transition-colors" />
              <h3 className="font-bold text-white mb-1">Settings</h3>
              <p className="text-xs text-cyber-400">Configure your terminal</p>
            </Link>
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="card-cyber p-6 hover:border-neon-magenta/30 transition-all group">
              <ExternalLink className="w-8 h-8 text-neon-green mx-auto mb-3 group-hover:text-neon-cyan transition-colors" />
              <h3 className="font-bold text-white mb-1">GitHub</h3>
              <p className="text-xs text-cyber-400">View source code</p>
            </a>
          </div>

          {/* System Status */}
          <div className="card-cyber p-6 max-w-md mx-auto mb-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold font-display text-white flex items-center gap-2">
                <Terminal className="w-5 h-5 text-neon-cyan" />
                System Diagnostics
              </h3>
              <span className="flex items-center gap-1 text-xs font-mono text-neon-green">
                <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                OPERATIONAL
              </span>
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="p-3 rounded-lg bg-cyber-800/50">
                <p className="text-2xl font-bold font-display text-neon-green">99.9%</p>
                <p className="text-xs text-cyber-400">Uptime</p>
              </div>
              <div className="p-3 rounded-lg bg-cyber-800/50">
                <p className="text-2xl font-bold font-display text-neon-cyan"><50ms</p>
                <p className="text-xs text-cyber-400">Latency</p>
              </div>
              <div className="p-3 rounded-lg bg-cyber-800/50">
                <p className="text-2xl font-bold font-display text-neon-magenta">0</p>
                <p className="text-xs text-cyber-400">Errors</p>
              </div>
            </div>
          </div>

          {/* Easter Egg */}
          <details className="mt-8 group">
            <summary className="cursor-pointer text-cyber-500 hover:text-neon-magenta transition-colors flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 group-hover:animate-spin transition-transform" />
              <span className="text-sm font-mono">Access Classified Logs</span>
            </summary>
            <div className="mt-4 p-4 bg-cyber-900/50 rounded-lg border border-cyber-700/50 font-mono text-xs text-cyber-400 overflow-x-auto">
              <pre>{`[SYSTEM] Git-Fix v1.0.0 initialized
[SECURITY] All sectors encrypted with AES-256
[NETWORK] Mesh topology active - 47 nodes
[AI] Multi-agent ensemble: SECURE
[PIPELINE] 5-stage validation: ACTIVE
[STORAGE] Qdrant vector index: 2.4M embeddings
[QUEUE] Redis cluster: 3 nodes healthy
[DB] PostgreSQL 15: PRIMARY + 2 REPLICAS
[CACHE] Redis 7: 256MB LRU cache
[MONITORING] Prometheus + Grafana: ONLINE
[ALERTS] PagerDuty + Slack: CONFIGURED

>_ ACCESS GRANTED - Welcome back, Operator`}</pre>
            </div>
          </details>

          {/* Footer */}
          <div className="mt-12 text-cyber-500 text-xs">
            <p>Git-Fix v1.0.0-cyberpunk | Built with ⚡️ in the digital underground</p>
            <p className="mt-2">Error code: SECTOR_NOT_FOUND | Timestamp: {new Date().toISOString()}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default NotFound