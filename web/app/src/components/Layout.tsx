import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../store/auth'
import { api } from '../api/client'
import type { OrgSettingsOut } from '../api/types'

const NAV = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/clients', label: 'Clients' },
  { to: '/services', label: 'Services' },
  { to: '/instructors', label: 'Instructors' },
  { to: '/operations', label: 'Operations' },
  { to: '/invoices', label: 'Invoices' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const isPlatform = user?.role === 'superadmin'

  const { data: org } = useQuery({
    queryKey: ['org'],
    queryFn: async () => (await api.get<OrgSettingsOut>('/org')).data,
    enabled: !isPlatform,
  })

  return (
    <div className="min-h-screen">
      <header className="bg-brown-deep text-yellow-pale">
        <div className="mx-auto flex max-w-6xl items-center gap-8 px-6 py-3">
          <div>
            <div className="font-display text-lg font-extrabold italic tracking-tight leading-none">
              CoachLink
            </div>
            <div className="font-mono text-[9px] uppercase tracking-[.16em] text-gold">
              {isPlatform ? 'Platform administration' : (org?.name ?? ' ')}
            </div>
          </div>
          <nav className="flex flex-1 gap-1">
            {!isPlatform &&
              NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `rounded-[4px] px-3 py-1.5 text-sm transition-colors duration-150 ${
                      isActive
                        ? 'bg-yellow text-brown-deep font-semibold'
                        : 'text-yellow-pale/85 hover:text-white'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            {isPlatform && (
              <NavLink
                to="/platform"
                className={({ isActive }) =>
                  `rounded-[4px] px-3 py-1.5 text-sm ${
                    isActive ? 'bg-yellow text-brown-deep font-semibold' : 'text-yellow-pale/85'
                  }`
                }
              >
                Organisations & plans
              </NavLink>
            )}
          </nav>
          {!isPlatform && user?.role === 'admin' && (
            <NavLink to="/settings/members" className="text-sm text-yellow-pale/85 hover:text-white">
              Members
            </NavLink>
          )}
          <div className="flex items-center gap-3">
            <span className="font-mono text-[11px] text-yellow-pale/70">
              {user?.name} · {user?.role}
            </span>
            <button
              onClick={() => {
                logout()
                navigate('/login')
              }}
              className="rounded-[4px] border border-yellow-pale/30 px-2.5 py-1 text-xs hover:border-yellow-pale/70 cursor-pointer"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
