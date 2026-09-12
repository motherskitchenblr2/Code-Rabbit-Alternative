import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Repositories from './pages/Repositories'
import RepositoryDetail from './pages/RepositoryDetail'
import Settings from './pages/Settings'
import SelfImprovement from './pages/SelfImprovement'
import AgentTeam from './pages/AgentTeam'
import TeamDashboard from './pages/analytics/TeamDashboard'
import ComplianceReport from './pages/analytics/ComplianceReport'
import Admin from './pages/Admin'
import Login from './pages/Login'
import NotFound from './pages/NotFound'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cyber-900">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-neon-magenta border-t-transparent rounded-full animate-spin"></div>
          <p className="text-cyber-400 font-mono">Initializing...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cyber-900">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-neon-magenta border-t-transparent rounded-full animate-spin"></div>
          <p className="text-cyber-400 font-mono">Initializing...</p>
        </div>
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

function AdminOnly({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, user } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cyber-900">
        <div className="w-12 h-12 border-4 border-neon-magenta border-t-transparent rounded-full animate-spin"></div>
        <p className="text-cyber-400 font-mono">Initializing...</p>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (user?.role !== 'admin') {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={
        <PublicRoute>
          <Login />
        </PublicRoute>
      } />
      <Route element={
        <ProtectedRoute>
          <Layout />
        </ProtectedRoute>
      }>
        <Route path="/" element={<Dashboard />} />
        <Route path="/repositories" element={<Repositories />} />
        <Route path="/repositories/:id" element={<RepositoryDetail />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/admin" element={
          <AdminOnly>
            <Admin />
          </AdminOnly>
        } />
        <Route path="/self-improvement" element={<SelfImprovement />} />
        <Route path="/agents" element={<AgentTeam />} />
        <Route path="/analytics" element={<TeamDashboard />} />
        <Route path="/analytics/compliance" element={<ComplianceReport />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default App