import { Navigate, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from './store/auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Clients from './pages/Clients'
import ClientDetail from './pages/ClientDetail'
import Services from './pages/Services'
import Instructors from './pages/Instructors'
import InstructorDetail from './pages/InstructorDetail'
import Operations from './pages/Operations'
import BatchDetail from './pages/BatchDetail'
import Invoices from './pages/Invoices'
import Platform from './pages/Platform'
import Members from './pages/Members'

function Guard({ children, platform = false }: { children: ReactNode; platform?: boolean }) {
  const user = useAuth((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  const isPlatform = user.role === 'superadmin'
  if (platform && !isPlatform) return <Navigate to="/dashboard" replace />
  if (!platform && isPlatform) return <Navigate to="/platform" replace />
  return <>{children}</>
}

export default function App() {
  const user = useAuth((s) => s.user)
  const home = user ? (user.role === 'superadmin' ? '/platform' : '/dashboard') : '/login'
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route path="/dashboard" element={<Guard><Dashboard /></Guard>} />
        <Route path="/clients" element={<Guard><Clients /></Guard>} />
        <Route path="/clients/:id" element={<Guard><ClientDetail /></Guard>} />
        <Route path="/services" element={<Guard><Services /></Guard>} />
        <Route path="/instructors" element={<Guard><Instructors /></Guard>} />
        <Route path="/instructors/:id" element={<Guard><InstructorDetail /></Guard>} />
        <Route path="/operations" element={<Guard><Operations /></Guard>} />
        <Route path="/operations/batches/:id" element={<Guard><BatchDetail /></Guard>} />
        <Route path="/invoices" element={<Guard><Invoices /></Guard>} />
        <Route path="/settings/members" element={<Guard><Members /></Guard>} />
        <Route path="/platform" element={<Guard platform><Platform /></Guard>} />
      </Route>
      <Route path="*" element={<Navigate to={home} replace />} />
    </Routes>
  )
}
