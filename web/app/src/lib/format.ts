// Money carries the ₹ symbol with Indian digit grouping; dates are full and
// explicit ("24 Jul 2026") — per the Elevionix content rules.

const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })

export function rupees(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (Number.isNaN(n)) return '—'
  return `₹${inr.format(n)}`
}

export function fullDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(`${iso}T00:00:00`)
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function shortTime(t: string | null | undefined): string {
  if (!t) return '—'
  const [h, m] = t.split(':').map(Number)
  const am = h < 12
  const hour = h % 12 === 0 ? 12 : h % 12
  return `${hour}:${String(m).padStart(2, '0')} ${am ? 'am' : 'pm'}`
}

export function age(dob: string | null | undefined): number | null {
  if (!dob) return null
  const b = new Date(`${dob}T00:00:00`)
  const now = new Date()
  let years = now.getFullYear() - b.getFullYear()
  if (now.getMonth() < b.getMonth() || (now.getMonth() === b.getMonth() && now.getDate() < b.getDate())) years--
  return years
}
