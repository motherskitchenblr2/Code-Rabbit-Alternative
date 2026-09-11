import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Plus,
  Search,
  GitBranch,
  Lock,
  Globe,
  ChevronDown,
  ChevronUp,
  Settings,
  Eye,
  ExternalLink,
} from 'lucide-react'

// Types
interface Repository {
  id: string
  name: string
  full_name: string
  description: string
  private: boolean
  language: string
  stars: number
  forks: number
  open_prs: number
  last_scan: string
  status: 'active' | 'idle' | 'error'
  created_at: string
}

const repositories: Repository[] = [
  { id: '1', name: 'gitfix-core', full_name: 'org/gitfix-core', description: 'Core Git-Fix engine with 5-stage pipeline', private: true, language: 'Python', stars: 142, forks: 28, open_prs: 5, last_scan: '2 min ago', status: 'active', created_at: '2024-01-01' },
  { id: '2', name: 'gitfix-frontend', full_name: 'org/gitfix-frontend', description: 'Cyberpunk dashboard with real-time updates', private: true, language: 'TypeScript', stars: 89, forks: 15, open_prs: 3, last_scan: '15 min ago', status: 'active', created_at: '2024-01-05' },
  { id: '3', name: 'gitfix-cli', full_name: 'org/gitfix-cli', description: 'CLI tool for Git-Fix integration', private: false, language: 'Go', stars: 256, forks: 42, open_prs: 2, last_scan: '1 hour ago', status: 'idle', created_at: '2024-01-10' },
  { id: '4', name: 'gitfix-hooks', full_name: 'org/gitfix-hooks', description: 'Git hooks integration package', private: true, language: 'Python', stars: 67, forks: 12, open_prs: 1, last_scan: '3 hours ago', status: 'active', created_at: '2024-01-12' },
  { id: '5', name: 'gitfix-api', full_name: 'org/gitfix-api', description: 'REST API with WebSocket support', private: true, language: 'Python', stars: 134, forks: 23, open_prs: 4, last_scan: '5 min ago', status: 'active', created_at: '2024-01-08' },
  { id: '6', name: 'gitfix-docs', full_name: 'org/gitfix-docs', description: 'Documentation and guides', private: false, language: 'Markdown', stars: 45, forks: 8, open_prs: 0, last_scan: '2 days ago', status: 'idle', created_at: '2024-01-15' },
]

