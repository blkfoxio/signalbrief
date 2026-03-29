import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { exchangeOAuthCode } from '@/api/endpoints'
import { Loader2, Shield } from 'lucide-react'

export function CallbackPage() {
  const [searchParams] = useSearchParams()
  const { login } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')

    if (!code || !state) {
      setError('Invalid callback parameters')
      return
    }

    const handleCallback = async () => {
      try {
        const res = await exchangeOAuthCode(code, state)
        login(res.access_token, res.refresh_token, res.user)
        navigate('/')
      } catch {
        setError('Authentication failed. Please try again.')
      }
    }

    handleCallback()
  }, [searchParams, login, navigate])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <a href="/login" className="text-blue-600 hover:underline">Back to login</a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <Shield className="w-8 h-8 text-blue-600" />
        <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
        <p className="text-sm text-slate-500">Completing sign in...</p>
      </div>
    </div>
  )
}
