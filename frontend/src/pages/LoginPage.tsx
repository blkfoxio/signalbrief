import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Loader2 } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { devLogin, devRegister, getLoginUrl } from '@/api/endpoints'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleMicrosoftLogin = async () => {
    setIsLoading(true)
    try {
      const authUrl = await getLoginUrl()
      window.location.href = authUrl
    } catch {
      setError('Failed to initiate login')
      setIsLoading(false)
    }
  }

  const handleDevAuth = async (e: FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    try {
      const authFn = mode === 'register' ? devRegister : devLogin
      const res = await authFn(email, password)
      login(res.access_token, res.refresh_token, res.user)
      navigate('/')
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { error?: string } } }
        setError(axiosErr.response?.data?.error || 'Authentication failed')
      } else {
        setError('Authentication failed')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Shield className="w-8 h-8 text-blue-600" />
            <h1 className="text-2xl font-bold text-slate-900">SignalBrief</h1>
          </div>
          <p className="text-sm text-slate-500">Presales intelligence, powered by evidence</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 p-6 space-y-4">
          <button
            onClick={handleMicrosoftLogin}
            disabled={isLoading}
            className="w-full py-2.5 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
          >
            Sign in with Microsoft
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-white px-2 text-slate-400">or dev login</span>
            </div>
          </div>

          <form onSubmit={handleDevAuth} className="space-y-3">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              required
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
              minLength={8}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            {error && <p className="text-xs text-red-600">{error}</p>}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {mode === 'register' ? 'Create Account' : 'Sign In'}
            </button>
          </form>

          <p className="text-xs text-center text-slate-400">
            {mode === 'login' ? (
              <>
                No account?{' '}
                <button onClick={() => setMode('register')} className="text-blue-600 hover:underline cursor-pointer">
                  Register
                </button>
              </>
            ) : (
              <>
                Have an account?{' '}
                <button onClick={() => setMode('login')} className="text-blue-600 hover:underline cursor-pointer">
                  Sign in
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  )
}
