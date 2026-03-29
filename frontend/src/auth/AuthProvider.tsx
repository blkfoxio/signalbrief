import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react'
import { getMe } from '@/api/endpoints'
import { setAccessToken } from '@/api/client'
import type { User } from '@/types'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (accessToken: string, refreshToken: string, user: User) => void
  logout: () => void
}

export const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  login: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const login = useCallback((accessToken: string, refreshToken: string, userData: User) => {
    setAccessToken(accessToken)
    localStorage.setItem('refresh_token', refreshToken)
    setUser(userData)
  }, [])

  const logout = useCallback(() => {
    setAccessToken(null)
    localStorage.removeItem('refresh_token')
    setUser(null)
  }, [])

  useEffect(() => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      setIsLoading(false)
      return
    }

    // Try to restore session
    const restoreSession = async () => {
      try {
        const res = await fetch('/api/auth/refresh/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh: refreshToken }),
        })
        if (!res.ok) throw new Error('Refresh failed')
        const data = await res.json()
        setAccessToken(data.access)
        const userData = await getMe()
        setUser(userData)
      } catch {
        localStorage.removeItem('refresh_token')
      } finally {
        setIsLoading(false)
      }
    }

    restoreSession()
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
