import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  LayoutDashboard,
  GitBranch,
  Brain,
  Users,
  ShieldCheck,
  Settings,
} from 'lucide-react'

interface NavItem {
  path: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  adminOnly?: boolean
}

const navItems: NavItem[] = [
  { path: '/', label: 'Home', icon: LayoutDashboard },
  { path: '/repositories', label: 'Repos', icon: GitBranch },
  { path: '/self-improvement', label: 'AI', icon: Brain },
  { path: '/agents', label: 'Agents', icon: Users, adminOnly: true },
  { path: '/admin', label: 'Admin', icon: ShieldCheck, adminOnly: true },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export default function MobileNav() {
  const { user } = useAuth()
  const location = useLocation()

  const visible = navItems.filter((item) => !item.adminOnly || user?.role === 'admin')

  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-cyber-900/95 backdrop-blur-md border-t border-cyber-700/60"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      aria-label="Mobile navigation"
    >
      <div className="flex items-stretch">
        {visible.map((item) => {
          const Icon = item.icon
          const isActive =
            item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path)
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={`flex flex-1 flex-col items-center justify-center gap-0.5 py-2 transition-colors min-h-[56px] ${
                isActive
                  ? 'text-neon-magenta'
                  : 'text-cyber-500 active:text-cyber-300'
              }`}
              aria-label={item.label}
            >
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-200 ${
                  isActive
                    ? 'bg-neon-magenta/15 shadow-[0_0_12px_rgba(255,0,255,0.25)]'
                    : 'bg-transparent'
                }`}
              >
                <Icon className="w-5 h-5" />
              </div>
              <span className="text-[10px] font-mono font-medium leading-none">
                {item.label}
              </span>
              {isActive && (
                <span className="absolute top-0 w-5 h-0.5 rounded-full bg-neon-magenta shadow-[0_0_8px_rgba(255,0,255,0.6)]" />
              )}
            </NavLink>
          )
        })}
      </div>
    </nav>
  )
}
