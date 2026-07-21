import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { DashboardOut } from '../api/types'
import { fullDate, rupees, shortTime } from '../lib/format'
import { EmptyState, Panel, SealHeading, Spinner, StatCard, Table } from '../components/ui'

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => (await api.get<DashboardOut>('/dashboard')).data,
  })

  if (isLoading || !data) return <Spinner />

  return (
    <div>
      <SealHeading eyebrow="Today at a glance">Dashboard</SealHeading>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Active clients" value={data.active_clients} />
        <StatCard label="Active batches" value={data.active_batches} />
        <StatCard label="Billed this month" value={rupees(data.billed_this_month)} />
        <StatCard
          label="Overdue invoices"
          value={data.overdue_count}
          hint={data.overdue_count > 0 ? 'needs follow-up' : 'all clear'}
        />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="font-display text-lg font-bold mb-3">Today's batches</h2>
          {data.todays_batches.length === 0 ? (
            <Panel>
              <EmptyState title="No batches running today" />
            </Panel>
          ) : (
            <Table head={['Batch', 'Time', 'Instructor', 'Location', 'Fill']}>
              {data.todays_batches.map((b) => (
                <tr key={b.id}>
                  <td className="px-4 py-2.5">
                    <Link to={`/operations/batches/${b.id}`} className="font-medium text-orange-deep hover:text-orange">
                      {b.name}
                    </Link>
                    <span className="ml-2 font-mono text-[11px] text-brown-mid">{b.code}</span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs">
                    {shortTime(b.start_time)} – {shortTime(b.end_time)}
                  </td>
                  <td className="px-4 py-2.5">{b.instructor_name ?? '—'}</td>
                  <td className="px-4 py-2.5">{b.location_name ?? '—'}</td>
                  <td className="px-4 py-2.5 font-mono text-xs">
                    {b.enrolled_count}/{b.capacity ?? '∞'}
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </section>

        <section>
          <h2 className="font-display text-lg font-bold mb-3">Recent enrollments</h2>
          {data.recent_enrollments.length === 0 ? (
            <Panel>
              <EmptyState title="No enrollments yet" hint="Enroll a client from a batch page or a client profile." />
            </Panel>
          ) : (
            <Table head={['Client', 'Batch', 'Start date']}>
              {data.recent_enrollments.map((e) => (
                <tr key={e.id}>
                  <td className="px-4 py-2.5">
                    <Link to={`/clients/${e.client_id}`} className="font-medium text-orange-deep hover:text-orange">
                      {e.client_name}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5">
                    {e.batch_name}
                    <span className="ml-2 font-mono text-[11px] text-brown-mid">{e.batch_code}</span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs">{fullDate(e.start_date)}</td>
                </tr>
              ))}
            </Table>
          )}
        </section>
      </div>
    </div>
  )
}
