import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { OrgSettingsOut } from '../api/types'
import {
  Button, ErrorNote, Field, Panel, SealHeading, SelectField, Spinner, TextArea,
} from '../components/ui'

const BLANK = {
  name: '',
  address: '',
  billing_email: '',
  phone: '',
  gstin: '',
  invoice_prefix: '',
  invoice_grace_days: '7',
  capacity_policy: 'warn',
}

export default function Organisation() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(BLANK)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const set = (k: keyof typeof form, v: string) => {
    setForm((f) => ({ ...f, [k]: v }))
    setSaved(false)
  }

  const { data: org, isLoading } = useQuery({
    queryKey: ['org'],
    queryFn: async () => (await api.get<OrgSettingsOut>('/org')).data,
  })

  // Seed the form once the org arrives; nulls become empty strings for the inputs.
  useEffect(() => {
    if (!org) return
    setForm({
      name: org.name,
      address: org.address ?? '',
      billing_email: org.billing_email ?? '',
      phone: org.phone ?? '',
      gstin: org.gstin ?? '',
      invoice_prefix: org.invoice_prefix,
      invoice_grace_days: String(org.invoice_grace_days),
      capacity_policy: org.capacity_policy,
    })
  }, [org])

  const save = useMutation({
    mutationFn: async () =>
      api.patch('/org', {
        ...form,
        // Send null rather than "" so a cleared field reads as absent on the invoice.
        address: form.address || null,
        billing_email: form.billing_email || null,
        phone: form.phone || null,
        gstin: form.gstin || null,
        invoice_grace_days: Number(form.invoice_grace_days),
      }),
    onSuccess: () => {
      setError(null)
      setSaved(true)
      queryClient.invalidateQueries({ queryKey: ['org'] })
    },
    onError: (e) => setError(errorMessage(e)),
  })

  if (isLoading) return <Spinner />

  return (
    <div>
      <SealHeading eyebrow={org?.code}>Organisation</SealHeading>
      <form
        onSubmit={(e) => { e.preventDefault(); save.mutate() }}
        className="grid gap-6 lg:grid-cols-2"
      >
        <Panel className="h-fit p-5 space-y-4">
          <h3 className="font-display font-bold">Billing identity</h3>
          <p className="text-sm text-brown-mid">
            These appear in the header of every invoice you issue. A GSTIN and address are
            expected on a tax invoice, so fill them in before sending anything to a client.
          </p>
          <Field label="Organisation name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
          <TextArea label="Address" value={form.address} onChange={(e) => set('address', e.target.value)} />
          <Field label="Billing email" type="email" value={form.billing_email} onChange={(e) => set('billing_email', e.target.value)} />
          <Field label="Phone" value={form.phone} onChange={(e) => set('phone', e.target.value)} />
          <Field
            label="GSTIN"
            value={form.gstin}
            onChange={(e) => set('gstin', e.target.value)}
            className="[&>input]:font-mono"
            hint="15-character GST identification number"
          />
        </Panel>

        <Panel className="h-fit p-5 space-y-4">
          <h3 className="font-display font-bold">Invoicing</h3>
          <Field
            label="Invoice prefix"
            value={form.invoice_prefix}
            onChange={(e) => set('invoice_prefix', e.target.value)}
            className="[&>input]:font-mono"
            hint="Numbers read PREFIX-YYYY-NNNN"
          />
          <Field
            label="Grace days before overdue"
            type="number"
            min={0}
            value={form.invoice_grace_days}
            onChange={(e) => set('invoice_grace_days', e.target.value)}
            hint="An invoice reads Overdue once its issue date plus this many days has passed"
          />
          <SelectField
            label="Capacity policy"
            value={form.capacity_policy}
            onChange={(e) => set('capacity_policy', e.target.value)}
          >
            <option value="warn">warn — allow enrolment over capacity</option>
            <option value="block">block — refuse enrolment over capacity</option>
          </SelectField>

          <ErrorNote message={error} />
          {saved && <p className="text-sm">Saved.</p>}
          <Button intent="accent" type="submit" disabled={save.isPending} className="w-full">
            Save organisation
          </Button>
        </Panel>
      </form>
    </div>
  )
}
