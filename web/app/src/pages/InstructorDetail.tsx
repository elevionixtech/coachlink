import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { InstructorOut } from '../api/types'
import { fullDate } from '../lib/format'
import { Badge, Button, EmptyState, Panel, SealHeading, Spinner, Table, statusTone } from '../components/ui'
import { InstructorForm } from './Instructors'

interface TaughtBatch {
  id: string
  name: string
  code: string
  status: string
  start_date: string | null
  end_date: string | null
  location_name: string | null
}

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="eyebrow">{label}</div>
      <div className="mt-0.5 text-sm">{children ?? '—'}</div>
    </div>
  )
}

export default function InstructorDetail() {
  const { id } = useParams()
  const [editing, setEditing] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const { data: instructor, isLoading } = useQuery({
    queryKey: ['instructor', id],
    queryFn: async () => (await api.get<InstructorOut>(`/instructors/${id}`)).data,
  })
  const { data: batches } = useQuery({
    queryKey: ['instructor-batches', id],
    queryFn: async () => (await api.get<TaughtBatch[]>(`/instructors/${id}/batches`)).data,
  })

  const archive = useMutation({
    mutationFn: async () => api.delete(`/instructors/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instructors'] })
      navigate('/instructors')
    },
  })

  if (isLoading || !instructor) return <Spinner />

  return (
    <div>
      <div className="flex items-start justify-between">
        <SealHeading eyebrow="Instructor">{instructor.name}</SealHeading>
        <div className="flex gap-2">
          <Button onClick={() => setEditing(true)}>Edit details</Button>
          <Button
            intent="danger"
            onClick={() => confirm(`Archive ${instructor.name}?`) && archive.mutate()}
          >
            Archive
          </Button>
        </div>
      </div>

      <Panel className="grid grid-cols-2 gap-x-8 gap-y-4 p-5 lg:grid-cols-4">
        <Item label="Age">{instructor.age != null && `${instructor.age} yrs`}</Item>
        <Item label="Current experience">
          {instructor.current_experience != null && `${instructor.current_experience} yrs`}
        </Item>
        <Item label="Joining date">{fullDate(instructor.joining_date)}</Item>
        <Item label="Phone">{instructor.phone && <span className="font-mono">{instructor.phone}</span>}</Item>
        <Item label="Skills">{instructor.skills.join(' · ')}</Item>
        <Item label="Courses">{instructor.courses}</Item>
        <Item label="Certifications">{instructor.certifications}</Item>
        <Item label="Address">{instructor.address}</Item>
      </Panel>

      <h2 className="font-display text-lg font-bold mt-8 mb-3">Batches taught</h2>
      {!batches?.length ? (
        <Panel><EmptyState title="No batches assigned" /></Panel>
      ) : (
        <Table head={['Batch', 'Code', 'Status', 'Dates', 'Location']}>
          {batches.map((b) => (
            <tr key={b.id}>
              <td className="px-4 py-2.5">
                <Link to={`/operations/batches/${b.id}`} className="font-medium text-orange-deep hover:text-orange">
                  {b.name}
                </Link>
              </td>
              <td className="px-4 py-2.5 font-mono text-xs">{b.code}</td>
              <td className="px-4 py-2.5"><Badge tone={statusTone(b.status)}>{b.status}</Badge></td>
              <td className="px-4 py-2.5 font-mono text-xs">
                {fullDate(b.start_date)} – {fullDate(b.end_date)}
              </td>
              <td className="px-4 py-2.5 text-xs">{b.location_name ?? '—'}</td>
            </tr>
          ))}
        </Table>
      )}

      {editing && (
        <InstructorForm
          initial={instructor}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false)
            queryClient.invalidateQueries({ queryKey: ['instructor', id] })
          }}
        />
      )}
    </div>
  )
}
