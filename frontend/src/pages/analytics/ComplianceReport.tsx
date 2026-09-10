import React, { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import {
  Shield,
  CheckCircle,
  AlertTriangle,
  XCircle,
  FileText,
  Download,
  Calendar,
  TrendingUp,
  Target,
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
  Clock,
  Zap,
  BarChart3,
  PieChart,
  Users,
  Shield as ShieldIcon,
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, AreaChart, Area } from 'recharts'

interface ComplianceStandard {
  id: string
  name: string
  description: string
  status: 'compliant' | 'partial' | 'non-compliant' | 'not-assessed'
  score: number
  findings: number
  criticalFindings: number
  highFindings: number
  lastAudit: string
  nextAudit: string
  requirements: Requirement[]
  evidence: Evidence[]
  lastUpdated: string
}

interface Requirement {
  id: string
  title: string
  description: string
  status: 'met' | 'partial' | 'not-met' | 'not-applicable'
  evidence: string[]
  responsible: string
  dueDate: string
}

interface Evidence {
  id: string
  title: string
  type: 'document' | 'screenshot' | 'log' | 'policy' | 'config'
  url: string
  uploadedAt: string
  uploadedBy: string
  verified: boolean
}

const mockComplianceData: ComplianceStandard[] = [
  {
    id: 'soc2',
    name: 'SOC 2 Type II',
    description: 'Security, Availability, Processing Integrity, Confidentiality, Privacy',
    status: 'compliant',
    score: 98,
    findings: 2,
    criticalFindings: 0,
    highFindings: 1,
    lastAudit: '2024-01-15',
    nextAudit: '2025-01-15',
    lastUpdated: '2024-01-20',
    requirements: [
      { id: 'cc6.1', title: 'Logical Access Controls', description: 'Restrict logical access to information assets', status: 'met', evidence: ['access-control-policy.pdf', 'iam-config.json'], responsible: 'Sarah Chen', dueDate: '2024-12-31' },
      { id: 'cc6.2', title: 'Authentication & Authorization', description: 'Identify and authenticate users', status: 'met', evidence: ['mfa-config.yaml', 'sso-config.json'], responsible: 'Marcus Johnson', dueDate: '2024-12-31' },
      { id: 'cc6.7', title: 'Data Transmission Protection', description: 'Encrypt data in transit', status: 'met', evidence: ['tls-config.yaml', 'cert-manager.yaml'], responsible: 'Priya Patel', dueDate: '2024-12-31' },
      { id: 'cc7.2', title: 'System Monitoring', description: 'Monitor system components for anomalies', status: 'partial', evidence: ['prometheus-config.yaml', 'alerting-rules.yaml'], responsible: 'Alex Rivera', dueDate: '2024-06-30' },
      { id: 'cc8.1', title: 'Change Management', description: 'Authorize and track changes', status: 'met', evidence: ['change-policy.pdf', 'github-actions.yml'], responsible: 'Jordan Kim', dueDate: '2024-12-31' },
    ],
    evidence: [
      { id: '1', title: 'Access Control Policy', type: 'document', url: '/evidence/access-control-policy.pdf', uploadedAt: '2024-01-15', uploadedBy: 'Sarah Chen', verified: true },
      { id: '2', title: 'IAM Configuration', type: 'config', url: '/evidence/iam-config.json', uploadedAt: '2024-01-14', uploadedBy: 'Marcus Johnson', verified: true },
      { id: '3', title: 'MFA Configuration', type: 'config', url: '/evidence/mfa-config.yaml', uploadedAt: '2024-01-14', uploadedBy: 'Marcus Johnson', verified: true },
      { id: '4', title: 'SSO Configuration', type: 'config', url: '/evidence/sso-config.json', uploadedAt: '2024-01-13', uploadedBy: 'Priya Patel', verified: true },
      { id: '5', title: 'TLS Configuration', type: 'config', url: '/evidence/tls-config.yaml', uploadedAt: '2024-01-13', uploadedBy: 'Priya Patel', verified: true },
      { id: '6', title: 'Certificate Manager Config', type: 'config', url: '/evidence/cert-manager.yaml', uploadedAt: '2024-01-12', uploadedBy: 'Priya Patel', verified: true },
      { id: '7', title: 'Prometheus Configuration', type: 'config', url: '/evidence/prometheus-config.yaml', uploadedAt: '2024-01-12', uploadedBy: 'Alex Rivera', verified: true },
      { id: '8', title: 'Alerting Rules', type: 'config', url: '/evidence/alerting-rules.yaml', uploadedAt: '2024-01-11', uploadedBy: 'Alex Rivera', verified: false },
      { id: '9', title: 'Change Management Policy', type: 'document', url: '/evidence/change-policy.pdf', uploadedAt: '2024-01-10', uploadedBy: 'Jordan Kim', verified: true },
      { id: '10', title: 'GitHub Actions Workflow', type: 'config', url: '/evidence/github-actions.yml', uploadedAt: '2024-01-09', uploadedBy: 'Jordan Kim', verified: true },
    ],
  },
  {
    id: 'iso27001',
    name: 'ISO 27001',
    description: 'Information Security Management Systems',
    status: 'compliant',
    score: 95,
    findings: 5,
    criticalFindings: 0,
    highFindings: 2,
    lastAudit: '2024-01-10',
    nextAudit: '2025-01-10',
    lastUpdated: '2024-01-18',
    requirements: [
      { id: 'a.5.1', title: 'Information Security Policies', description: 'Define and communicate security policies', status: 'met', evidence: ['security-policy.pdf'], responsible: 'Sarah Chen', dueDate: '2024-12-31' },
      { id: 'a.6.1', title: 'Internal Organization', description: 'Define security roles and responsibilities', status: 'met', evidence: ['org-chart.pdf', 'rba-matrix.xlsx'], responsible: 'Morgan Lee', dueDate: '2024-12-31' },
      { id: 'a.8.1', title: 'Asset Management', description: 'Inventory of information assets', status: 'partial', evidence: ['asset-inventory.csv', 'cmdb-export.json'], responsible: 'Alex Rivera', dueDate: '2024-06-30' },
      { id: 'a.9.2', title: 'User Access Management', description: 'Formal user access provisioning', status: 'met', evidence: ['iam-process.pdf', 'jit-access.yaml'], responsible: 'Sarah Chen', dueDate: '2024-12-31' },
      { id: 'a.12.1', title: 'Operational Procedures', description: 'Documented operating procedures', status: 'met', evidence: ['runbooks/', 'playbooks/'], responsible: 'Morgan Lee', dueDate: '2024-12-31' },
    ],
    evidence: [],
    lastAudit: '2024-01-10',
    nextAudit: '2025-01-10',
    lastUpdated: '2024-01-18',
    requirements: [],
    evidence: [],
  },
  {
    id: 'gdpr',
    name: 'GDPR',
    description: 'General Data Protection Regulation',
    status: 'partial',
    score: 87,
    findings: 12,
    criticalFindings: 1,
    highFindings: 4,
    lastAudit: '2024-01-08',
    nextAudit: '2024-07-08',
    lastUpdated: '2024-01-16',
    requirements: [],
    evidence: [],
    lastAudit: '2024-01-08',
    nextAudit: '2024-07-08',
    lastUpdated: '2024-01-16',
    requirements: [],
    evidence: [],
  },
  {
    id: 'hipaa',
    name: 'HIPAA',
    description: 'Health Insurance Portability and Accountability Act',
    status: 'compliant',
    score: 92,
    findings: 3,
    criticalFindings: 0,
    highFindings: 1,
    lastAudit: '2024-01-12',
    nextAudit: '2025-01-12',
    lastUpdated: '2024-01-19',
    requirements: [],
    evidence: [],
    lastAudit: '2024-01-12',
    nextAudit: '2025-01-12',
    lastUpdated: '2024-01-19',
    requirements: [],
    evidence: [],
  },
  {
    id: 'pci-dss',
    name: 'PCI DSS',
    description: 'Payment Card Industry Data Security Standard',
    status: 'partial',
    score: 89,
    findings: 8,
    criticalFindings: 0,
    highFindings: 3,
    lastAudit: '2024-01-05',
    nextAudit: '2024-07-05',
    lastUpdated: '2024-01-14',
    requirements: [],
    evidence: [],
    lastAudit: '2024-01-05',
    nextAudit: '2024-07-05',
    lastUpdated: '2024-01-14',
    requirements: [],
    evidence: [],
  },
  {
    id: 'owasp',
    name: 'OWASP Top 10',
    description: 'Open Web Application Security Project Top 10',
    status: 'compliant',
    score: 96,
    findings: 1,
    criticalFindings: 0,
    highFindings: 0,
    lastAudit: '2024-01-14',
    nextAudit: '2025-01-14',
    lastUpdated: '2024-01-19',
    requirements: [],
    evidence: [],
    lastAudit: '2024-01-14',
    nextAudit: '2025-01-14',
    lastUpdated: '2024-01-19',
    requirements: [],
    evidence: [],
  },
]

export default function ComplianceReport() {
  const { user } = useAuth()
  const [selectedStandard, setSelectedStandard] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'overview' | 'detail' | 'evidence' | 'requirements'>('overview')
  const [filter, setFilter] = useState({ status: '', search: '' })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'compliant': return 'bg-neon-green/20 text-neon-green border-neon-green/30'
      case 'partial': return 'bg-neon-amber/20 text-neon-amber border-neon-amber/30'
      case 'non-compliant': return 'bg-red-500/20 text-red-400 border-red-500/30'
      case 'not-assessed': return 'bg-cyber-700/20 text-cyber-400 border-cyber-700/30'
      default: return 'bg-cyber-700/20 text-cyber-400 border-cyber-700/30'
    }
  }

  const getReqStatusColor = (status: string) => {
    switch (status) {
      case 'met': return 'bg-neon-green/20 text-neon-green border-neon-green/30'
      case 'partial': return 'bg-neon-amber/20 text-neon-amber border-neon-amber/30'
      case 'not-met': return 'bg-red-500/20 text-red-400 border-red-500/30'
      case 'not-applicable': return 'bg-cyber-700/20 text-cyber-400 border-cyber-700/30'
      default: return 'bg-cyber-700/20 text-cyber-400 border-cyber-700/30'
    }
  }

  const filteredStandards = mockComplianceData.filter(s => {
    if (filter.status && s.status !== filter.status) return false
    if (filter.search && !s.name.toLowerCase().includes(filter.search.toLowerCase()) && !s.description.toLowerCase().includes(filter.search.toLowerCase())) return false
    return true
  })

  if (viewMode === 'detail' && selectedStandard) {
    const standard = mockComplianceData.find(s => s.id === selectedStandard)!
    return (
      <div className="space-y-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div className="flex items-center gap-4">
            <button onClick={() => { setViewMode('overview'); setSelectedStandard(null) }} className="p-2 rounded-lg bg-cyber-800/50 hover:bg-cyber-700/50 border border-cyber-700/50 transition-colors">
              ←
            </button>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl font-bold font-display text-white">{standard.name}</h1>
                <span className={`badge-cyber ${getStatusColor(standard.status)}`}>{standard.status.toUpperCase()}</span>
              </div>
              <p className="text-cyber-400">{standard.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button className="btn-cyber-ghost" onClick={() => { setViewMode('requirements'); setViewMode('detail') }}>
              <FileText className="w-4 h-4 mr-2" /> Requirements
            </button>
            <button className="btn-cyber-ghost" onClick={() => { setViewMode('evidence'); setViewMode('detail') }}>
              <Shield className="w-4 h-4 mr-2" /> Evidence
            </button>
            <button className="btn-cyber-magenta">
              <Download className="w-4 h-4 mr-2" />
              Export Report
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-8">
          <StatCard title="Compliance Score" value={`${standard.score}%`} icon="🎯" color={standard.status === 'compliant' ? 'neon-green' : standard.status === 'partial' ? 'neon-amber' : 'red'} />
          <StatCard title="Total Findings" value={standard.findings} icon="🔍" color="neon-magenta" />
          <StatCard title="Critical Findings" value={standard.criticalFindings} icon="🔴" color="red" />
          <StatCard title="High Findings" value={standard.highFindings} icon="🟠" color="neon-amber" />
        </div>

        <div className="card-cyber p-6">
          <h3 className="text-lg font-bold font-display text-white mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-neon-cyan" />
            Requirements ({standard.requirements.length})
          </h3>
          <div className="space-y-3">
            {standard.requirements.map((req) => (
              <div key={req.id} className="p-4 rounded-lg bg-cyber-800/50 border border-cyber-700/50 hover:border-neon-magenta/30 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="font-mono text-neon-cyan text-sm">{req.id}</span>
                      <h4 className="font-medium text-white">{req.title}</h4>
                      <span className={`badge-cyber ${getReqStatusColor(req.status)}`}>{req.status.toUpperCase()}</span>
                    </div>
                    <p className="text-cyber-300 text-sm mb-2">{req.description}</p>
                    <div className="flex flex-wrap gap-2 text-xs text-cyber-400">
                      <span className="flex items-center gap-1"><Users className="w-3 h-3" /> {req.responsible}</span>
                      <span className="flex items-center gap-1"><Calendar className="w-3 h-3" /> Due: {req.dueDate}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`badge-cyber ${getReqStatusColor(req.status)} text-xs`}>{req.status}</span>
                    <button className="p-2 rounded-lg bg-cyber-800/50 hover:bg-cyber-700/50 border border-cyber-700/50 text-cyber-400 hover:text-neon-cyan transition-colors" title="View Evidence">
                      <FileText className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }
}

function StatCard({ title, value, icon, color }: { title: string; value: string | number; icon: string; color: string }) {
  const colorMap: Record<string, string> = {
    'neon-cyan': 'bg-neon-cyan/10 text-neon-cyan',
    'neon-magenta': 'bg-neon-magenta/10 text-neon-magenta',
    'neon-amber': 'bg-neon-amber/10 text-neon-amber',
    'neon-green': 'bg-neon-green/10 text-neon-green',
    'red': 'bg-red-500/10 text-red-400',
  }
  return (
    <div className="card-cyber p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-mono text-cyber-400 uppercase tracking-wider mb-1">{title}</p>
          <p className="text-3xl font-bold font-display text-white">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${{
          'neon-cyan': 'bg-neon-cyan/10',
          'neon-magenta': 'bg-neon-magenta/10',
          'neon-amber': 'bg-neon-amber/10',
          'neon-green': 'bg-neon-green/10',
          'red': 'bg-red-500/10',
        }[color] || 'bg-neon-magenta/10'}`}>
          <span className="text-2xl">{icon}</span>
        </div>
      </div>
    </div>
  )
}

export default ComplianceReport