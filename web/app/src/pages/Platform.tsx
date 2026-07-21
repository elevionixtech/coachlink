import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { AdminOrgOut, MemberOut, PlanOut } from '../api/types'
import { fullDate, rupees } from '../lib/format'
import {
  Badge, Button, ErrorNote, Field, Modal, EmptyState, Panel, SealHeading, SelectField,
  Spinner, Table,
} from '../components/ui'

export default function Platform() {
  return (
    <div className="space-y-10">
      <OrgsSection />
      <PlansSection />
    </div>
  )
}

// ---------------------------------------------------------------- organisations

function OrgsSection() {
  const queryClient = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [managing, setManaging] = useState<AdminOrgOut | null>(null)
  const [assigning, setAssigning] = useState<AdminOrgOut | null>(null)

  const { data: orgs, isLoading } = useQuery({
    queryKey: ['admin-orgs'],
    queryFn: async () => (await api.get<AdminOrgOut[]>('/admin/organisations')).data,
  })

  const stateTone = (s: string) => (s === 'active' ? 'active' : s === 'expired' ? 'pending' : 'draft')

  return (
    <section>
      <div className="flex items-start justify-between">
        <SealHeading eyebrow="Platform administration">Organisations</SealHeading>
        <Button intent="accent" onClick={() => setCreating(true)}>Create organisation</Button>
      </div>
      {isLoading ? (
        <Spinner />
      ) : !orgs?.length ? (
        <Panel><EmptyState title="No organisations yet" /></Panel>
      ) : (
        <Table head={['Organisation', 'Code', 'Plan', 'Subscription', 'Members', 'Clients', '']}>
          {orgs.map((o) => (
            <tr key={o.id}>
              <td className="px-4 py-2.5 font-medium">{o.name}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{o.code}</td>
              <td className="px-4 py-2.5 text-xs">{o.plan_name ?? '—'}</td>
              <td className="px-4 py-2.5">
                <Badge tone={stateTone(o.subscription_state)}>
                  {o.subscription_state === 'none'
                    ? 'No plan'
                    : o.subscription_state === 'active'
                      ? `Active until ${fullDate(o.subscription_ends_on)}`
                      : `Expired ${fullDate(o.subscription_ends_on)}`}
                </Badge>
              </td>
              <td className="px-4 py-2.5 font-mono text-xs">{o.member_count}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{o.client_count}</td>
              <td className="px-4 py-2.5 text-right whitespace-nowrap">
                <Button className="!px-2 !py-1 text-xs" onClick={() => setManaging(o)}>Members</Button>{' '}
                <Button className="!px-2 !py-1 text-xs" onClick={() => setAssigning(o)}>Assign plan</Button>
              </td>
            </tr>
          ))}
        </Table>
      )}
      {creating && (
        <CreateOrgModal
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false)
            queryClient.invalidateQueries({ queryKey: ['admin-orgs'] })
          }}
        />
      )}
      {managing && <MembersModal org={managing} onClose={() => setManaging(null)} />}
      {assigning && (
        <AssignPlanModal
          org={assigning}
          onClose={() => setAssigning(null)}
          onSaved={() => {
            setAssigning(null)
            queryClient.invalidateQueries({ queryKey: ['admin-orgs'] })
          }}
        />
      )}
    </section>
  )
}

function CreateOrgModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ name: '', code: '', adminName: '', username: '', password: '' })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const save = useMutation({
    mutationFn: async () =>
      api.post('/admin/organisations', {
        name: form.name,
        code: form.code,
        admin: { name: form.adminName, username: form.username, password: form.password, role: 'admin' },
      }),
    onSuccess: onSaved,
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal title="Create organisation" onClose={onClose}>
      <form onSubmit={(e) => { e.preventDefault(); save.mutate() }} className="space-y-4">
        <Field label="Organisation name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
        <Field
          label="Code" required value={form.code}
          onChange={(e) => set('code', e.target.value.toUpperCase())}
          className="[&>input]:font-mono [&>input]:uppercase"
          hint="2–20 chars, A–Z 0–9 and dashes — used at login"
        />
        <div className="border-t border-gold-soft pt-3">
          <span className="eyebrow">First admin account</span>
        </div>
        <Field label="Admin name" required value={form.adminName} onChange={(e) => set('adminName', e.target.value)} />
        <div className="grid grid-cols-2 gap-4">
          <Field label="Username" required value={form.username} onChange={(e) => set('username', e.target.value)} />
          <Field label="Password" type="password" required minLength={4} value={form.password} onChange={(e) => set('password', e.target.value)} />
        </div>
        <ErrorNote message={error} />
        <div className="flex justify-end gap-3">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button intent="accent" type="submit" disabled={save.isPending}>Create organisation</Button>
        </div>
      </form>
    </Modal>
  )
}

function AssignPlanModal({
  org, onClose, onSaved,
}: { org: AdminOrgOut; onClose: () => void; onSaved: () => void }) {
  const [planId, setPlanId] = useState(org.plan_id ?? '')
  const [startsOn, setStartsOn] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: plans } = useQuery({
    queryKey: ['admin-plans'],
    queryFn: async () => (await api.get<PlanOut[]>('/admin/plans')).data,
  })

  const save = useMutation({
    mutationFn: async () =>
      api.post(`/admin/organisations/${org.id}/plan`, {
        plan_id: planId,
        starts_on: startsOn || null,
      }),
    onSuccess: onSaved,
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal title={`Assign plan — ${org.name}`} onClose={onClose}>
      <form onSubmit={(e) => { e.preventDefault(); save.mutate() }} className="space-y-4">
        <SelectField label="Plan" required value={planId} onChange={(e) => setPlanId(e.target.value)}>
          <option value="">Choose a plan…</option>
          {plans?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} · {rupees(p.amount)} · {p.no_of_days} days
            </option>
          ))}
        </SelectField>
        <Field
          label="Starts on" type="date" value={startsOn}
          onChange={(e) => setStartsOn(e.target.value)}
          hint="Defaults to today; expiry is start + plan days"
        />
        <ErrorNote message={error} />
        <div className="flex justify-end gap-3">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button intent="accent" type="submit" disabled={save.isPending || !planId}>Assign plan</Button>
        </div>
      </form>
    </Modal>
  )
}

function MembersModal({ org, onClose }: { org: AdminOrgOut; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ name: '', username: '', password: '', role: 'staff' })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const { data: members } = useQuery({
    queryKey: ['org-members', org.id],
    queryFn: async () => (await api.get<MemberOut[]>(`/organisations/${org.id}/members`)).data,
  })

  const add = useMutation({
    mutationFn: async () => api.post(`/organisations/${org.id}/members`, form),
    onSuccess: () => {
      setForm({ name: '', username: '', password: '', role: 'staff' })
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['org-members', org.id] })
      queryClient.invalidateQueries({ queryKey: ['admin-orgs'] })
    },
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal title={`Members — ${org.name}`} onClose={onClose} wide>
      <div className="space-y-4">
        {!members?.length ? (
          <p className="text-sm text-brown-mid">No members.</p>
        ) : (
          <Table head={['Name', 'Username', 'Role', 'Added']}>
            {members.map((m) => (
              <tr key={m.id}>
                <td className="px-4 py-2">{m.name}</td>
                <td className="px-4 py-2 font-mono text-xs">{m.username}</td>
                <td className="px-4 py-2"><Badge tone={m.role === 'admin' ? 'active' : 'draft'}>{m.role}</Badge></td>
                <td className="px-4 py-2 font-mono text-xs">{fullDate(m.created_at.slice(0, 10))}</td>
              </tr>
            ))}
          </Table>
        )}
        <form
          onSubmit={(e) => { e.preventDefault(); add.mutate() }}
          className="grid grid-cols-2 gap-3 rounded-lg border border-gold-soft bg-white/50 p-3"
        >
          <Field label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
          <Field label="Username" required value={form.username} onChange={(e) => set('username', e.target.value)} />
          <Field label="Password" type="password" required minLength={4} value={form.password} onChange={(e) => set('password', e.target.value)} />
          <SelectField label="Role" value={form.role} onChange={(e) => set('role', e.target.value)}>
            <option value="staff">staff</option>
            <option value="admin">admin</option>
          </SelectField>
          <div className="col-span-2">
            <ErrorNote message={error} />
          </div>
          <div className="col-span-2 flex justify-end">
            <Button intent="accent" type="submit" disabled={add.isPending}>Add member</Button>
          </div>
        </form>
      </div>
    </Modal>
  )
}

