// A proper generated PDF of an invoice (not a print of the web page), built with
// @react-pdf/renderer. Lazy-loaded — import this module only when the user downloads,
// so the ~1 MB renderer stays out of the main bundle.
import { Document, Image, Page, StyleSheet, Text, View, pdf } from '@react-pdf/renderer'
import QRCode from 'qrcode'
import type { InvoiceDocumentOut } from '../api/types'

// The built-in PDF fonts (Helvetica) have no rupee glyph, so amounts read "Rs." with
// the same Indian digit grouping the app uses on screen.
const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 })
function money(v: string | number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  const n = typeof v === 'string' ? parseFloat(v) : v
  return Number.isNaN(n) ? '—' : `Rs. ${inr.format(n)}`
}
function fdate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

const C = { text: '#3a2c1a', mid: '#7a5a32', muted: '#948468', hair: '#e7dcc4', deep: '#33200d' }

const s = StyleSheet.create({
  page: { paddingVertical: 44, paddingHorizontal: 48, fontFamily: 'Helvetica', fontSize: 10, color: C.text },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  orgName: { fontFamily: 'Helvetica-Bold', fontSize: 18, marginBottom: 6, lineHeight: 1 },
  small: { fontSize: 9, color: C.mid, lineHeight: 1.35, marginBottom: 1 },
  mono: { fontFamily: 'Courier' },
  label: { fontSize: 8, letterSpacing: 1, color: C.muted, textTransform: 'uppercase' },
  rightBlock: { alignItems: 'flex-end' },
  number: { fontFamily: 'Courier-Bold', fontSize: 14, marginTop: 2 },
  status: { marginTop: 6, fontFamily: 'Helvetica-Bold', fontSize: 9, letterSpacing: 1, color: C.deep },
  rule: { borderBottomWidth: 1, borderBottomColor: C.hair, marginVertical: 18 },
  cols: { flexDirection: 'row', justifyContent: 'space-between' },
  colHalf: { width: '48%' },
  billName: { fontFamily: 'Helvetica-Bold', fontSize: 11, marginTop: 3, marginBottom: 2, lineHeight: 1 },
  tableHead: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: C.hair, paddingBottom: 4, marginTop: 28 },
  thDesc: { flex: 1 }, thAmt: { width: 110, textAlign: 'right' },
  lineRow: { flexDirection: 'row', paddingVertical: 14 },
  lineTitle: { fontFamily: 'Helvetica-Bold', fontSize: 11 },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 2, borderTopColor: C.deep, paddingTop: 8, marginTop: 2 },
  totalLabel: { fontFamily: 'Helvetica-Bold', fontSize: 11 },
  totalAmt: { fontFamily: 'Courier-Bold', fontSize: 13 },
  payBox: { marginTop: 30, borderWidth: 1, borderColor: C.hair, borderRadius: 4, padding: 14 },
  payGrid: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 8 },
  payCol: { width: '31%' },
  payHead: { fontFamily: 'Helvetica-Bold', fontSize: 10, marginBottom: 3 },
  qr: { width: 96, height: 96 },
  footer: { marginTop: 34, fontSize: 8, color: C.muted },
})

function statusLabel(inv: InvoiceDocumentOut): string {
  if (inv.overdue) return 'OVERDUE'
  return inv.status === 'due' ? 'DUE' : inv.status === 'paid' ? 'PAID' : 'VOID'
}

