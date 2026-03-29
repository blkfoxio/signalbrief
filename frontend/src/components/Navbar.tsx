import { Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Shield, LogOut } from 'lucide-react'

export function Navbar() {
  const { user, logout, isAuthenticated } = useAuth()

  return (
    <nav className="bg-white border-b border-slate-200">
      <div className="max-w-5xl mx-auto px-4 flex items-center justify-between h-14">
        <Link to="/" className="flex items-center gap-2 text-blue-600 font-semibold text-lg no-underline">
          <Shield className="w-5 h-5" />
          SignalBrief
        </Link>
        {isAuthenticated && (
          <div className="flex items-center gap-4">
            <Link to="/new" className="text-sm text-slate-600 hover:text-blue-600 no-underline">
              New Report
            </Link>
            <Link to="/" className="text-sm text-slate-600 hover:text-blue-600 no-underline">
              Dashboard
            </Link>
            <span className="text-sm text-slate-400">{user?.email}</span>
            <button
              onClick={logout}
              className="text-slate-400 hover:text-slate-600 cursor-pointer"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </nav>
  )
}
