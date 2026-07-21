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

export function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <Panel className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gold-soft">
            {head.map((h) => (
              <th key={h} className="eyebrow px-4 py-2.5 text-left font-medium">
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
