import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type {
  DeliverableIn, Page, PricingOptionOut, ServiceIn, ServiceOut, ServicePricingOptionIn,
} from '../api/types'
import {
  BILLING_INTERVALS, CANCELLATION_POLICIES, DELIVERABLE_UNITS, DELIVERY_MODES,
  SERVICE_TYPES,
} from '../api/types'
import { rupees } from '../lib/format'
import {
  Badge, Button, ErrorNote, Field, Modal, EmptyState, Panel, SealHeading, SelectField,
  Spinner, TextArea,
} from '../components/ui'

function ServiceForm({
  initial,
  onSaved,
  onClose,
}: {
  initial?: ServiceOut
  onSaved: () => void
  onClose: () => void
}) {
  const [form, setForm] = useState<ServiceIn>({
    name: initial?.name ?? '',
    sku: initial?.sku ?? '',
    description: initial?.description ?? '',
    service_type: initial?.service_type ?? 'Subscription',
    delivery_mode: initial?.delivery_mode ?? 'Offline',
    max_capacity: initial?.max_capacity ?? null,
    billing_interval: initial?.billing_interval ?? 'Monthly',
    rate: initial?.rate ?? '0',
    cancellation_policy: initial?.cancellation_policy ?? 'Flexible',
    pricing_options: initial?.pricing_options.map((p) => ({
      pricing_option_id: p.pricing_option_id,
      pricing_mode: p.pricing_mode,
      value: p.value,
    })) ?? [],
    deliverables: initial?.deliverables.map((d) => ({ name: d.name, quantity: d.quantity, unit: d.unit })) ?? [],
  })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof ServiceIn, v: unknown) => setForm((f) => ({ ...f, [k]: v }))

  const save = useMutation({
    mutationFn: async () => {
      if (initial) await api.patch(`/services/${initial.id}`, form)
      else await api.post('/services', form)
    },
    onSuccess: onSaved,
    onError: (e) => setError(errorMessage(e)),
  })

  const setDeliverable = (i: number, patch: Partial<DeliverableIn>) =>
    set('deliverables', form.deliverables!.map((d, j) => (i === j ? { ...d, ...patch } : d)))

  // The org's configurable catalog — no fixed set of tiers any more.
  const catalog = useQuery({
    queryKey: ['pricing-options'],
    queryFn: async () => (await api.get<PricingOptionOut[]>('/pricing-options')).data,
  })
  const priced = form.pricing_options ?? []
  const setPriced = (i: number, patch: Partial<ServicePricingOptionIn>) =>
    set('pricing_options', priced.map((p, j) => (i === j ? { ...p, ...patch } : p)))
  const unpriced = (catalog.data ?? []).filter(
    (o) => !priced.some((p) => p.pricing_option_id === o.id),
  )

  return (
    <Modal title={initial ? 'Edit service' : 'New service'} onClose={onClose} wide>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
        className="space-y-4"
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Hatha Yoga — Monthly" />
          <Field label="SKU" required value={form.sku} onChange={(e) => set('sku', e.target.value)} className="[&>input]:font-mono" hint="Stable billing identifier, unique per organisation" />
          <SelectField label="Service type" value={form.service_type} onChange={(e) => set('service_type', e.target.value)}>
            {SERVICE_TYPES.map((t) => <option key={t}>{t}</option>)}
          </SelectField>
          <SelectField label="Delivery mode" value={form.delivery_mode} onChange={(e) => set('delivery_mode', e.target.value)}>
            {DELIVERY_MODES.map((m) => <option key={m}>{m}</option>)}
          </SelectField>
          <SelectField label="Billing interval" value={form.billing_interval} onChange={(e) => set('billing_interval', e.target.value)}>
            {BILLING_INTERVALS.map((i) => <option key={i}>{i}</option>)}
          </SelectField>
          <Field label="Rate (₹)" type="number" min={0} required value={String(form.rate)} onChange={(e) => set('rate', e.target.value)} />
          <SelectField label="Cancellation policy" value={form.cancellation_policy} onChange={(e) => set('cancellation_policy', e.target.value)}>
            {CANCELLATION_POLICIES.map((p) => <option key={p}>{p}</option>)}
          </SelectField>
          <Field label="Max capacity" type="number" min={0} value={form.max_capacity ?? ''} onChange={(e) => set('max_capacity', e.target.value === '' ? null : Number(e.target.value))} />
        </div>
        <TextArea label="Description" value={form.description ?? ''} onChange={(e) => set('description', e.target.value)} />
        <div>
          <div className="flex items-center justify-between">
            <span className="eyebrow">Pricing options</span>
            <Button
              type="button"
              className="!px-2 !py-1 text-xs"
              disabled={unpriced.length === 0}
              onClick={() =>
                set('pricing_options', [
                  ...priced,
                  { pricing_option_id: unpriced[0].id, pricing_mode: 'discount_pct', value: '0' },
                ])
              }
            >
              Add pricing option
            </Button>
          </div>
          {catalog.data && catalog.data.length === 0 ? (
            <p className="mt-2 text-sm text-muted">
              No pricing options configured yet — add them under Pricing options in the sidebar.
            </p>
          ) : (
            <div className="mt-2 space-y-2">
              {priced.map((p, i) => {
                const isPct = p.pricing_mode === 'discount_pct'
                return (
                  <div key={i} className="flex items-end gap-2">
                    <SelectField
                      label="Option"
                      value={p.pricing_option_id}
                      onChange={(e) => setPriced(i, { pricing_option_id: e.target.value })}
                      className="flex-1"
                    >
                      {catalog.data
                        ?.filter(
                          (o) =>
                            o.id === p.pricing_option_id ||
                            !priced.some((q) => q.pricing_option_id === o.id),
                        )
                        .map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                    </SelectField>
                    <SelectField
                      label="Priced as"
                      value={p.pricing_mode}
                      onChange={(e) => setPriced(i, { pricing_mode: e.target.value as 'discount_pct' | 'fixed_rate' })}
                      className="w-44"
                    >
                      <option value="discount_pct">Discount %</option>
                      <option value="fixed_rate">Fixed rate ₹</option>
                    </SelectField>
                    <Field
                      label={isPct ? 'Discount (%)' : 'Rate (₹)'}
                      type="number"
                      min={0}
                      max={isPct ? 100 : undefined}
                      required
                      value={String(p.value)}
                      onChange={(e) => setPriced(i, { value: e.target.value })}
                      className="w-32"
                    />
                    <Button
                      type="button"
                      intent="danger"
                      className="!px-2 !py-2 text-xs"
                      onClick={() => set('pricing_options', priced.filter((_, j) => j !== i))}
                    >
                      Remove
                    </Button>
                  </div>
                )
              })}
              {priced.length > 0 && (
                <p className="text-xs text-muted">
                  {priced.map((p) => {
                    const option = catalog.data?.find((o) => o.id === p.pricing_option_id)
                    const rate = Number(form.rate)
                    const amount =
                      p.pricing_mode === 'fixed_rate'
                        ? Number(p.value)
                        : Math.round(rate * (1 - Number(p.value) / 100))
                    return `${option?.name ?? 'Option'}: ${rupees(String(amount))}`
                  }).join(' · ')}
                </p>
              )}
            </div>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between">
            <span className="eyebrow">Deliverables</span>
            <Button type="button" className="!px-2 !py-1 text-xs" onClick={() => set('deliverables', [...form.deliverables!, { name: '', quantity: 1, unit: 'sessions' }])}>
              Add deliverable
            </Button>
          </div>
          <div className="mt-2 space-y-2">
            {form.deliverables!.map((d, i) => (
              <div key={i} className="flex items-end gap-2">
                <Field label="Name" required value={d.name} onChange={(e) => setDeliverable(i, { name: e.target.value })} className="flex-1" />
                <Field label="Qty" type="number" min={1} required value={d.quantity} onChange={(e) => setDeliverable(i, { quantity: Number(e.target.value) })} className="w-20" />
                <SelectField label="Unit" value={d.unit} onChange={(e) => setDeliverable(i, { unit: e.target.value })} className="w-32">
                  {DELIVERABLE_UNITS.map((u) => <option key={u}>{u}</option>)}
                </SelectField>
                <Button type="button" intent="danger" className="!px-2 !py-2 text-xs" onClick={() => set('deliverables', form.deliverables!.filter((_, j) => j !== i))}>
                  Remove
                </Button>
              </div>
            ))}
          </div>
        </div>

        <ErrorNote message={error} />
        <div className="flex justify-end gap-3">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button intent="accent" type="submit" disabled={save.isPending}>
            {initial ? 'Save changes' : 'Create service'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default function Services() {
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState<ServiceOut | 'new' | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['services', q],
    queryFn: async () => (await api.get<Page<ServiceOut>>('/services', { params: { q: q || undefined } })).data,
  })

  const archive = useMutation({
    mutationFn: async (id: string) => api.delete(`/services/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['services'] }),
  })

  return (
    <div>
      <div className="flex items-start justify-between">
        <SealHeading eyebrow="Catalogue">Services</SealHeading>
        <Button intent="accent" onClick={() => setEditing('new')}>New service</Button>
      </div>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search name or SKU"
        className="mb-5 w-72 rounded-[4px] border border-gold-soft bg-white px-3 py-2 text-sm"
      />

      {isLoading ? (
        <Spinner />
      ) : !data || data.items.length === 0 ? (
        <Panel>
          <EmptyState title="No services" hint="Create your first service to start billing." />
        </Panel>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.items.map((s) => (
            <Panel key={s.id} className="flex flex-col p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-display font-bold">{s.name}</div>
                  <div className="font-mono text-[11px] text-brown-mid">{s.sku}</div>
                </div>
                <Badge tone="active">{s.service_type}</Badge>
              </div>
              <div className="mt-3 font-display text-xl font-extrabold">
                {rupees(s.rate)}
                <span className="ml-1 font-sans text-xs font-normal text-brown-mid">
                  {s.billing_interval !== 'N/A' ? `/ ${s.billing_interval.toLowerCase()}` : 'one-time'}
                </span>
              </div>
              <div className="mt-2 space-y-0.5 text-xs text-brown-mid">
                <div>{s.delivery_mode} · {s.cancellation_policy}</div>
                {s.deliverables.map((d) => (
                  <div key={d.id} className="font-mono">{d.quantity} {d.unit} — {d.name}</div>
                ))}
              </div>
              <div className="mt-auto flex justify-end gap-2 pt-3">
                <Button className="!px-2 !py-1 text-xs" onClick={() => setEditing(s)}>Edit</Button>
                <Button
                  intent="danger"
                  className="!px-2 !py-1 text-xs"
                  onClick={() => confirm(`Archive ${s.name}?`) && archive.mutate(s.id)}
                >
                  Archive
                </Button>
              </div>
            </Panel>
          ))}
        </div>
      )}

      {editing && (
        <ServiceForm
          initial={editing === 'new' ? undefined : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            queryClient.invalidateQueries({ queryKey: ['services'] })
          }}
        />
      )}
    </div>
  )
}
