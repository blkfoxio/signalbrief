import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Shield, LogOut, Menu, X } from 'lucide-react'

export function Navbar() {
  const { user, logout, isAuthenticated } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)

  const closeMenu = () => setMenuOpen(false)

  // Close menu on route change
  const NavLink = ({ to, children }: { to: string; children: React.ReactNode }) => (
    <Link
      to={to}
      onClick={closeMenu}
      className="text-sm text-slate-600 hover:text-blue-600 no-underline"
    >
      {children}
    </Link>
  )

  return (
    <nav className="bg-white border-b border-slate-200">
      <div className="max-w-5xl mx-auto px-4 flex items-center justify-between h-14">
        <Link to="/" className="flex items-center gap-2 text-blue-600 font-semibold text-lg no-underline">
          <Shield className="w-5 h-5" />
          SignalBrief
        </Link>
        {isAuthenticated && (
          <>
            {/* Desktop nav */}
            <div className="hidden sm:flex items-center gap-4">
              <NavLink to="/new">New Report</NavLink>
              <NavLink to="/">Dashboard</NavLink>
              <span className="text-sm text-slate-400">{user?.email}</span>
              <button
                onClick={logout}
                className="text-slate-400 hover:text-slate-600 cursor-pointer p-2"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>

            {/* Mobile hamburger */}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="sm:hidden p-2 -mr-2 text-slate-500 hover:text-slate-700 cursor-pointer min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label="Toggle menu"
            >
              {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </>
        )}
      </div>

      {/* Mobile dropdown */}
      {isAuthenticated && menuOpen && (
        <div className="sm:hidden border-t border-slate-200 bg-white px-4 py-3 space-y-1">
          <Link
            to="/new"
            onClick={closeMenu}
            className="block py-2.5 text-sm text-slate-700 hover:text-blue-600 no-underline"
          >
            New Report
          </Link>
          <Link
            to="/"
            onClick={closeMenu}
            className="block py-2.5 text-sm text-slate-700 hover:text-blue-600 no-underline"
          >
            Dashboard
          </Link>
          <div className="border-t border-slate-100 pt-2 mt-1">
            <span className="block text-xs text-slate-400 mb-2">{user?.email}</span>
            <button
              onClick={() => { closeMenu(); logout() }}
              className="flex items-center gap-2 py-2.5 text-sm text-slate-600 hover:text-slate-900 cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
