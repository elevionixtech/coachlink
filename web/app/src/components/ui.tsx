import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'

// ---------------------------------------------------------------- buttons

type Intent = 'accent' | 'primary' | 'quiet' | 'danger'

const intents: Record<Intent, string> = {
  // orange appears once per screen — the single committing action
  accent: 'bg-orange text-white hover:bg-orange-deep border border-orange hover:border-orange-deep',
  primary: 'bg-brown-deep text-yellow-pale hover:bg-brown border border-brown-deep',
  quiet: 'bg-transparent text-brown border border-gold-soft hover:border-gold',
  danger: 'bg-transparent text-orange-deep border border-gold-soft hover:border-orange-deep',
}

export function Button({
  intent = 'quiet',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { intent?: Intent }) {
  return (
    <button
      className={`rounded-[4px] px-4 py-2 text-sm font-semibold transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${intents[intent]} ${className}`}
      {...props}
    />
  )
}

// ---------------------------------------------------------------- typography

export function Eyebrow({ children }: { children: ReactNode }) {
  return <div className="eyebrow">{children}</div>
}

export function SealHeading({ children, eyebrow }: { children: ReactNode; eyebrow?: string }) {
  return (
    <div className="mb-6">
      {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
      <h1 className="seal font-display text-2xl font-extrabold tracking-tight mt-1">{children}</h1>
    </div>
  )
}

// ---------------------------------------------------------------- surfaces

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-yellow-card border border-gold-soft rounded-xl ${className}`}>
      {children}
    </div>
  )
}

export function StatCard({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Panel className="p-4">
      <div className="eyebrow">{label}</div>
      <div className="font-display text-[28px] font-extrabold tracking-tight mt-1">{value}</div>
      {hint && <div className="font-mono text-[11px] text-brown-mid mt-1">{hint}</div>}
    </Panel>
  )
}

// ---------------------------------------------------------------- feedback

const badgeStyles: Record<string, string> = {
  active: 'text-[#7A5E10] bg-[rgba(242,194,48,.18)] border-[rgba(201,151,28,.55)]',
  pending: 'text-orange-deep bg-[rgba(229,114,0,.08)] border-[rgba(229,114,0,.4)]',
  draft: 'text-brown-mid bg-white border-gold-soft',
}

export function Badge({ tone = 'draft', children }: { tone?: 'active' | 'pending' | 'draft'; children: ReactNode }) {
  return (
    <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-medium ${badgeStyles[tone]}`}>
      {children}
    </span>
  )
}

