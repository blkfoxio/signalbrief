import { Navigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  if (!user?.is_staff) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}
