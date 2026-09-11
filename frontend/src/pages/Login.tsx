import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuth } from '../contexts/AuthContext'
import { Lock, Mail, AlertCircle, Eye, EyeOff, Sparkles, Terminal } from 'lucide-react'

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginForm) => {
    setError(null)
    setIsLoading(true)
    try {
      await login(data.email, data.password)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-cyber-900 flex items-center justify-center p-4">
      {/* Background */}
      <div className="fixed inset-0 bg-grid pointer-events-none opacity-30" />

      <div className="relative z-10 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center justify-center gap-3 mb-6">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-neon-magenta to-neon-cyan flex items-center justify-center text-cyber-900 shadow-[0_0_40px_rgba(255,0,255,0.3)]">
              <Sparkles className="w-10 h-10" />
            </div>
          </Link>
          <h1 className="text-3xl font-bold font-display text-white mb-2">Welcome Back</h1>
          <p className="text-cyber-400">Sign in to access your Git-Fix dashboard</p>
        </div>

        {/* Login Form */}
        <div className="card-cyber-glow p-8">
          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-900/30 border border-red-500/30 flex items-center gap-3 text-red-300">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div>
              <label htmlFor="email" className="label-cyber">
                <Mail className="w-4 h-4 inline mr-2" />
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-cyber-500" />
                <input
                  {...register('email')}
                  type="email"
                  id="email"
                  autoComplete="email"
                  className="input-cyber pl-10"
                  placeholder="operator@gitfix.io"
                  disabled={isLoading}
                />
                {errors.email && (
                  <p className="mt-1 text-xs text-red-400 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {errors.email.message}
                  </p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="password" className="label-cyber">
                <Lock className="w-4 h-4 inline mr-2" />
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-cyber-500" />
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  autoComplete="current-password"
                  className="input-cyber pl-10 pr-10"
                  placeholder="••••••••"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-cyber-500 hover:text-neon-cyan transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <Eye className="w-5 h-5" /> : <EyeOff className="w-5 h-5" />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-xs text-red-400 flex items-center gap-1">
                  <AlertCircle className="w-3 h-3" />
                  {errors.password.message}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-cyber-magenta w-full py-3"
            >
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-5 h-5 border-2 border-neon-cyan border-t-transparent rounded-full animate-spin" />
                  Authenticating...
                </span>
              ) : (
                'Access Terminal'
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-cyber-700/50">
            <p className="text-center text-cyber-400 text-sm mb-4">Demo credentials are provisioned by the deployment owner — no passwords are baked into the client.</p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-cyber-500 text-sm">
            Don't have an account?{' '}
            <Link to="/register" className="text-neon-magenta hover:text-neon-cyan font-medium">
              Request Access
            </Link>
          </p>
          <div className="mt-6 flex items-center justify-center gap-4 text-cyber-500 text-xs">
            <span className="flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              Git-Fix v1.0.0
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
              Systems Operational
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