// ---------------------------------------------------------------- plans

function PlansSection() {
  const queryClient = useQueryClient()
  const [creating, setCreating] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const { data: plans, isLoading } = useQuery({
    queryKey: ['admin-plans'],
    queryFn: async () => (await api.get<PlanOut[]>('/admin/plans')).data,
  })

  const remove = useMutation({
    mutationFn: async (id: string) => api.delete(`/admin/plans/${id}`),
    onSuccess: () => {
      setMessage(null)
      queryClient.invalidateQueries({ queryKey: ['admin-plans'] })
    },
    onError: (e) => setMessage(errorMessage(e)),
  })

  return (
    <section>
      <div className="flex items-start justify-between">
        <SealHeading eyebrow="Platform billing">Subscription plans</SealHeading>
        <Button intent="primary" onClick={() => setCreating(true)}>New plan</Button>
      </div>
      {message && <div className="mb-3"><ErrorNote message={message} /></div>}
      {isLoading ? (
        <Spinner />
      ) : !plans?.length ? (
        <Panel><EmptyState title="No plans" hint="Create a plan, then assign it to organisations." /></Panel>
      ) : (
        <Table head={['Plan', 'Amount', 'Duration', 'In use', 'Description', '']}>
          {plans.map((p) => (
            <tr key={p.id}>
              <td className="px-4 py-2.5 font-medium">{p.name}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{rupees(p.amount)}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{p.no_of_days} days</td>
              <td className="px-4 py-2.5 font-mono text-xs">{p.orgs_in_use} org(s)</td>
              <td className="px-4 py-2.5 text-xs">{p.description ?? '—'}</td>
              <td className="px-4 py-2.5 text-right">
                <Button
                  intent="danger"
                  className="!px-2 !py-1 text-xs"
                  disabled={p.orgs_in_use > 0}
                  title={p.orgs_in_use > 0 ? `In use by ${p.orgs_in_use} organisation(s)` : undefined}
                  onClick={() => confirm(`Delete plan ${p.name}?`) && remove.mutate(p.id)}
                >
                  Delete
                </Button>
              </td>
            </tr>
          ))}
        </Table>
      )}
      {creating && (
        <PlanModal
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false)
            queryClient.invalidateQueries({ queryKey: ['admin-plans'] })
          }}
        />
      )}
    </section>
  )
}

function PlanModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ name: '', amount: '', no_of_days: '30', description: '' })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const save = useMutation({
    mutationFn: async () =>
      api.post('/admin/plans', {
        name: form.name,
        amount: form.amount,
        no_of_days: Number(form.no_of_days),
        description: form.description || null,
      }),
    onSuccess: onSaved,
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal title="New subscription plan" onClose={onClose}>
      <form onSubmit={(e) => { e.preventDefault(); save.mutate() }} className="space-y-4">
        <Field label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
        <div className="grid grid-cols-2 gap-4">
          <Field label="Amount (₹)" type="number" min={0} required value={form.amount} onChange={(e) => set('amount', e.target.value)} />
          <Field label="Duration (days)" type="number" min={1} required value={form.no_of_days} onChange={(e) => set('no_of_days', e.target.value)} />
        </div>
        <Field label="Description" value={form.description} onChange={(e) => set('description', e.target.value)} />
        <ErrorNote message={error} />
        <div className="flex justify-end gap-3">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button intent="accent" type="submit" disabled={save.isPending}>Create plan</Button>
        </div>
      </form>
    </Modal>
  )
}