export function statusTone(status: string): 'active' | 'pending' | 'draft' {
  if (['active', 'paid', 'Customer'].includes(status)) return 'active'
  if (['due', 'overdue', 'upcoming', 'expired', 'Lead', 'Prospect'].includes(status)) return 'pending'
  return 'draft'
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="text-center py-14">
      <div className="font-display font-bold text-lg text-brown-mid">{title}</div>
      {hint && <p className="text-sm text-brown-mid mt-1">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

// ---------------------------------------------------------------- forms

export function Field({
  label,
  hint,
  className = '',
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  return (
    <label className={`block ${className}`}>
      <span className="eyebrow">{label}</span>
      <input
        className="mt-1 w-full rounded-[4px] border border-gold-soft bg-white px-3 py-2 text-sm text-brown"
        {...props}
      />
      {hint && <span className="text-xs text-brown-mid">{hint}</span>}
    </label>
  )
}

export function SelectField({
  label,
  children,
  className = '',
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  return (
    <label className={`block ${className}`}>
      <span className="eyebrow">{label}</span>
      <select
        className="mt-1 w-full rounded-[4px] border border-gold-soft bg-white px-3 py-2 text-sm text-brown"
        {...props}
      >
        {children}
      </select>
    </label>
  )
}

/** A dropdown of checkboxes for choosing several options at once. Closes on outside
 *  click. The `field` variant is a bordered control; the `header` variant renders as a
 *  clickable table-column header that turns orange while a filter is applied. */
export function MultiSelect({
  label,
  options,
  selected,
  onChange,
  variant = 'field',
}: {
  label: string
  options: { value: string; label: string }[]
  selected: string[]
  onChange: (values: string[]) => void
  variant?: 'field' | 'header'
}) {
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    // The menu renders in a portal (so the table's overflow can't clip it); keep it
    // anchored under the trigger and dismiss it on an outside click.
    const place = () => {
      const r = triggerRef.current?.getBoundingClientRect()
      if (r) setPos({ top: r.bottom + 4, left: r.left })
    }
    place()
    const onDoc = (e: MouseEvent) => {
      const t = e.target as Node
      if (!triggerRef.current?.contains(t) && !menuRef.current?.contains(t)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      window.removeEventListener('resize', place)
      window.removeEventListener('scroll', place, true)
    }
  }, [open])

  const toggle = (value: string, on: boolean) =>
    onChange(on ? [...selected, value] : selected.filter((v) => v !== value))

  const trigger =
    variant === 'header'
      ? `eyebrow inline-flex items-center gap-1 cursor-pointer font-medium ${
          selected.length ? 'text-orange-deep' : ''
        }`
      : `rounded-[4px] border bg-white px-3 py-2 text-sm cursor-pointer ${
          selected.length ? 'border-brown-deep text-brown' : 'border-gold-soft text-brown-mid'
        }`

  return (
    <span className="inline-block">
      <button ref={triggerRef} type="button" onClick={() => setOpen((o) => !o)} className={trigger}>
        {label}
        {selected.length > 0 && ` · ${selected.length}`}
        <span className={variant === 'header' ? '' : 'ml-1 text-brown-mid'}>▾</span>
      </button>
      {open &&
        pos &&
        createPortal(
          <div
            ref={menuRef}
            style={{ position: 'fixed', top: pos.top, left: pos.left }}
            className="z-50 max-h-72 w-64 overflow-auto rounded-[4px] border border-gold-soft bg-white p-2 text-left text-sm normal-case tracking-normal text-brown shadow-lg"
          >
            {options.length === 0 ? (
              <div className="px-1 py-1 text-xs text-brown-mid">No options</div>
            ) : (
              options.map((o) => (
                <label
                  key={o.value}
                  className="flex items-center gap-2 rounded-[3px] px-1 py-1 text-sm cursor-pointer hover:bg-yellow-pale"
                >
                  <input
                    type="checkbox"
                    className="accent-orange"
                    checked={selected.includes(o.value)}
                    onChange={(e) => toggle(o.value, e.target.checked)}
                  />
                  {o.label}
                </label>
              ))
            )}
            {selected.length > 0 && (
              <button
                type="button"
                onClick={() => onChange([])}
                className="mt-1 w-full px-1 py-1 text-left text-xs text-orange-deep cursor-pointer"
              >
                Clear selection
              </button>
            )}
          </div>,
          document.body,
        )}
    </span>
  )
}

export function TextArea({
  label,
  className = '',
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }) {
  return (
    <label className={`block ${className}`}>
      <span className="eyebrow">{label}</span>
      <textarea
        className="mt-1 w-full rounded-[4px] border border-gold-soft bg-white px-3 py-2 text-sm text-brown"
        rows={3}
        {...props}
      />
    </label>
  )
}

// ---------------------------------------------------------------- modal

export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string
  onClose: () => void
  children: ReactNode
  wide?: boolean
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-[rgba(51,32,13,.42)] p-6"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className={`mt-10 w-full ${wide ? 'max-w-2xl' : 'max-w-md'} rounded-xl bg-yellow-card border border-gold-soft shadow-[0_1px_2px_rgba(51,32,13,.06),0_10px_28px_-14px_rgba(51,32,13,.24)]`}
      >
        <div className="flex items-center justify-between border-b border-gold-soft px-5 py-3">
          <h2 className="font-display text-lg font-bold">{title}</h2>
          <button onClick={onClose} className="text-brown-mid hover:text-brown text-xl leading-none cursor-pointer" aria-label="Close">
            ×
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- table

export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <Panel className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gold-soft">
            {head.map((h, i) => (
              <th key={i} className="eyebrow px-4 py-2.5 text-left font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white/40 divide-y divide-hairline">{children}</tbody>
      </table>
    </Panel>
  )
}

export function ErrorNote({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <div className="rounded-[4px] border border-[rgba(229,114,0,.4)] bg-[rgba(229,114,0,.08)] px-3 py-2 text-sm text-orange-deep">
      {message}
    </div>
  )
}

export function Spinner() {
  return <div className="py-10 text-center font-mono text-xs text-brown-mid">Loading…</div>
}
