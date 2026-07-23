import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { InvoiceDocumentOut } from '../api/types'
import { fullDate, rupees } from '../lib/format'
import { Badge, Button, ErrorNote, Panel, Spinner } from '../components/ui'

function Party({ label, party }: { label: string; party: InvoiceDocumentOut['bill_to'] }) {
  return (
    <div>
      <span className="eyebrow">{label}</span>
      <div className="mt-1 font-display font-bold">{party.name}</div>
      {party.company_name && <div className="text-sm">{party.company_name}</div>}
      {party.address && <div className="text-sm whitespace-pre-line">{party.address}</div>}
      {party.email && <div className="text-sm">{party.email}</div>}
      {party.phone && <div className="font-mono text-xs">{party.phone}</div>}
      {party.gstin && (
        <div className="font-mono text-xs">
          GSTIN <span>{party.gstin}</span>
        </div>
      )}
    </div>
  )
}

export default function InvoiceView() {
  const { id } = useParams<{ id: string }>()

  const { data: inv, isLoading, error } = useQuery({
    queryKey: ['invoice', id],
    queryFn: async () => (await api.get<InvoiceDocumentOut>(`/invoices/${id}`)).data,
  })

  if (isLoading) return <Spinner />
  if (error || !inv) {
    return (
      <div>
        <ErrorNote message="That invoice could not be loaded." />
        <Link to="/invoices" className="text-sm text-orange-deep hover:text-orange">
          Back to invoices
        </Link>
      </div>
    )
  }

  const statusLabel = inv.overdue
    ? 'Overdue'
    : inv.status === 'due'
      ? 'Due'
      : inv.status === 'paid'
        ? 'Paid'
        : 'Void'

  return (
    <div>
      <div className="print-hide mb-4 flex items-center justify-between">
        <Link to="/invoices" className="text-sm text-orange-deep hover:text-orange">
          ← Back to invoices
        </Link>
        {/* The browser's print dialog is the PDF writer — "Save as PDF" in the
            destination list. No server-side renderer, so nothing to install. */}
        <Button intent="accent" onClick={() => window.print()}>
          Download PDF
        </Button>
      </div>

      <Panel className="print-sheet mx-auto max-w-3xl p-8">
        <div className="flex items-start justify-between gap-8">
          <div>
            <div className="font-display text-2xl font-bold">{inv.issued_by.name}</div>
            {inv.issued_by.address && (
              <div className="mt-1 text-sm whitespace-pre-line">{inv.issued_by.address}</div>
            )}
            {inv.issued_by.email && <div className="text-sm">{inv.issued_by.email}</div>}
            {inv.issued_by.gstin && (
              <div className="font-mono text-xs">GSTIN {inv.issued_by.gstin}</div>
            )}
          </div>
          <div className="text-right">
            <span className="eyebrow">Invoice</span>
            <div className="font-mono text-lg font-bold">{inv.number}</div>
            <div className="mt-2">
              <Badge tone={inv.status === 'paid' ? 'active' : inv.overdue ? 'pending' : 'draft'}>
                {statusLabel}
              </Badge>
            </div>
          </div>
        </div>

        <div className="my-6 h-px bg-hairline" />

        <div className="grid grid-cols-2 gap-8">
          <Party label="Billed to" party={inv.bill_to} />
          <div className="space-y-2 text-right">
            <div>
              <span className="eyebrow">Issued</span>
              <div className="font-mono text-sm">{fullDate(inv.issue_date)}</div>
            </div>
            <div>
              <span className="eyebrow">Period</span>
              <div className="font-mono text-sm">
                {fullDate(inv.period_start)} – {fullDate(inv.period_end)}
              </div>
              {inv.period_end_adjusted && (
                <div className="text-[10px] uppercase tracking-wide text-muted">adjusted</div>
              )}
            </div>
          </div>
        </div>

        <table className="mt-8 w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-hairline">
              <th className="pb-2 eyebrow font-normal">Description</th>
              <th className="pb-2 eyebrow font-normal text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            <tr className="print-keep align-top">
              <td className="py-4">
                <div className="font-display font-bold">{inv.service_name}</div>
                {/* No period here — the dates are already stated under Period, and
                    repeating "Jun 2026" beside them reads as a second, vaguer date.
                    An empty description is stored as "" on some rows, so a falsy
                    check rather than a null check. */}
                {inv.service_description && (
                  <div className="mt-0.5 text-sm">{inv.service_description}</div>
                )}
                {inv.pricing_option_name && (
                  <div className="mt-0.5 text-sm text-muted">{inv.pricing_option_name}</div>
                )}
                {inv.includes.length > 0 && (
                  <ul className="mt-2 space-y-0.5 text-sm">
                    {inv.includes.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                )}
              </td>
              <td className="py-4 text-right font-mono">{rupees(inv.amount)}</td>
            </tr>
          </tbody>
        </table>

        <div className="print-keep mt-2 border-t-2 border-brown-deep pt-3 flex justify-between">
          <span className="font-display font-bold">Total due</span>
          <span className="font-mono text-lg font-bold">{rupees(inv.amount)}</span>
        </div>

        <p className="mt-8 text-xs text-muted">
          {inv.currency} · Invoice {inv.number} for the period{' '}
          {fullDate(inv.period_start)} to {fullDate(inv.period_end)}.
        </p>
      </Panel>
    </div>
  )
}
