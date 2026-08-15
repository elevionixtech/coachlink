import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { OrgSettingsOut, PricingOptionOut } from '../api/types'
import { fullDate } from '../lib/format'
import {
  Button, EmptyState, ErrorNote, Field, Panel, SealHeading, Spinner, Table, TextArea,
} from '../components/ui'

const BLANK = { name: '', description: '', sort_order: 0 }

export default function PricingOptions() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(BLANK)
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof typeof form, v: unknown) => setForm((f) => ({ ...f, [k]: v }))

  const { data: org } = useQuery({
    queryKey: ['org'],
    queryFn: async () => (await api.get<OrgSettingsOut>('/org')).data,
  })
  const { data: options, isLoading } = useQuery({
    queryKey: ['pricing-options'],
    queryFn: async () => (await api.get<PricingOptionOut[]>('/pricing-options')).data,
  })

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['pricing-options'] })

  const add = useMutation({
    mutationFn: async () => api.post('/pricing-options', { ...form, sort_order: Number(form.sort_order) }),
    onSuccess: () => { setForm(BLANK); setError(null); refresh() },
    onError: (e) => setError(errorMessage(e)),
  })

  const remove = useMutation({
    mutationFn: async (id: string) => api.delete(`/pricing-options/${id}`),
    onSuccess: () => { setError(null); refresh() },
    onError: (e) => setError(errorMessage(e)),
  })


  return (
    <div>
      <SealHeading eyebrow={org?.name ?? 'Organisation settings'}>Pricing options</SealHeading>
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div>
          {isLoading ? (
            <Spinner />
          ) : options?.length === 0 ? (
            <EmptyState
              title="No pricing options yet"
              hint="Add a tier such as Corporate Plan or Student, then set what each service charges for it on the service itself."
            />
          ) : (
            <Table head={['Name', 'Order', 'Added', '']}>
              {options?.map((o) => (
                <tr key={o.id}>
                  <td className="px-4 py-2.5">
                    <div>{o.name}</div>
                    {o.description && (
                      <div className="text-xs text-muted">{o.description}</div>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs">{o.sort_order}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">
                    {fullDate(o.created_at.slice(0, 10))}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <Button
                      intent="danger"
                      className="!px-2 !py-1 text-xs"
                      onClick={() => remove.mutate(o.id)}
                      disabled={remove.isPending}
                    >
                      Remove
                    </Button>
                  </td>
                </tr>
              ))}
            </Table>
          )}
          <ErrorNote message={error} />
        </div>
        <Panel className="h-fit p-4">
          <h3 className="font-display font-bold mb-3">Add pricing option</h3>
          <form onSubmit={(e) => { e.preventDefault(); add.mutate() }} className="space-y-3">
            <Field
              label="Name"
              required
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="Corporate Plan"
              hint="Unique within your organisation"
            />
            <TextArea
              label="Description"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
            />
            <Field
              label="Sort order"
              type="number"
              value={String(form.sort_order)}
              onChange={(e) => set('sort_order', e.target.value)}
            />
            <Button intent="accent" type="submit" disabled={add.isPending} className="w-full">
              Add pricing option
            </Button>
          </form>
        </Panel>
      </div>
    </div>
  )
}