function InvoiceDoc({ inv, qr }: { inv: InvoiceDocumentOut; qr: string | null }) {
  const b = inv.bill_to
  const o = inv.issued_by
  const p = inv.payment
  const line = inv.service_name || inv.description || 'Invoice'
  const paidLess = inv.paid_amount != null && Number(inv.paid_amount) !== Number(inv.amount)
  const hasDiscount = inv.subtotal != null && Number(inv.subtotal) > Number(inv.amount)
  const discountAmt = hasDiscount ? Number(inv.subtotal) - Number(inv.amount) : 0
  const discountPct = hasDiscount ? Math.round((discountAmt / Number(inv.subtotal)) * 100) : 0
  return (
    <Document title={`Invoice ${inv.number}`}>
      <Page size="A4" style={s.page}>
        {/* header */}
        <View style={s.row}>
          <View style={{ maxWidth: '60%' }}>
            <Text style={s.orgName}>{o.name}</Text>
            {!!o.address && <Text style={s.small}>{o.address}</Text>}
            {!!o.email && <Text style={s.small}>{o.email}</Text>}
            {!!o.phone && <Text style={[s.small, s.mono]}>{o.phone}</Text>}
            {!!o.gstin && <Text style={[s.small, s.mono]}>GSTIN {o.gstin}</Text>}
          </View>
          <View style={s.rightBlock}>
            <Text style={s.label}>Invoice</Text>
            <Text style={s.number}>{inv.number}</Text>
            <Text style={s.status}>{statusLabel(inv)}</Text>
          </View>
        </View>

        <View style={s.rule} />

        {/* parties */}
        <View style={s.cols}>
          <View style={s.colHalf}>
            <Text style={s.label}>Billed to</Text>
            <Text style={s.billName}>{b.name}</Text>
            {!!b.company_name && <Text>{b.company_name}</Text>}
            {!!b.address && <Text>{b.address}</Text>}
            {!!b.email && <Text>{b.email}</Text>}
            {!!b.phone && <Text style={s.mono}>{b.phone}</Text>}
            {!!b.gstin && <Text style={s.mono}>GSTIN {b.gstin}</Text>}
          </View>
          <View style={[s.colHalf, { alignItems: 'flex-end' }]}>
            <Text style={s.label}>Issued</Text>
            <Text style={s.mono}>{fdate(inv.issue_date)}</Text>
            {!!inv.subscription_id && (
              <View style={{ alignItems: 'flex-end', marginTop: 8 }}>
                <Text style={s.label}>Period</Text>
                <Text style={s.mono}>{fdate(inv.period_start)} – {fdate(inv.period_end)}</Text>
              </View>
            )}
          </View>
        </View>

        {/* line item */}
        <View style={s.tableHead}>
          <Text style={[s.label, s.thDesc]}>Description</Text>
          <Text style={[s.label, s.thAmt]}>Amount</Text>
        </View>
        <View style={s.lineRow}>
          <View style={s.thDesc}>
            <Text style={s.lineTitle}>{line}</Text>
            {!!inv.service_description && <Text style={{ marginTop: 2 }}>{inv.service_description}</Text>}
            {!!inv.pricing_option_name && <Text style={{ marginTop: 2, color: C.mid }}>{inv.pricing_option_name}</Text>}
            {inv.includes.map((it) => (
              <Text key={it} style={{ marginTop: 2 }}>{it}</Text>
            ))}
          </View>
          <Text style={[s.thAmt, s.mono]}>{money(hasDiscount ? inv.subtotal : inv.amount)}</Text>
        </View>

        {/* discount */}
        {hasDiscount && (
          <View style={{ marginTop: 2 }}>
            <View style={s.row}>
              <Text style={{ color: C.muted }}>Subtotal</Text>
              <Text style={s.mono}>{money(inv.subtotal)}</Text>
            </View>
            <View style={[s.row, { marginTop: 2 }]}>
              <Text style={{ color: C.muted }}>
                {inv.pricing_option_name
                  ? `${inv.pricing_option_name} (${discountPct}% off)`
                  : `Discount (${discountPct}%)`}
              </Text>
              <Text style={[s.mono, { color: C.muted }]}>- {money(discountAmt)}</Text>
            </View>
          </View>
        )}

        {/* total */}
        <View style={s.totalRow}>
          <Text style={s.totalLabel}>{inv.status === 'paid' ? 'Total' : 'Total due'}</Text>
          <Text style={s.totalAmt}>{money(inv.amount)}</Text>
        </View>
        {inv.status === 'paid' && inv.paid_amount != null && (
          <View style={{ marginTop: 4 }}>
            <View style={s.row}>
              <Text>Paid{inv.payment_method ? ` via ${inv.payment_method}` : ''}</Text>
              <Text style={s.mono}>{money(inv.paid_amount)}</Text>
            </View>
            {inv.payment_date && (
              <View style={[s.row, { marginTop: 2 }]}>
                <Text style={{ color: C.muted }}>Payment date</Text>
                <Text style={[s.mono, { color: C.muted }]}>{fdate(inv.payment_date)}</Text>
              </View>
            )}
            {paidLess && (
              <View style={[s.row, { marginTop: 2 }]}>
                <Text style={{ color: C.muted }}>
                  {Number(inv.paid_amount) < Number(inv.amount) ? 'Balance' : 'Overpaid'}
                </Text>
                <Text style={[s.mono, { color: C.muted }]}>
                  {money(Math.abs(Number(inv.amount) - Number(inv.paid_amount)))}
                </Text>
              </View>
            )}
          </View>
        )}

        {/* payment options (unpaid only) */}
        {inv.status === 'due' && (!!p.bank_account_number || !!p.upi_id) && (
          <View style={s.payBox}>
            <Text style={s.label}>Pay online — {money(inv.amount)} due</Text>
            <View style={s.payGrid}>
              {!!p.bank_account_number && (
                <View style={s.payCol}>
                  <Text style={s.payHead}>Bank transfer</Text>
                  {!!p.bank_account_name && <Text>{p.bank_account_name}</Text>}
                  <Text style={s.mono}>A/C {p.bank_account_number}</Text>
                  {!!p.bank_ifsc && <Text style={s.mono}>IFSC {p.bank_ifsc}</Text>}
                  {!!p.bank_name && <Text>{p.bank_name}</Text>}
                </View>
              )}
              {!!p.upi_id && (
                <View style={s.payCol}>
                  <Text style={s.payHead}>UPI</Text>
                  <Text style={s.mono}>{p.upi_id}</Text>
                </View>
              )}
              {!!qr && (
                <View style={s.payCol}>
                  <Text style={s.payHead}>Scan to pay</Text>
                  <Image style={s.qr} src={qr} />
                </View>
              )}
            </View>
          </View>
        )}

        <Text style={s.footer}>
          {inv.currency} · Invoice {inv.number}
          {inv.subscription_id ? ` for the period ${fdate(inv.period_start)} to ${fdate(inv.period_end)}.` : '.'}
        </Text>
      </Page>
    </Document>
  )
}

export async function downloadInvoicePdf(inv: InvoiceDocumentOut): Promise<void> {
  // The QR encodes a UPI payment with the amount pre-filled — same as on screen.
  let qr: string | null = null
  const p = inv.payment
  if (inv.status === 'due' && p.show_qr && p.upi_id) {
    const link =
      `upi://pay?pa=${encodeURIComponent(p.upi_id)}&pn=${encodeURIComponent(inv.issued_by.name)}` +
      `&am=${inv.amount}&cu=${inv.currency}&tn=${encodeURIComponent('Invoice ' + inv.number)}`
    qr = await QRCode.toDataURL(link, { width: 240, margin: 1 }).catch(() => null)
  }
  const blob = await pdf(<InvoiceDoc inv={inv} qr={qr} />).toBlob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  // Include the recipient's name so the file is easy to identify; strip characters that
  // aren't valid in filenames.
  const who = (inv.bill_to.name || '').replace(/[/\\:*?"<>|]/g, '').trim()
  a.download = who ? `${inv.number} - ${who}.pdf` : `${inv.number}.pdf`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
