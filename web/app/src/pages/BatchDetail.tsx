import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api/client'
import type { BatchOut, ClientOut, EnrollmentOut, Page } from '../api/types'
import { fullDate, shortTime } from '../lib/format'
import {
  Badge, Button, ErrorNote, Field, Modal, EmptyState, Panel, SealHeading, SelectField,
  Spinner, Table, statusTone,
} from '../components/ui'
import { BatchForm } from './Operations'

export default function BatchDetail() {
  const { id } = useParams()
  const [editing, setEditing] = useState(false)
  const [enrolling, setEnrolling] = useState(false)
  const [warning, setWarning] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: batch, isLoading } = useQuery({
    queryKey: ['batch', id],
    queryFn: async () => (await api.get<BatchOut>(`/batches/${id}`)).data,
  })
  const { data: roster } = useQuery({
    queryKey: ['roster', id],
    queryFn: async () => (await api.get<EnrollmentOut[]>(`/batches/${id}/roster`)).data,
  })

  if (isLoading || !batch) return <Spinner />

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <SealHeading eyebrow={`Batch · ${batch.code}`}>{batch.name}</SealHeading>
          <div className="-mt-3 mb-4 flex items-center gap-3">
            <Badge tone={statusTone(batch.status)}>{batch.status}</Badge>
            <span className="font-mono text-xs text-brown-mid">
              {fullDate(batch.start_date)} – {fullDate(batch.end_date)} · {shortTime(batch.start_time)} –{' '}
              {shortTime(batch.end_time)}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setEditing(true)}>Edit batch</Button>
          <Button intent="accent" onClick={() => setEnrolling(true)}>Enroll client</Button>
        </div>
      </div>

      <Panel className="mb-6 grid grid-cols-2 gap-4 p-5 lg:grid-cols-4">
        <div>
          <div className="eyebrow">Instructor</div>
          <div className="mt-0.5 text-sm">
            <Link to={`/instructors/${batch.instructor_id}`} className="text-orange-deep hover:text-orange">
              {batch.instructor_name}
            </Link>
          </div>
        </div>
        <div>
          <div className="eyebrow">Location</div>
          <div className="mt-0.5 text-sm">{batch.location_name}</div>
        </div>
        <div>
          <div className="eyebrow">Fill</div>
          <div className="mt-0.5 font-mono text-sm">
            {batch.enrolled_count}/{batch.capacity ?? '∞'}
          </div>
        </div>
        <div>
          <div className="eyebrow">Description</div>
          <div className="mt-0.5 text-sm">{batch.description || '—'}</div>
        </div>
      </Panel>

      {warning && <div className="mb-3 font-mono text-xs text-orange-deep">{warning}</div>}

      <h2 className="font-display text-lg font-bold mb-3">
        Roster{' '}
        <span className="font-mono text-xs font-normal text-brown-mid">
          {batch.enrolled_count}/{batch.capacity ?? '∞'} enrolled
        </span>
      </h2>
      {!roster?.length ? (
        <Panel><EmptyState title="No one enrolled yet" action={<Button intent="accent" onClick={() => setEnrolling(true)}>Enroll client</Button>} /></Panel>
      ) : (
        <Table head={['Client', 'Start date', 'Enrolled on']}>
          {roster.map((e) => (
            <tr key={e.id}>
              <td className="px-4 py-2.5">
                <Link to={`/clients/${e.client_id}`} className="font-medium text-orange-deep hover:text-orange">
                  {e.client_name}
                </Link>
              </td>
              <td className="px-4 py-2.5 font-mono text-xs">{fullDate(e.start_date)}</td>
              <td className="px-4 py-2.5 font-mono text-xs">{fullDate(e.created_at.slice(0, 10))}</td>
            </tr>
          ))}
        </Table>
      )}

      {editing && (
        <BatchForm
          initial={batch}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false)
            queryClient.invalidateQueries({ queryKey: ['batch', id] })
          }}
        />
      )}
      {enrolling && (
        <EnrollModal
          batchId={batch.id}
          onClose={() => setEnrolling(false)}
          onDone={(w) => {
            setEnrolling(false)
            setWarning(w)
            queryClient.invalidateQueries({ queryKey: ['roster', id] })
            queryClient.invalidateQueries({ queryKey: ['batch', id] })
          }}
        />
      )}
    </div>
  )
}

function EnrollModal({
  batchId,
  onClose,
  onDone,
}: {
  batchId: string
  onClose: () => void
  onDone: (warning: string | null) => void
}) {
  const [clientId, setClientId] = useState('')
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10))
  const [error, setError] = useState<string | null>(null)

  const { data: clients } = useQuery({
    queryKey: ['clients-for-enroll'],
    queryFn: async () => (await api.get<Page<ClientOut>>('/clients', { params: { limit: 200 } })).data,
  })

  const enroll = useMutation({
    mutationFn: async () =>
      (await api.post<EnrollmentOut>('/enrollments', { client_id: clientId, batch_id: batchId, start_date: startDate })).data,
    onSuccess: (d) => onDone(d.capacity_warning ?? null),
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal title="Enroll client" onClose={onClose}>
      <form onSubmit={(e) => { e.preventDefault(); enroll.mutate() }} className="space-y-4">
        <SelectField label="Client" required value={clientId} onChange={(e) => setClientId(e.target.value)}>
          <option value="">Choose a client…</option>
          {clients?.items.map((c) => (
            <option key={c.id} value={c.id}>{c.name}{c.name_hint ? ` — ${c.name_hint}` : ''}</option>
          ))}
        </SelectField>
        <Field label="Start date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
        <ErrorNote message={error} />
        <div className="flex justify-end gap-3">
          <Button type="button" onClick={onClose}>Cancel</Button>
          <Button intent="accent" type="submit" disabled={enroll.isPending || !clientId}>Enroll</Button>
        </div>
      </form>
    </Modal>
  )
}
