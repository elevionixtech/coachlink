import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { ClientOut, InvoiceDocumentOut, InvoicePage, Page } from '../api/types'
import { rupees } from '../lib/format'
import {
  Button, EmptyState, ErrorNote, Field, Modal, Panel, SealHeading, SelectField, Spinner,
  StatCard, TextArea,
} from '../components/ui'
import { InvoiceTable } from './ClientDetail'

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'due', label: 'Due' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'paid', label: 'Paid' },
  { value: 'void', label: 'Void' },
]

export default function Invoices() {
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['invoices', status, q],
    queryFn: async () =>
      (
        await api.get<InvoicePage>('/invoices', {
          params: { status: status || undefined, q: q || undefined, limit: 100 },
        })
      ).data,
  })

  const generate = useMutation({
    mutationFn: async () => (await api.post<{ created: number }>('/invoices/generate-missing', {})).data,
    onSuccess: (d) => {
      setMessage(`${d.created} invoice(s) created`)
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    },
    onError: (e) => setMessage(errorMessage(e)),
  })

  return (
    <div>
      <div className="flex items-start justify-between">
        <SealHeading eyebrow="Billing ledger">Invoices</SealHeading>
        <div className="text-right">
          <div className="flex gap-2">
            <Button onClick={() => setCreating(true)}>New invoice</Button>
            <Button intent="accent" onClick={() => generate.mutate()} disabled={generate.isPending}>
              {generate.isPending ? 'Generating…' : 'Generate missing invoices'}
            </Button>
          </div>
          {message && <div className="mt-1 font-mono text-xs text-brown-mid">{message}</div>}
        </div>
      </div>

      <div className="mb-5 grid max-w-xs grid-cols-1">
        <StatCard label="Outstanding (due)" value={rupees(data?.outstanding_total)} />
      </div>

      <div className="mb-4 flex items-center gap-3">
        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatus(f.value)}
              className={`rounded-[4px] px-3 py-1.5 text-sm cursor-pointer border transition-colors ${
                status === f.value
                  ? 'border-brown-deep bg-brown-deep text-yellow-pale'
                  : 'border-gold-soft bg-white text-brown hover:border-gold'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search number or client"
          className="w-64 rounded-[4px] border border-gold-soft bg-white px-3 py-2 text-sm"
        />
      </div>

      {isLoading ? (
        <Spinner />
      ) : !data?.items.length ? (
        <Panel>
          <EmptyState
            title="No invoices"
            hint="Generate missing invoices to bill active subscriptions for every period to date."
          />
        </Panel>
      ) : (
        <InvoiceTable
          invoices={data.items}
          onChanged={() => queryClient.invalidateQueries({ queryKey: ['invoices'] })}
        />
      )}

      {creating && (
        <AdHocInvoiceModal
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false)
            setMessage('Invoice created')
            queryClient.invalidateQueries({ queryKey: ['invoices'] })
          }}
        />
      )}
    </div>
  )
}

export function AdHocInvoiceModal({
  invoice,
  onClose,
  onSaved,
}: {
  invoice?: InvoiceDocumentOut // when present, edit that invoice instead of creating one
  onClose: () => void
  onSaved: () => void
}) {
  const editing = !!invoice
  const nonClient = editing && !invoice.client_id
  const [recipient, setRecipient] = useState<'client' | 'other'>(nonClient ? 'other' : 'client')
  const [clientId, setClientId] = useState(invoice?.client_id ?? '')
  const [name, setName] = useState(nonClient ? invoice.bill_to.name ?? '' : '')
  const [email, setEmail] = useState(nonClient ? invoice.bill_to.email ?? '' : '')
  const [phone, setPhone] = useState(nonClient ? invoice.bill_to.phone ?? '' : '')
  const [address, setAddress] = useState(nonClient ? invoice.bill_to.address ?? '' : '')
  const [gstin, setGstin] = useState(nonClient ? invoice.bill_to.gstin ?? '' : '')
  const [description, setDescription] = useState(invoice?.description ?? '')
  const [amount, setAmount] = useState(invoice?.amount ?? '')
  const [issueDate, setIssueDate] = useState(invoice?.issue_date ?? new Date().toISOString().slice(0, 10))
  const [error, setError] = useState<string | null>(null)

  const { data: clients } = useQuery({
    queryKey: ['clients-for-invoice'],
    queryFn: async () => (await api.get<Page<ClientOut>>('/clients', { params: { limit: 200 } })).data,
  })

  const isClient = recipient === 'client'
  const recipientReady = isClient ? !!clientId : !!name

  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        // Exactly one of client_id / bill_to_name, matching the server contract.
        client_id: isClient ? clientId : null,
        bill_to_name: isClient ? null : name,
        bill_to_email: isClient ? null : email || null,
        bill_to_phone: isClient ? null : phone || null,
        bill_to_address: isClient ? null : address || null,
        bill_to_gstin: isClient ? null : gstin || null,
        description,
        amount,
        issue_date: issueDate,
      }
      return editing ? api.put(`/invoices/${invoice.id}`, payload) : api.post('/invoices', payload)
    },
    onSuccess: onSaved,
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal title={editing ? 'Edit invoice' : 'New invoice'} onClose={onClose}>
      <form onSubmit={(e) => { e.preventDefault(); save.mutate() }} className="space-y-4">
        <p className="text-sm text-muted">
          A one-off invoice — for a workshop, a joining fee, or anything outside a
          subscription. Bill an existing client or someone with no client record.
        </p>

        <div className="flex gap-1">
          {(['client', 'other'] as const).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRecipient(r)}
              className={`rounded-[4px] px-3 py-1.5 text-sm cursor-pointer border transition-colors ${
                recipient === r
                  ? 'border-brown-deep bg-brown-deep text-yellow-pale'
                  : 'border-gold-soft bg-white text-brown hover:border-gold'
              }`}
            >
              {r === 'client' ? 'Existing client' : 'Someone else'}
            </button>
          ))}
        </div>

        {isClient ? (
          <SelectField label="Client" required value={clientId} onChange={(e) => setClientId(e.target.value)}>
            <option value="">Choose a client…</option>
            {clients?.items.map((c) => (
              <option key={c.id} value={c.id}>{c.name}{c.name_hint ? ` — ${c.name_hint}` : ''}</option>
            ))}
          </SelectField>
        ) : (
          <div className="space-y-4 rounded-lg border border-gold-soft bg-white/50 p-3">
            <Field label="Bill to (name)" required value={name} onChange={(e) => setName(e.target.value)} placeholder="Ravi Kumar" />
            <div className="grid grid-cols-2 gap-4">
              <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              <Field label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </div>
            <Field label="Address" value={address} onChange={(e) => setAddress(e.target.value)} />
            <Field label="GSTIN" value={gstin} onChange={(e) => setGstin(e.target.value)} className="[&>input]:font-mono" hint="If the recipient has one" />
          </div>
        )}

        <TextArea
          label="Description"
          required
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Diwali special workshop — includes mat and refreshments"
        />
        <div className="grid grid-cols-2 gap-4">
          <Field label="Amount (₹)" type="number" min={1} step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} />
          <Field label="Issue date" type="date" required value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
        </div>
        <ErrorNote message={error} />
        <div className="flex justify-end gap-3">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button intent="accent" type="submit" disabled={save.isPending || !recipientReady || !description || !amount}>
            {editing ? 'Save changes' : 'Create invoice'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
