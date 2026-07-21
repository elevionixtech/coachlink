import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { ClientIn, ClientOut, Page } from '../api/types'
import { ACCOUNT_TYPES, GENDERS, LEAD_SOURCES, LIFECYCLE_STAGES } from '../api/types'
import {
  Badge, Button, ErrorNote, Field, Modal, EmptyState, Panel, SealHeading, SelectField,
  Spinner, Table, statusTone,
} from '../components/ui'

export function ClientForm({
  initial,
  onSaved,
  onClose,
}: {
  initial?: ClientOut
  onSaved: () => void
  onClose: () => void
}) {
  const [form, setForm] = useState<Partial<ClientIn>>({
    name: initial?.name ?? '',
    name_hint: initial?.name_hint ?? '',
    phone: initial?.phone ?? '',
    email: initial?.email ?? '',
    gender: initial?.gender ?? null,
    date_of_birth: initial?.date_of_birth ?? null,
    lead_source: initial?.lead_source ?? null,
    lifecycle_stage: initial?.lifecycle_stage ?? 'Lead',
    account_type: initial?.account_type ?? 'Individual',
    company_name: initial?.company_name ?? '',
    gstin: initial?.gstin ?? '',
    company_contact: initial?.company_contact ?? '',
    address: initial?.address ?? '',
    work: initial?.work ?? '',
    description: initial?.description ?? '',
    do_not_contact: initial?.do_not_contact ?? false,
    do_not_email: initial?.do_not_email ?? false,
    do_not_call: initial?.do_not_call ?? false,
  })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof ClientIn, v: unknown) => setForm((f) => ({ ...f, [k]: v }))

  const save = useMutation({
    mutationFn: async () => {
      const body = { ...form, gender: form.gender || null, lead_source: form.lead_source || null, date_of_birth: form.date_of_birth || null }
      if (initial) await api.patch(`/clients/${initial.id}`, body)
      else await api.post('/clients', body)
    },
    onSuccess: onSaved,
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal title={initial ? 'Edit client' : 'New client'} onClose={onClose} wide>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
        className="space-y-4"
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Name" required value={form.name ?? ''} onChange={(e) => set('name', e.target.value)} />
          <Field label="Name hint" value={form.name_hint ?? ''} onChange={(e) => set('name_hint', e.target.value)} placeholder="Marathon runner" />
          <Field label="Phone" value={form.phone ?? ''} onChange={(e) => set('phone', e.target.value)} />
          <Field label="Email" type="email" value={form.email ?? ''} onChange={(e) => set('email', e.target.value)} />
          <SelectField label="Gender" value={form.gender ?? ''} onChange={(e) => set('gender', e.target.value || null)}>
            <option value="">—</option>
            {GENDERS.map((g) => <option key={g}>{g}</option>)}
          </SelectField>
          <Field label="Date of birth" type="date" value={form.date_of_birth ?? ''} onChange={(e) => set('date_of_birth', e.target.value || null)} />
          <SelectField label="Lead source" value={form.lead_source ?? ''} onChange={(e) => set('lead_source', e.target.value || null)}>
            <option value="">—</option>
            {LEAD_SOURCES.map((s) => <option key={s}>{s}</option>)}
          </SelectField>
          <SelectField label="Lifecycle stage" value={form.lifecycle_stage ?? 'Lead'} onChange={(e) => set('lifecycle_stage', e.target.value)}>
            {LIFECYCLE_STAGES.map((s) => <option key={s}>{s}</option>)}
          </SelectField>
          <SelectField label="Account type" value={form.account_type ?? 'Individual'} onChange={(e) => set('account_type', e.target.value)}>
            {ACCOUNT_TYPES.map((t) => <option key={t}>{t}</option>)}
          </SelectField>
          <Field label="Work" value={form.work ?? ''} onChange={(e) => set('work', e.target.value)} />
        </div>
        {form.account_type === 'Corporate' && (
          <div className="grid grid-cols-3 gap-4 rounded-lg border border-gold-soft bg-white/50 p-3">
            <Field label="Company name" value={form.company_name ?? ''} onChange={(e) => set('company_name', e.target.value)} />
            <Field label="GSTIN" value={form.gstin ?? ''} onChange={(e) => set('gstin', e.target.value)} className="[&>input]:font-mono" />
            <Field label="Company contact" value={form.company_contact ?? ''} onChange={(e) => set('company_contact', e.target.value)} />
          </div>
        )}
        <Field label="Address" value={form.address ?? ''} onChange={(e) => set('address', e.target.value)} />
        <div className="flex gap-6">
          {(['do_not_contact', 'do_not_email', 'do_not_call'] as const).map((k) => (
            <label key={k} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!form[k]} onChange={(e) => set(k, e.target.checked)} className="accent-orange" />
              {k.replaceAll('_', ' ').replace('do not', 'Do not')}
            </label>
          ))}
        </div>
        <ErrorNote message={error} />
        <div className="flex justify-end gap-3">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button intent="accent" type="submit" disabled={save.isPending}>
            {initial ? 'Save changes' : 'Create client'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default function Clients() {
  const [q, setQ] = useState('')
  const [stage, setStage] = useState('')
  const [creating, setCreating] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['clients', q, stage],
    queryFn: async () =>
      (
        await api.get<Page<ClientOut>>('/clients', {
          params: { q: q || undefined, lifecycle_stage: stage || undefined },
        })
      ).data,
  })

  return (
    <div>
      <div className="flex items-start justify-between">
        <SealHeading eyebrow="CRM">Clients</SealHeading>
        <Button intent="accent" onClick={() => setCreating(true)}>Add client</Button>
      </div>

      <div className="mb-4 flex gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search name, phone or email"
          className="w-72 rounded-[4px] border border-gold-soft bg-white px-3 py-2 text-sm"
        />
        <select
          value={stage}
          onChange={(e) => setStage(e.target.value)}
          className="rounded-[4px] border border-gold-soft bg-white px-3 py-2 text-sm"
        >
          <option value="">All stages</option>
          {LIFECYCLE_STAGES.map((s) => <option key={s}>{s}</option>)}
        </select>
      </div>

      {isLoading ? (
        <Spinner />
      ) : !data || data.items.length === 0 ? (
        <Panel>
          <EmptyState
            title="No clients found"
            hint={q || stage ? 'Try a different search or filter.' : 'Add your first client to get started.'}
            action={!q && !stage && <Button intent="accent" onClick={() => setCreating(true)}>Add client</Button>}
          />
        </Panel>
      ) : (
        <Table head={['Name', 'Contact', 'Stage', 'Account', 'Preferences']}>
          {data.items.map((c) => (
            <tr key={c.id}>
              <td className="px-4 py-2.5">
                <Link to={`/clients/${c.id}`} className="font-medium text-orange-deep hover:text-orange">
                  {c.name}
                </Link>
                {c.name_hint && <div className="text-xs text-brown-mid">{c.name_hint}</div>}
              </td>
              <td className="px-4 py-2.5 font-mono text-xs">
                {c.phone ?? '—'}
                <div className="text-brown-mid">{c.email ?? ''}</div>
              </td>
              <td className="px-4 py-2.5"><Badge tone={statusTone(c.lifecycle_stage)}>{c.lifecycle_stage}</Badge></td>
              <td className="px-4 py-2.5 text-xs">{c.account_type}</td>
              <td className="px-4 py-2.5 text-xs text-orange-deep">
                {[c.do_not_contact && 'No contact', c.do_not_email && 'No email', c.do_not_call && 'No calls']
                  .filter(Boolean)
                  .join(' · ') || <span className="text-brown-mid">—</span>}
              </td>
            </tr>
          ))}
        </Table>
      )}

      {creating && (
        <ClientForm
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false)
            queryClient.invalidateQueries({ queryKey: ['clients'] })
          }}
        />
      )}
    </div>
  )
}
