import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { MemberOut, OrgSettingsOut } from '../api/types'
import { fullDate } from '../lib/format'
import {
  Badge, Button, ErrorNote, Field, Panel, SealHeading, SelectField, Spinner, Table,
} from '../components/ui'

export default function Members() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ name: '', username: '', password: '', role: 'staff' })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const { data: org } = useQuery({
    queryKey: ['org'],
    queryFn: async () => (await api.get<OrgSettingsOut>('/org')).data,
  })
  const { data: members, isLoading } = useQuery({
    queryKey: ['members', org?.id],
    queryFn: async () => (await api.get<MemberOut[]>(`/organisations/${org!.id}/members`)).data,
    enabled: !!org,
  })

  const add = useMutation({
    mutationFn: async () => api.post(`/organisations/${org!.id}/members`, form),
    onSuccess: () => {
      setForm({ name: '', username: '', password: '', role: 'staff' })
      setError(null)
      queryClient.invalidateQueries({ queryKey: ['members'] })
    },
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <div>
      <SealHeading eyebrow={org?.name ?? 'Organisation settings'}>Members</SealHeading>
      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div>
          {isLoading ? (
            <Spinner />
          ) : (
            <Table head={['Name', 'Username', 'Role', 'Added']}>
              {members?.map((m) => (
                <tr key={m.id}>
                  <td className="px-4 py-2.5">{m.name}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">{m.username}</td>
                  <td className="px-4 py-2.5">
                    <Badge tone={m.role === 'admin' ? 'active' : 'draft'}>{m.role}</Badge>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs">{fullDate(m.created_at.slice(0, 10))}</td>
                </tr>
              ))}
            </Table>
          )}
        </div>
        <Panel className="h-fit p-4">
          <h3 className="font-display font-bold mb-3">Add member</h3>
          <form onSubmit={(e) => { e.preventDefault(); add.mutate() }} className="space-y-3">
            <Field label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
            <Field label="Username" required value={form.username} onChange={(e) => set('username', e.target.value)} hint="Unique within your organisation" />
            <Field label="Password" type="password" required minLength={4} value={form.password} onChange={(e) => set('password', e.target.value)} />
            <SelectField label="Role" value={form.role} onChange={(e) => set('role', e.target.value)}>
              <option value="staff">staff</option>
              <option value="admin">admin</option>
            </SelectField>
            <ErrorNote message={error} />
            <Button intent="accent" type="submit" disabled={add.isPending} className="w-full">
              Add member
            </Button>
          </form>
        </Panel>
      </div>
    </div>
  )
}
