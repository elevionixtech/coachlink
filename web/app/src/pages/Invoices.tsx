import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { InvoicePage } from '../api/types'
import { rupees } from '../lib/format'
import { Button, EmptyState, Panel, SealHeading, Spinner, StatCard } from '../components/ui'
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
          <Button intent="accent" onClick={() => generate.mutate()} disabled={generate.isPending}>
            {generate.isPending ? 'Generating…' : 'Generate missing invoices'}
          </Button>
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
    </div>
  )
}
