import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { errorMessage } from '../api/client'
import type { TokenPair } from '../api/types'
import { useAuth } from '../store/auth'
import { Button, ErrorNote, Field } from '../components/ui'

export default function Login() {
  const [orgCode, setOrgCode] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const setSession = useAuth((s) => s.setSession)
  const navigate = useNavigate()

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const { data } = await axios.post<TokenPair>('/api/login', {
        org_code: orgCode,
        username,
        password,
      })
      setSession(data.access_token, data.refresh_token, data.user)
      navigate(data.user.role === 'superadmin' ? '/platform' : '/dashboard')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      <div className="hidden w-2/5 flex-col justify-between bg-brown-deep p-10 text-yellow-pale lg:flex">
        <div className="font-mono text-[10px] uppercase tracking-[.16em] text-gold">
          CoachLink · Class & client management
        </div>
        <div>
          <h1 className="font-display text-4xl font-extrabold italic tracking-tight">CoachLink</h1>
          <div className="mt-2 h-1 w-11 rounded-sm bg-gold" />
          <p className="mt-4 max-w-sm text-sm text-yellow-pale/80">
            Services, clients, instructors, batches and billing — automation your business can
            stand on.
          </p>
        </div>
        <div className="font-mono text-[10px] text-yellow-pale/50">An Elevionix Tech Labs product</div>
      </div>
      <div className="flex flex-1 items-center justify-center p-6">
        <form
          onSubmit={submit}
          className="w-full max-w-sm rounded-xl border border-gold-soft bg-yellow-card p-8 shadow-[0_1px_2px_rgba(51,32,13,.06),0_10px_28px_-14px_rgba(51,32,13,.24)]"
        >
          <h2 className="seal font-display text-xl font-extrabold tracking-tight">Sign in</h2>
          <div className="mt-6 space-y-4">
            <Field
              label="Organisation code"
              value={orgCode}
              onChange={(e) => setOrgCode(e.target.value.toUpperCase())}
              placeholder="STUDIO-1"
              required
              autoFocus
              className="[&>input]:font-mono [&>input]:uppercase"
            />
            <Field
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <Field
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <ErrorNote message={error} />
            <Button intent="accent" type="submit" disabled={busy} className="w-full">
              {busy ? 'Signing in…' : 'Sign in'}
            </Button>
            <p className="text-xs text-brown-mid">
              Platform administrators sign in with the reserved code{' '}
              <span className="font-mono">PLATFORM</span>.
            </p>
          </div>
        </form>
      </div>
    </div>
  )
}
