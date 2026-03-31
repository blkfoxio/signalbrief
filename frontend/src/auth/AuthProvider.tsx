import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react'
import { getMe } from '@/api/endpoints'
import client, { setAccessToken } from '@/api/client'
import type { User } from '@/types'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (accessToken: string, user: User) => void
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

  const login = useCallback((accessToken: string, userData: User) => {
    setAccessToken(accessToken)
    setUser(userData)
  }, [])

  const logout = useCallback(async () => {
    try {
      await client.post('/auth/logout/')
    } catch { /* best-effort */ }
    setAccessToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    // Try to restore session using HttpOnly cookie (sent automatically)
    const restoreSession = async () => {
      try {
        const res = await client.post('/auth/refresh/')
        setAccessToken(res.data.access)
        const userData = await getMe()
        setUser(userData)
      } catch {
        // No valid session
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
