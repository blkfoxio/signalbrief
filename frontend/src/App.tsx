import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from '@/auth/AuthProvider'
import { ProtectedRoute } from '@/auth/ProtectedRoute'
import { Layout } from '@/components/Layout'
import { LoginPage } from '@/pages/LoginPage'
import { CallbackPage } from '@/pages/CallbackPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { NewReportPage } from '@/pages/NewReportPage'
import { ReportPage } from '@/pages/ReportPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/auth/callback" element={<CallbackPage />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/new" element={<NewReportPage />} />
            <Route path="/reports/:id" element={<ReportPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
