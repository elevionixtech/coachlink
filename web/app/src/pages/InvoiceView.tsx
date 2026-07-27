import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import QRCode from 'qrcode'
import { api } from '../api/client'
import type { InvoiceDocumentOut } from '../api/types'
import { fullDate, rupees } from '../lib/format'
import { Badge, Button, ErrorNote, Panel, Spinner } from '../components/ui'

function PaymentSection({ inv }: { inv: InvoiceDocumentOut }) {
  const p = inv.payment
  const hasBank = !!p.bank_account_number
  const hasUpi = !!p.upi_id
  if (!hasBank && !hasUpi) return null

  // UPI deep link with the amount pre-filled — a client scans and confirms.
  const upiLink = hasUpi
    ? `upi://pay?pa=${encodeURIComponent(p.upi_id!)}&pn=${encodeURIComponent(inv.issued_by.name)}` +
      `&am=${inv.amount}&cu=${inv.currency}&tn=${encodeURIComponent('Invoice ' + inv.number)}`
    : ''

  const [qr, setQr] = useState<string>('')
  useEffect(() => {
    if (p.show_qr && upiLink) {
      QRCode.toDataURL(upiLink, { width: 220, margin: 1 }).then(setQr).catch(() => setQr(''))
    } else {
      setQr('')
    }
  }, [upiLink, p.show_qr])

  return (
    <div className="print-keep mt-8 rounded-md border border-hairline p-4">
      <div className="eyebrow mb-3">Pay online — {rupees(inv.amount)} due</div>
      <div className="grid gap-6 sm:grid-cols-3">
        {hasBank && (
          <div className="text-sm">
            <div className="font-display font-bold mb-1">Bank transfer</div>
            {p.bank_account_name && <div>{p.bank_account_name}</div>}
            <div className="font-mono text-xs">A/C {p.bank_account_number}</div>
            {p.bank_ifsc && <div className="font-mono text-xs">IFSC {p.bank_ifsc}</div>}
            {p.bank_name && <div>{p.bank_name}</div>}
          </div>
        )}
        {hasUpi && (
          <div className="text-sm">
            <div className="font-display font-bold mb-1">UPI</div>
            <div className="font-mono text-xs break-all">{p.upi_id}</div>
          </div>
        )}
        {qr && (
          <div className="text-sm">
            <div className="font-display font-bold mb-1">Scan to pay</div>
            <img src={qr} alt="UPI payment QR" className="h-32 w-32" />
          </div>
        )}
      </div>
    </div>
  )
}

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
  const [downloading, setDownloading] = useState(false)

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

  const hasDiscount = inv.subtotal != null && Number(inv.subtotal) > Number(inv.amount)
  const discountAmt = hasDiscount ? Number(inv.subtotal) - Number(inv.amount) : 0
  const discountPct = hasDiscount ? Math.round((discountAmt / Number(inv.subtotal)) * 100) : 0

  return (
    <div>
      <div className="print-hide mb-4 flex items-center justify-between">
        <Link to="/invoices" className="text-sm text-orange-deep hover:text-orange">
          ← Back to invoices
        </Link>
        {/* A real generated PDF, not a print of the page. The renderer is lazy-loaded
            on click so it stays out of the main bundle. */}
        <Button
          intent="accent"
          disabled={downloading}
          onClick={async () => {
            setDownloading(true)
            try {
              const { downloadInvoicePdf } = await import('../lib/invoicePdf')
              await downloadInvoicePdf(inv)
            } finally {
              setDownloading(false)
            }
          }}
        >
          {downloading ? 'Preparing…' : 'Download PDF'}
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
            {inv.subscription_id && (
              <div>
                <span className="eyebrow">Period</span>
                <div className="font-mono text-sm">
                  {fullDate(inv.period_start)} – {fullDate(inv.period_end)}
                </div>
                {inv.period_end_adjusted && (
                  <div className="text-[10px] uppercase tracking-wide text-muted">adjusted</div>
                )}
              </div>
            )}
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
                <div className="font-display font-bold whitespace-pre-line">{inv.service_name ?? inv.description}</div>
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
              <td className="py-4 text-right font-mono">
                {rupees(hasDiscount ? inv.subtotal : inv.amount)}
              </td>
            </tr>
          </tbody>
        </table>

        {hasDiscount && (
          <div className="print-keep mt-2 space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-muted">Subtotal</span>
              <span className="font-mono">{rupees(inv.subtotal)}</span>
            </div>
            <div className="flex justify-between text-sm text-muted">
              <span>
                {inv.pricing_option_name
                  ? `${inv.pricing_option_name} (${discountPct}% off)`
                  : `Discount (${discountPct}%)`}
              </span>
              <span className="font-mono">− {rupees(String(discountAmt))}</span>
            </div>
          </div>
        )}

        <div className="print-keep mt-2 border-t-2 border-brown-deep pt-3 flex justify-between">
          <span className="font-display font-bold">
            {inv.status === 'paid' ? 'Total' : 'Total due'}
          </span>
          <span className="font-mono text-lg font-bold">{rupees(inv.amount)}</span>
        </div>

        {inv.status === 'paid' && inv.paid_amount != null && (
          <div className="print-keep mt-1 space-y-0.5 text-sm">
            <div className="flex justify-between">
              <span>Paid</span>
              <span className="font-mono">{rupees(inv.paid_amount)}</span>
            </div>
            {inv.paid_amount !== inv.amount && (
              <div className="flex justify-between text-muted">
                <span>{Number(inv.paid_amount) < Number(inv.amount) ? 'Balance' : 'Overpaid'}</span>
                <span className="font-mono">
                  {rupees(String(Math.abs(Number(inv.amount) - Number(inv.paid_amount))))}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Payment options only matter while the invoice is unpaid. */}
        {(inv.status === 'due') && <PaymentSection inv={inv} />}

        <p className="mt-8 text-xs text-muted">
          {inv.subscription_id
            ? `${inv.currency} · Invoice ${inv.number} for the period ${fullDate(inv.period_start)} to ${fullDate(inv.period_end)}.`
            : `${inv.currency} · Invoice ${inv.number}.`}
        </p>
      </Panel>
    </div>
  )
}
