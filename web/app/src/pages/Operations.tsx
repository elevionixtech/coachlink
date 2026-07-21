import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { BatchIn, BatchOut, EnrollmentOut, InstructorOut, LocationIn, LocationOut, Page } from '../api/types'
import { BATCH_STATUSES, LOCATION_TYPES } from '../api/types'
import { fullDate, shortTime } from '../lib/format'
import {
  Badge, Button, ErrorNote, Field, Modal, EmptyState, Panel, SealHeading, SelectField,
  Spinner, Table, statusTone,
} from '../components/ui'

const TABS = ['Locations', 'Batches', 'Enrollments'] as const

export default function Operations() {
  const [params, setParams] = useSearchParams()
  const tab = (params.get('tab') as (typeof TABS)[number]) || 'Batches'

  return (
    <div>
      <SealHeading eyebrow="Operations">Locations, batches & enrollments</SealHeading>
      <div className="mb-5 flex gap-1 border-b border-gold-soft">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setParams({ tab: t })}
            className={`px-3 py-2 text-sm cursor-pointer border-b-2 -mb-px transition-colors ${
              tab === t ? 'border-orange font-semibold' : 'border-transparent text-brown-mid hover:text-brown'
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      {tab === 'Locations' && <LocationsTab />}
      {tab === 'Batches' && <BatchesTab />}
      {tab === 'Enrollments' && <EnrollmentsTab />}
    </div>
  )
}

// ---------------------------------------------------------------- locations

function LocationForm({
  initial,
  onSaved,
  onClose,
}: {
  initial?: LocationOut
  onSaved: () => void
  onClose: () => void
}) {
  const [form, setForm] = useState<LocationIn>({
    name: initial?.name ?? '',
    code: initial?.code ?? '',
    type: initial?.type ?? 'Studio',
    address: initial?.address ?? '',
    capacity_per_batch: initial?.capacity_per_batch ?? null,
    parallel_batches: initial?.parallel_batches ?? null,
  })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof LocationIn, v: unknown) => setForm((f) => ({ ...f, [k]: v }))

  const save = useMutation({
    mutationFn: async () => {
      if (initial) await api.patch(`/locations/${initial.id}`, form)
      else await api.post('/locations', form)
    },
    onSuccess: onSaved,
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal title={initial ? 'Edit location' : 'New location'} onClose={onClose}>
      <form onSubmit={(e) => { e.preventDefault(); save.mutate() }} className="space-y-4">
        <Field label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
        <div className="grid grid-cols-2 gap-4">
          <Field label="Code" required value={form.code} onChange={(e) => set('code', e.target.value)} className="[&>input]:font-mono" hint="Unique per organisation" />
          <SelectField label="Type" value={form.type ?? ''} onChange={(e) => set('type', e.target.value)}>
            {LOCATION_TYPES.map((t) => <option key={t}>{t}</option>)}
          </SelectField>
          <Field label="Capacity per batch" type="number" min={0} value={form.capacity_per_batch ?? ''} onChange={(e) => set('capacity_per_batch', e.target.value === '' ? null : Number(e.target.value))} />
          <Field label="Parallel batches" type="number" min={0} value={form.parallel_batches ?? ''} onChange={(e) => set('parallel_batches', e.target.value === '' ? null : Number(e.target.value))} />
        </div>
        <Field label="Address" value={form.address ?? ''} onChange={(e) => set('address', e.target.value)} />
        <ErrorNote message={error} />
        <div className="flex justify-end gap-3">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button intent="accent" type="submit" disabled={save.isPending}>
            {initial ? 'Save changes' : 'Create location'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function LocationsTab() {
  const [editing, setEditing] = useState<LocationOut | 'new' | null>(null)
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['locations'],
    queryFn: async () => (await api.get<Page<LocationOut>>('/locations', { params: { limit: 200 } })).data,
  })
  const archive = useMutation({
    mutationFn: async (id: string) => api.delete(`/locations/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['locations'] }),
  })

  return (
    <div>
      <div className="mb-3 flex justify-end">
        <Button intent="accent" onClick={() => setEditing('new')}>New location</Button>
      </div>
      {isLoading ? (
        <Spinner />
      ) : !data?.items.length ? (
        <Panel><EmptyState title="No locations" hint="Batches need a location — add one first." /></Panel>
      ) : (
        <Table head={['Name', 'Code', 'Type', 'Capacity/batch', 'Parallel batches', '']}>
          {data.items.map((l) => (
            <tr key={l.id}>
              <td className="px-4 py-2.5 font-medium">{l.name}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{l.code}</td>
              <td className="px-4 py-2.5 text-xs">{l.type ?? '—'}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{l.capacity_per_batch ?? '—'}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{l.parallel_batches ?? '—'}</td>
              <td className="px-4 py-2.5 text-right whitespace-nowrap">
                <Button className="!px-2 !py-1 text-xs" onClick={() => setEditing(l)}>Edit</Button>{' '}
                <Button intent="danger" className="!px-2 !py-1 text-xs" onClick={() => confirm(`Archive ${l.name}?`) && archive.mutate(l.id)}>
                  Archive
                </Button>
              </td>
            </tr>
          ))}
        </Table>
      )}
      {editing && (
        <LocationForm
          initial={editing === 'new' ? undefined : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            queryClient.invalidateQueries({ queryKey: ['locations'] })
          }}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------- batches

export function BatchForm({
  initial,
  onSaved,
  onClose,
}: {
  initial?: BatchOut
  onSaved: () => void
  onClose: () => void
}) {
  const [form, setForm] = useState<BatchIn>({
    name: initial?.name ?? '',
    code: initial?.code ?? '',
    status: initial?.status ?? 'upcoming',
    location_id: initial?.location_id ?? '',
    instructor_id: initial?.instructor_id ?? '',
    start_date: initial?.start_date ?? null,
    end_date: initial?.end_date ?? null,
    start_time: initial?.start_time ?? null,
    end_time: initial?.end_time ?? null,
    description: initial?.description ?? '',
  })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof BatchIn, v: unknown) => setForm((f) => ({ ...f, [k]: v }))

  const { data: locations } = useQuery({
    queryKey: ['locations'],
    queryFn: async () => (await api.get<Page<LocationOut>>('/locations', { params: { limit: 200 } })).data,
  })
  const { data: instructors } = useQuery({
    queryKey: ['instructors', ''],
    queryFn: async () => (await api.get<Page<InstructorOut>>('/instructors', { params: { limit: 200 } })).data,
  })

  const save = useMutation({
    mutationFn: async () => {
      const body = {
        ...form,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        start_time: form.start_time || null,
        end_time: form.end_time || null,
      }
      if (initial) await api.patch(`/batches/${initial.id}`, body)
      else await api.post('/batches', body)
    },
    onSuccess: onSaved,
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal title={initial ? 'Edit batch' : 'New batch'} onClose={onClose} wide>
      <form onSubmit={(e) => { e.preventDefault(); save.mutate() }} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
          <Field label="Code" required value={form.code} onChange={(e) => set('code', e.target.value)} className="[&>input]:font-mono" hint="Unique per organisation" />
          <SelectField label="Location" required value={form.location_id} onChange={(e) => set('location_id', e.target.value)}>
            <option value="">Choose…</option>
            {locations?.items.map((l) => <option key={l.id} value={l.id}>{l.name} ({l.code})</option>)}
          </SelectField>
          <SelectField label="Instructor" required value={form.instructor_id} onChange={(e) => set('instructor_id', e.target.value)}>
            <option value="">Choose…</option>
            {instructors?.items.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
          </SelectField>
          <SelectField label="Status" value={form.status ?? 'upcoming'} onChange={(e) => set('status', e.target.value)}>
            {BATCH_STATUSES.map((s) => <option key={s}>{s}</option>)}
          </SelectField>
          <div />
          <Field label="Start date" type="date" value={form.start_date ?? ''} onChange={(e) => set('start_date', e.target.value || null)} />
          <Field label="End date" type="date" value={form.end_date ?? ''} onChange={(e) => set('end_date', e.target.value || null)} />
          <Field label="Start time" type="time" value={form.start_time ?? ''} onChange={(e) => set('start_time', e.target.value || null)} />
          <Field label="End time" type="time" value={form.end_time ?? ''} onChange={(e) => set('end_time', e.target.value || null)} />
        </div>
        <Field label="Description" value={form.description ?? ''} onChange={(e) => set('description', e.target.value)} />
        <ErrorNote message={error} />
        <div className="flex justify-end gap-3">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button intent="accent" type="submit" disabled={save.isPending || !form.location_id || !form.instructor_id}>
            {initial ? 'Save changes' : 'Create batch'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function BatchesTab() {
  const [q, setQ] = useState('')
  const [creating, setCreating] = useState(false)
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['batches', q],
    queryFn: async () => (await api.get<Page<BatchOut>>('/batches', { params: { q: q || undefined } })).data,
  })

  return (
    <div>
      <div className="mb-3 flex justify-between">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search name or code"
          className="w-72 rounded-[4px] border border-gold-soft bg-white px-3 py-2 text-sm"
        />
        <Button intent="accent" onClick={() => setCreating(true)}>New batch</Button>
      </div>
      {isLoading ? (
        <Spinner />
      ) : !data?.items.length ? (
        <Panel><EmptyState title="No batches" hint="Create a location and an instructor first, then a batch." /></Panel>
      ) : (
        <Table head={['Batch', 'Status', 'Schedule', 'Instructor', 'Location', 'Fill']}>
          {data.items.map((b) => (
            <tr key={b.id}>
              <td className="px-4 py-2.5">
                <Link to={`/operations/batches/${b.id}`} className="font-medium text-orange-deep hover:text-orange">
                  {b.name}
                </Link>
                <span className="ml-2 font-mono text-[11px] text-brown-mid">{b.code}</span>
              </td>
              <td className="px-4 py-2.5"><Badge tone={statusTone(b.status)}>{b.status}</Badge></td>
              <td className="px-4 py-2.5 font-mono text-xs">
                {fullDate(b.start_date)} – {fullDate(b.end_date)}
                <div className="text-brown-mid">{shortTime(b.start_time)} – {shortTime(b.end_time)}</div>
              </td>
              <td className="px-4 py-2.5 text-xs">{b.instructor_name}</td>
              <td className="px-4 py-2.5 text-xs">{b.location_name}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{b.enrolled_count}/{b.capacity ?? '∞'}</td>
            </tr>
          ))}
        </Table>
      )}
      {creating && (
        <BatchForm
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false)
            queryClient.invalidateQueries({ queryKey: ['batches'] })
          }}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------- enrollments

function EnrollmentsTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['enrollments'],
    queryFn: async () => (await api.get<Page<EnrollmentOut>>('/enrollments', { params: { limit: 100 } })).data,
  })

  return isLoading ? (
    <Spinner />
  ) : !data?.items.length ? (
    <Panel><EmptyState title="No enrollments" hint="Enroll clients from a batch page or a client profile." /></Panel>
  ) : (
    <Table head={['Client', 'Batch', 'Start date', 'Enrolled on']}>
      {data.items.map((e) => (
        <tr key={e.id}>
          <td className="px-4 py-2.5">
            <Link to={`/clients/${e.client_id}`} className="font-medium text-orange-deep hover:text-orange">
              {e.client_name}
            </Link>
          </td>
          <td className="px-4 py-2.5">
            <Link to={`/operations/batches/${e.batch_id}`} className="text-orange-deep hover:text-orange">
              {e.batch_name}
            </Link>
            <span className="ml-2 font-mono text-[11px] text-brown-mid">{e.batch_code}</span>
          </td>
          <td className="px-4 py-2.5 font-mono text-xs">{fullDate(e.start_date)}</td>
          <td className="px-4 py-2.5 font-mono text-xs">{fullDate(e.created_at.slice(0, 10))}</td>
        </tr>
      ))}
    </Table>
  )
}
