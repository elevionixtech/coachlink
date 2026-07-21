import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { InstructorIn, InstructorOut, Page } from '../api/types'
import { fullDate } from '../lib/format'
import {
  Button, ErrorNote, Field, Modal, EmptyState, Panel, SealHeading, Spinner, Table, TextArea,
} from '../components/ui'

export function InstructorForm({
  initial,
  onSaved,
  onClose,
}: {
  initial?: InstructorOut
  onSaved: () => void
  onClose: () => void
}) {
  const [form, setForm] = useState<InstructorIn>({
    name: initial?.name ?? '',
    date_of_birth: initial?.date_of_birth ?? null,
    address: initial?.address ?? '',
    phone: initial?.phone ?? '',
    skills: initial?.skills ?? [],
    experience_at_joining: initial?.experience_at_joining ?? null,
    courses: initial?.courses ?? '',
    certifications: initial?.certifications ?? '',
    joining_date: initial?.joining_date ?? null,
  })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof InstructorIn, v: unknown) => setForm((f) => ({ ...f, [k]: v }))

  const save = useMutation({
    mutationFn: async () => {
      const body = {
        ...form,
        date_of_birth: form.date_of_birth || null,
        joining_date: form.joining_date || null,
        experience_at_joining: form.experience_at_joining || null,
      }
      if (initial) await api.patch(`/instructors/${initial.id}`, body)
      else await api.post('/instructors', body)
    },
    onSuccess: onSaved,
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal title={initial ? 'Edit instructor' : 'New instructor'} onClose={onClose} wide>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
        className="space-y-4"
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
          <Field label="Phone" value={form.phone ?? ''} onChange={(e) => set('phone', e.target.value)} />
          <Field label="Date of birth" type="date" value={form.date_of_birth ?? ''} onChange={(e) => set('date_of_birth', e.target.value || null)} />
          <Field label="Joining date" type="date" value={form.joining_date ?? ''} onChange={(e) => set('joining_date', e.target.value || null)} />
          <Field
            label="Experience at joining (years)"
            type="number" min={0} step="0.5"
            value={form.experience_at_joining ?? ''}
            onChange={(e) => set('experience_at_joining', e.target.value === '' ? null : e.target.value)}
          />
          <Field
            label="Skills (comma-separated)"
            value={form.skills!.join(', ')}
            onChange={(e) => set('skills', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
            placeholder="Hatha, Vinyasa, Prenatal"
          />
        </div>
        <Field label="Address" value={form.address ?? ''} onChange={(e) => set('address', e.target.value)} />
        <TextArea label="Courses" value={form.courses ?? ''} onChange={(e) => set('courses', e.target.value)} />
        <TextArea label="Certifications" value={form.certifications ?? ''} onChange={(e) => set('certifications', e.target.value)} />
        <ErrorNote message={error} />
        <div className="flex justify-end gap-3">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button intent="accent" type="submit" disabled={save.isPending}>
            {initial ? 'Save changes' : 'Create instructor'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default function Instructors() {
  const [q, setQ] = useState('')
  const [creating, setCreating] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['instructors', q],
    queryFn: async () => (await api.get<Page<InstructorOut>>('/instructors', { params: { q: q || undefined } })).data,
  })

  return (
    <div>
      <div className="flex items-start justify-between">
        <SealHeading eyebrow="Team">Instructors</SealHeading>
        <Button intent="accent" onClick={() => setCreating(true)}>Add instructor</Button>
      </div>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search by name"
        className="mb-5 w-72 rounded-[4px] border border-gold-soft bg-white px-3 py-2 text-sm"
      />
      {isLoading ? (
        <Spinner />
      ) : !data || data.items.length === 0 ? (
        <Panel><EmptyState title="No instructors" /></Panel>
      ) : (
        <Table head={['Name', 'Skills', 'Experience', 'Joined', 'Phone']}>
          {data.items.map((i) => (
            <tr key={i.id}>
              <td className="px-4 py-2.5">
                <Link to={`/instructors/${i.id}`} className="font-medium text-orange-deep hover:text-orange">
                  {i.name}
                </Link>
              </td>
              <td className="px-4 py-2.5 text-xs">{i.skills.join(' · ') || '—'}</td>
              <td className="px-4 py-2.5 font-mono text-xs">
                {i.current_experience != null ? `${i.current_experience} yrs` : '—'}
              </td>
              <td className="px-4 py-2.5 font-mono text-xs">{fullDate(i.joining_date)}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{i.phone ?? '—'}</td>
            </tr>
          ))}
        </Table>
      )}
      {creating && (
        <InstructorForm
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false)
            queryClient.invalidateQueries({ queryKey: ['instructors'] })
          }}
        />
      )}
    </div>
  )
}
