import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type {
  BatchOut, ClientOut, EnrollmentOut, InvoiceOut, NoteOut, Page, ServiceOut, SubscriptionOut,
} from '../api/types'
import { NOTE_CHANNELS } from '../api/types'
import { age, fullDate, rupees } from '../lib/format'
import {
  Badge, Button, ErrorNote, Field, Modal, EmptyState, Panel, SealHeading, SelectField,
  Spinner, Table, TextArea, statusTone,
} from '../components/ui'
import { ClientForm } from './Clients'

const TABS = ['Details', 'Corporate & family', 'Notes', 'Invoices', 'Subscriptions', 'Enrollments'] as const
type Tab = (typeof TABS)[number]

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="eyebrow">{label}</div>
      <div className="mt-0.5 text-sm">{children ?? '—'}</div>
    </div>
  )
}

export default function ClientDetail() {
  const { id } = useParams()
  const [tab, setTab] = useState<Tab>('Details')
  const [editing, setEditing] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const { data: client, isLoading } = useQuery({
    queryKey: ['client', id],
    queryFn: async () => (await api.get<ClientOut>(`/clients/${id}`)).data,
  })

  const archive = useMutation({
    mutationFn: async () => api.delete(`/clients/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      navigate('/clients')
    },
  })

  if (isLoading || !client) return <Spinner />

  const flags = [
    client.do_not_contact && 'Do not contact',
    client.do_not_email && 'Do not email',
    client.do_not_call && 'Do not call',
  ].filter(Boolean) as string[]

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <SealHeading eyebrow="Client profile">{client.name}</SealHeading>
          <div className="-mt-3 mb-4 flex items-center gap-3">
            {client.name_hint && <span className="text-sm text-brown-mid">{client.name_hint}</span>}
            <Badge tone={statusTone(client.lifecycle_stage)}>{client.lifecycle_stage}</Badge>
            {flags.map((f) => (
              <span key={f} className="font-mono text-[11px] text-orange-deep">{f}</span>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setEditing(true)}>Edit details</Button>
          <Button
            intent="danger"
            onClick={() => {
              if (confirm(`Archive ${client.name}? The record is kept but hidden.`)) archive.mutate()
            }}
          >
            Archive
          </Button>
        </div>
      </div>

      <div className="mb-5 flex gap-1 border-b border-gold-soft">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm cursor-pointer border-b-2 -mb-px transition-colors ${
              tab === t ? 'border-orange font-semibold text-brown' : 'border-transparent text-brown-mid hover:text-brown'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Details' && (
        <Panel className="grid grid-cols-2 gap-x-8 gap-y-4 p-5 lg:grid-cols-3">
          <Item label="Phone">{client.phone && <span className="font-mono">{client.phone}</span>}</Item>
          <Item label="Email">{client.email && <span className="font-mono">{client.email}</span>}</Item>
          <Item label="Gender">{client.gender}</Item>
          <Item label="Date of birth">
            {client.date_of_birth && `${fullDate(client.date_of_birth)} · ${age(client.date_of_birth)} yrs`}
          </Item>
          <Item label="Lead source">{client.lead_source}</Item>
          <Item label="Work">{client.work}</Item>
          <Item label="Address">{client.address}</Item>
          <Item label="Description">{client.description}</Item>
          <Item label="Created">{fullDate(client.created_at.slice(0, 10))}</Item>
        </Panel>
      )}

      {tab === 'Corporate & family' && (
        <Panel className="p-5 space-y-5">
          <Item label="Account type">{client.account_type}</Item>
          {client.account_type === 'Corporate' && (
            <div className="grid grid-cols-3 gap-4">
              <Item label="Company">{client.company_name}</Item>
              <Item label="GSTIN">{client.gstin && <span className="font-mono">{client.gstin}</span>}</Item>
              <Item label="Company contact">{client.company_contact}</Item>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <Item label="Family link">
              {client.family_link_id ? (
                <Link to={`/clients/${client.family_link_id}`} className="text-orange-deep hover:text-orange">
                  {client.family_link_name}
                </Link>
              ) : (
                '—'
              )}
            </Item>
            <Item label="Linked by">
              {client.linked_by.length
                ? client.linked_by.map((r, i) => (
                    <span key={r.id}>
                      {i > 0 && ' · '}
                      <Link to={`/clients/${r.id}`} className="text-orange-deep hover:text-orange">{r.name}</Link>
                    </span>
                  ))
                : '—'}
            </Item>
          </div>
          <p className="text-xs text-brown-mid">
            Set the account type and family link from “Edit details”. Switching away from Corporate
            clears company fields; switching away from Family clears the link.
          </p>
        </Panel>
      )}

      {tab === 'Notes' && <NotesTab clientId={client.id} />}
      {tab === 'Invoices' && <InvoicesTab clientId={client.id} />}
      {tab === 'Subscriptions' && <SubscriptionsTab clientId={client.id} />}
      {tab === 'Enrollments' && <EnrollmentsTab clientId={client.id} />}

      {editing && (
        <ClientForm
          initial={client}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false)
            queryClient.invalidateQueries({ queryKey: ['client', id] })
          }}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------- notes

function NotesTab({ clientId }: { clientId: string }) {
  const queryClient = useQueryClient()
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [channel, setChannel] = useState<string>('Call')
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: notes } = useQuery({
    queryKey: ['notes', clientId],
    queryFn: async () => (await api.get<NoteOut[]>(`/clients/${clientId}/notes`)).data,
  })

  const add = useMutation({
    mutationFn: async () => api.post(`/clients/${clientId}/notes`, { date, channel, text }),
    onSuccess: () => {
      setText('')
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['notes', clientId] })
    },
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-3">
        {!notes?.length && (
          <Panel><EmptyState title="No contact notes yet" hint="Notes are append-only — newest first." /></Panel>
        )}
        {notes?.map((n) => (
          <Panel key={n.id} className="p-4">
            <div className="flex items-center gap-3 font-mono text-[11px] text-brown-mid">
              <span>{fullDate(n.date)}</span>
              <Badge>{n.channel}</Badge>
              <span>by {n.author_name}</span>
            </div>
            <p className="mt-2 text-sm whitespace-pre-wrap">{n.text}</p>
          </Panel>
        ))}
      </div>
      <Panel className="h-fit p-4">
        <h3 className="font-display font-bold mb-3">Add note</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            add.mutate()
          }}
          className="space-y-3"
        >
          <Field label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
          <SelectField label="Channel" value={channel} onChange={(e) => setChannel(e.target.value)}>
            {NOTE_CHANNELS.map((c) => <option key={c}>{c}</option>)}
          </SelectField>
          <TextArea label="Note" value={text} onChange={(e) => setText(e.target.value)} required />
          <ErrorNote message={error} />
          <Button intent="accent" type="submit" disabled={add.isPending} className="w-full">
            Append note
          </Button>
        </form>
      </Panel>
    </div>
  )
}

// ---------------------------------------------------------------- invoices

function InvoicesTab({ clientId }: { clientId: string }) {
  const queryClient = useQueryClient()
  const [message, setMessage] = useState<string | null>(null)

  const { data: invoices } = useQuery({
    queryKey: ['client-invoices', clientId],
    queryFn: async () => (await api.get<InvoiceOut[]>(`/clients/${clientId}/invoices`)).data,
  })

  const generate = useMutation({
    mutationFn: async () =>
      (await api.post<{ created: number }>('/invoices/generate-missing', { client_id: clientId })).data,
    onSuccess: (d) => {
      setMessage(`${d.created} invoice(s) created`)
      queryClient.invalidateQueries({ queryKey: ['client-invoices', clientId] })
    },
    onError: (e) => setMessage(errorMessage(e)),
  })

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-xs text-brown-mid">{message}</span>
        <Button intent="accent" onClick={() => generate.mutate()} disabled={generate.isPending}>
          Generate missing invoices
        </Button>
      </div>
      {!invoices?.length ? (
        <Panel><EmptyState title="No invoices" hint="Invoices are generated from active subscriptions." /></Panel>
      ) : (
        <InvoiceTable invoices={invoices} onChanged={() => queryClient.invalidateQueries({ queryKey: ['client-invoices', clientId] })} />
      )}
    </div>
  )
}

export function InvoiceTable({ invoices, onChanged }: { invoices: InvoiceOut[]; onChanged: () => void }) {
  const mark = useMutation({
    mutationFn: async ({ id, status }: { id: string; status: 'paid' | 'void' }) =>
      api.patch(`/invoices/${id}`, { status }),
    onSuccess: onChanged,
  })
  return (
    <Table head={['Number', 'Client', 'Service', 'Period', 'Issued', 'Amount', 'Status', '']}>
      {invoices.map((inv) => (
        <tr key={inv.id}>
          <td className="px-4 py-2.5 font-mono text-xs">{inv.number}</td>
          <td className="px-4 py-2.5">
            <Link to={`/clients/${inv.client_id}`} className="text-orange-deep hover:text-orange">{inv.client_name}</Link>
          </td>
          <td className="px-4 py-2.5 text-xs">{inv.service_name}</td>
          <td className="px-4 py-2.5 font-mono text-xs">{inv.period_label}</td>
          <td className="px-4 py-2.5 font-mono text-xs">{fullDate(inv.issue_date)}</td>
          <td className="px-4 py-2.5 font-mono text-xs">{rupees(inv.amount)}</td>
          <td className="px-4 py-2.5">
            <Badge tone={inv.status === 'paid' ? 'active' : inv.overdue ? 'pending' : 'draft'}>
              {inv.overdue ? 'Overdue' : inv.status === 'due' ? 'Due' : inv.status === 'paid' ? 'Paid' : 'Void'}
            </Badge>
          </td>
          <td className="px-4 py-2.5 text-right whitespace-nowrap">
            {inv.status === 'due' && (
              <>
                <Button className="!px-2 !py-1 text-xs" onClick={() => mark.mutate({ id: inv.id, status: 'paid' })}>
                  Mark paid
                </Button>{' '}
                <Button intent="danger" className="!px-2 !py-1 text-xs" onClick={() => mark.mutate({ id: inv.id, status: 'void' })}>
                  Void
                </Button>
              </>
            )}
          </td>
        </tr>
      ))}
    </Table>
  )
}

// ---------------------------------------------------------------- subscriptions

function SubscriptionsTab({ clientId }: { clientId: string }) {
  const queryClient = useQueryClient()
  const [adding, setAdding] = useState(false)
  const [serviceId, setServiceId] = useState('')
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10))
  const [discount, setDiscount] = useState('0')
  const [error, setError] = useState<string | null>(null)

  const { data: subs } = useQuery({
    queryKey: ['client-subs', clientId],
    queryFn: async () => (await api.get<SubscriptionOut[]>(`/clients/${clientId}/subscriptions`)).data,
  })
  const { data: services } = useQuery({
    queryKey: ['services', '', ''],
    queryFn: async () => (await api.get<Page<ServiceOut>>('/services', { params: { limit: 200 } })).data,
    enabled: adding,
  })

  const add = useMutation({
    mutationFn: async () =>
      api.post(`/clients/${clientId}/subscriptions`, {
        service_id: serviceId,
        start_date: startDate,
        discount_pct: discount || '0',
      }),
    onSuccess: () => {
      setAdding(false)
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['client-subs', clientId] })
      queryClient.invalidateQueries({ queryKey: ['client', clientId] })
    },
    onError: (e) => setError(errorMessage(e)),
  })

  const end = useMutation({
    mutationFn: async (id: string) => api.patch(`/subscriptions/${id}`, { status: 'ended' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['client-subs', clientId] }),
  })

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button intent="accent" onClick={() => setAdding(true)}>New subscription</Button>
      </div>
      {!subs?.length ? (
        <Panel><EmptyState title="No subscriptions" hint="Subscribing a client promotes them to Customer." /></Panel>
      ) : (
        <Table head={['Service', 'Interval', 'Start', 'Rate', 'Discount', 'Effective', 'Status', '']}>
          {subs.map((s) => (
            <tr key={s.id}>
              <td className="px-4 py-2.5">{s.service_name}</td>
              <td className="px-4 py-2.5 text-xs">{s.billing_interval}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{fullDate(s.start_date)}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{rupees(s.rate)}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{parseFloat(s.discount_pct)}%</td>
              <td className="px-4 py-2.5 font-mono text-xs">{rupees(s.effective_rate)}</td>
              <td className="px-4 py-2.5">
                <Badge tone={s.status === 'active' ? 'active' : 'draft'}>{s.status === 'active' ? 'Active' : 'Ended'}</Badge>
              </td>
              <td className="px-4 py-2.5 text-right">
                {s.status === 'active' && (
                  <Button className="!px-2 !py-1 text-xs" onClick={() => end.mutate(s.id)}>End</Button>
                )}
              </td>
            </tr>
          ))}
        </Table>
      )}
      {adding && (
        <Modal title="New subscription" onClose={() => setAdding(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              add.mutate()
            }}
            className="space-y-4"
          >
            <SelectField label="Service" value={serviceId} onChange={(e) => setServiceId(e.target.value)} required>
              <option value="">Choose a service…</option>
              {services?.items.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {s.billing_interval} · {rupees(s.rate)}
                </option>
              ))}
            </SelectField>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Start date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
              <Field label="Discount %" type="number" min={0} max={100} step="0.01" value={discount} onChange={(e) => setDiscount(e.target.value)} />
            </div>
            <ErrorNote message={error} />
            <div className="flex justify-end gap-3">
              <Button type="button" onClick={() => setAdding(false)}>Cancel</Button>
              <Button intent="accent" type="submit" disabled={add.isPending || !serviceId}>Create subscription</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- enrollments

function EnrollmentsTab({ clientId }: { clientId: string }) {
  const queryClient = useQueryClient()
  const [adding, setAdding] = useState(false)
  const [batchId, setBatchId] = useState('')
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10))
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)

  const { data: enrollments } = useQuery({
    queryKey: ['client-enrollments', clientId],
    queryFn: async () => (await api.get<EnrollmentOut[]>(`/clients/${clientId}/enrollments`)).data,
  })
  const { data: batches } = useQuery({
    queryKey: ['batches-for-enroll'],
    queryFn: async () => (await api.get<Page<BatchOut>>('/batches', { params: { limit: 200 } })).data,
    enabled: adding,
  })

  const add = useMutation({
    mutationFn: async () =>
      (await api.post<EnrollmentOut>('/enrollments', { client_id: clientId, batch_id: batchId, start_date: startDate })).data,
    onSuccess: (d) => {
      setAdding(false)
      setError(null)
      setWarning(d.capacity_warning ?? null)
      queryClient.invalidateQueries({ queryKey: ['client-enrollments', clientId] })
    },
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-xs text-orange-deep">{warning}</span>
        <Button intent="accent" onClick={() => setAdding(true)}>Enroll in batch</Button>
      </div>
      {!enrollments?.length ? (
        <Panel><EmptyState title="No enrollments" /></Panel>
      ) : (
        <Table head={['Batch', 'Code', 'Start date']}>
          {enrollments.map((e) => (
            <tr key={e.id}>
              <td className="px-4 py-2.5">
                <Link to={`/operations/batches/${e.batch_id}`} className="text-orange-deep hover:text-orange">
                  {e.batch_name}
                </Link>
              </td>
              <td className="px-4 py-2.5 font-mono text-xs">{e.batch_code}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{fullDate(e.start_date)}</td>
            </tr>
          ))}
        </Table>
      )}
      {adding && (
        <Modal title="Enroll in batch" onClose={() => setAdding(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              add.mutate()
            }}
            className="space-y-4"
          >
            <SelectField label="Batch" value={batchId} onChange={(e) => setBatchId(e.target.value)} required>
              <option value="">Choose a batch…</option>
              {batches?.items.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} · {b.code} · {b.enrolled_count}/{b.capacity ?? '∞'}
                </option>
              ))}
            </SelectField>
            <Field label="Start date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
            <ErrorNote message={error} />
            <div className="flex justify-end gap-3">
              <Button type="button" onClick={() => setAdding(false)}>Cancel</Button>
              <Button intent="accent" type="submit" disabled={add.isPending || !batchId}>Enroll</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