export default function Repositories() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'active' | 'idle' | 'error'>('all')
  const [sortBy, setSortBy] = useState<'name' | 'last_scan' | 'stars' | 'open_prs'>('last_scan')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [, setShowAddModal] = useState(false)

  const filteredRepos = repositories
    .filter(repo => {
      if (filter !== 'all' && repo.status !== filter) return false
      if (search && !repo.name.toLowerCase().includes(search.toLowerCase()) &&
          !repo.full_name.toLowerCase().includes(search.toLowerCase()) &&
          !repo.description.toLowerCase().includes(search.toLowerCase())) {
        return false
      }
      return true
    })
    .sort((a, b) => {
      const aVal = a[sortBy]
      const bVal = b[sortBy]
      const cmp =
        typeof aVal === 'number' && typeof bVal === 'number'
          ? aVal - bVal
          : String(aVal).localeCompare(String(bVal))
      return sortOrder === 'asc' ? cmp : -cmp
    })

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold font-display text-white flex items-center gap-3">
            <span className="text-neon-magenta">{'>_'}</span> Repositories
          </h1>
          <p className="text-cyber-400 mt-1">Manage and monitor your code repositories</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn-cyber-magenta flex items-center gap-2 self-start"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden md:inline">Add Repository</span>
          <span className="md:hidden">Add Repo</span>
        </button>
      </div>

      {/* Toolbar */}
      <div className="card-cyber p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-cyber-500" />
            <input
              type="text"
              placeholder="Search repositories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-cyber pl-10"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as any)}
              className="input-cyber py-2"
            >
              <option value="all">All Status</option>
              <option value="active">Active</option>
              <option value="idle">Idle</option>
              <option value="error">Error</option>
            </select>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="input-cyber py-2 w-40"
            >
              <option value="last_scan">Last Scan</option>
              <option value="name">Name</option>
              <option value="stars">Stars</option>
              <option value="open_prs">Open PRs</option>
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              className="p-2 rounded-lg bg-cyber-800/50 border border-cyber-700/50 hover:bg-cyber-700/50 transition-colors"
              aria-label={sortOrder === 'asc' ? 'Sort descending' : 'Sort ascending'}
            >
              {sortOrder === 'asc' ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile repository cards */}
      <div className="grid grid-cols-1 gap-3 md:hidden">
        {filteredRepos.map((repo) => (
          <div key={repo.id} className="card-cyber p-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-cyber-800 flex items-center justify-center flex-shrink-0">
                <GitBranch className="w-5 h-5 text-neon-cyan" />
              </div>
              <div className="flex-1 min-w-0">
                <Link to={`/repositories/${repo.id}`} className="block">
                  <p className="font-medium text-white truncate">{repo.name}</p>
                  <p className="text-xs text-cyber-400 font-mono flex items-center gap-1 mt-0.5">
                    {repo.private ? <Lock className="w-3 h-3" /> : <Globe className="w-3 h-3" />}
                    {repo.full_name}
                  </p>
                </Link>
                <p className="text-xs text-cyber-300 mt-2 line-clamp-2">{repo.description}</p>
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  <span className="text-xs px-2 py-1 bg-cyber-800 rounded text-cyber-300 font-mono">{repo.language}</span>
                  <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-mono ${
                    repo.status === 'active' ? 'bg-neon-green/20 text-neon-green border border-neon-green/30' :
                    repo.status === 'idle' ? 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30' :
                    'bg-red-500/20 text-red-400 border border-red-500/30'
                  }`}>
                    {repo.status.charAt(0).toUpperCase() + repo.status.slice(1)}
                  </span>
                  <span className="text-xs text-cyber-400 font-mono">{repo.last_scan}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-cyber-700/50">
              <Link to={`/repositories/${repo.id}`} className="btn-cyber-sm flex-1 flex items-center justify-center gap-1.5 bg-cyber-800/50 border border-cyber-700/50 text-cyber-200 hover:bg-cyber-700/50 transition-colors">
                <Eye className="w-4 h-4" />
                View
              </Link>
              <Link to={`/repositories/${repo.id}/settings`} className="btn-cyber-sm flex-1 flex items-center justify-center gap-1.5 bg-cyber-800/50 border border-cyber-700/50 text-cyber-200 hover:bg-cyber-700/50 transition-colors">
                <Settings className="w-4 h-4" />
                Configure
              </Link>
            </div>
          </div>
        ))}
        {filteredRepos.length === 0 && (
          <div className="card-cyber p-10 text-center">
            <GitBranch className="w-16 h-16 mx-auto mb-4 text-cyber-700" />
            <h3 className="text-lg font-medium text-cyber-300 mb-2">No repositories found</h3>
            <p className="text-cyber-500 mb-4">Try adjusting your search or filters</p>
            <button className="btn-cyber-magenta" onClick={() => { setSearch(''); setFilter('all'); }}>
              Clear Filters
            </button>
          </div>
        )}
      </div>

      {/* Desktop repositories table */}
      <div className="card-cyber overflow-hidden hidden md:block">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-cyber-700/50">
                <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Repository</th>
                <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider hidden md:table-cell">Description</th>
                <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider hidden md:table-cell">Language</th>
                <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider hidden lg:table-cell">Stars</th>
                <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider hidden lg:table-cell">Forks</th>
                <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider hidden lg:table-cell">Open PRs</th>
                <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Last Scan</th>
                <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-mono text-cyber-400 uppercase tracking-wider">Visibility</th>
                <th className="px-4 py-3 text-right text-xs font-mono text-cyber-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredRepos.map((repo) => (
                <tr key={repo.id} className="border-b border-cyber-800/50 hover:bg-cyber-800/30 transition-colors">
                  <td className="px-4 py-4">
                    <Link to={`/repositories/${repo.id}`} className="flex items-center gap-3 group">
                      <div className="w-10 h-10 rounded-lg bg-cyber-800 flex items-center justify-center group-hover:bg-neon-magenta/20 transition-colors">
                        <GitBranch className="w-5 h-5 text-neon-cyan" />
                      </div>
                      <div>
                        <p className="font-medium text-white group-hover:text-neon-cyan transition-colors">{repo.name}</p>
                        <p className="text-xs text-cyber-400 truncate max-w-xs">{repo.full_name}</p>
                      </div>
                    </Link>
                  </td>
                  <td className="px-4 py-4 hidden md:table-cell">
                    <p className="text-cyber-300 truncate max-w-md">{repo.description}</p>
                  </td>
                  <td className="px-4 py-4 hidden md:table-cell">
                    <span className="text-xs px-2 py-1 bg-cyber-800 rounded text-cyber-300 font-mono">{repo.language}</span>
                  </td>
                  <td className="px-4 py-4 hidden lg:table-cell">
                    <span className="text-cyber-300 font-mono flex items-center gap-1">{repo.stars.toLocaleString()}</span>
                  </td>
                  <td className="px-4 py-4 hidden lg:table-cell">
                    <span className="text-cyber-300 font-mono">{repo.forks.toLocaleString()}</span>
                  </td>
                  <td className="px-4 py-4 hidden lg:table-cell">
                    <span className="text-cyber-300 font-mono">{repo.open_prs}</span>
                  </td>
                  <td className="px-4 py-4">
                    <span className="text-xs text-cyber-400 font-mono">{repo.last_scan}</span>
                  </td>
                  <td className="px-4 py-4">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-mono ${
                      repo.status === 'active' ? 'bg-neon-green/20 text-neon-green border border-neon-green/30' :
                      repo.status === 'idle' ? 'bg-neon-amber/20 text-neon-amber border border-neon-amber/30' :
                      'bg-red-500/20 text-red-400 border border-red-500/30'
                    }`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${repo.status === 'active' ? 'bg-neon-green' : repo.status === 'idle' ? 'bg-neon-amber' : 'bg-red-500'}`} />
                      {repo.status.charAt(0).toUpperCase() + repo.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-mono ${
                      repo.private ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-neon-green/20 text-neon-green border border-neon-green/30'
                    }`}>
                      {repo.private ? <Lock className="w-3 h-3" /> : <Globe className="w-3 h-3" />}
                      {repo.private ? 'Private' : 'Public'}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Link to={`/repositories/${repo.id}`} className="p-2 rounded-lg bg-cyber-800/50 hover:bg-neon-cyan/10 hover:border-neon-cyan/30 border border-cyber-700/50 transition-colors" aria-label="View">
                        <Eye className="w-4 h-4 text-cyber-400" />
                      </Link>
                      <Link to={`/repositories/${repo.id}/settings`} className="p-2 rounded-lg bg-cyber-800/50 hover:bg-neon-amber/10 hover:border-neon-amber/30 border border-cyber-700/50 transition-colors" aria-label="Settings">
                        <Settings className="w-4 h-4 text-cyber-400" />
                      </Link>
                      <a href={`https://github.com/${repo.full_name}`} target="_blank" rel="noopener noreferrer" className="p-2 rounded-lg bg-cyber-800/50 hover:bg-neon-magenta/10 hover:border-neon-magenta/30 border border-cyber-700/50 transition-colors" aria-label="View on GitHub">
                        <ExternalLink className="w-4 h-4 text-cyber-400" />
                      </a>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredRepos.length === 0 && (
          <div className="p-12 text-center">
            <GitBranch className="w-16 h-16 mx-auto mb-4 text-cyber-700" />
            <h3 className="text-lg font-medium text-cyber-300 mb-2">No repositories found</h3>
            <p className="text-cyber-500 mb-4">Try adjusting your search or filters</p>
            <button className="btn-cyber-magenta" onClick={() => { setSearch(''); setFilter('all'); }}>
              Clear Filters
            </button>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-cyber-400 text-sm">Showing {filteredRepos.length} of {repositories.length} repositories</p>
        <div className="flex items-center gap-2">
          <button className="p-2 rounded-lg bg-cyber-800/50 border border-cyber-700/50 hover:bg-cyber-700/50 disabled:opacity-50" disabled>← Previous</button>
          <button className="p-2 rounded-lg bg-cyber-800/50 border border-cyber-700/50 hover:bg-cyber-700/50 disabled:opacity-50" disabled>Next →</button>
        </div>
      </div>
    </div>
  )
}

