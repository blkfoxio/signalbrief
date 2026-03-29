import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="text-center py-20">
      <h1 className="text-4xl font-bold text-slate-300 mb-2">404</h1>
      <p className="text-sm text-slate-500 mb-4">Page not found</p>
      <Link to="/" className="text-sm text-blue-600 hover:underline">
        Back to dashboard
      </Link>
    </div>
  )
}
