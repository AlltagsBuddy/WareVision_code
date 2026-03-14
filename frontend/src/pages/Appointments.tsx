import { useEffect, useState } from 'react'
import { appointmentsApi, customersApi, vehiclesApi } from '../api/client'

const TYPE_LABELS: Record<string, string> = {
  workshop: 'Werkstatt',
  test_drive: 'Probefahrt',
}

function getWeekDates(base: Date): Date[] {
  const start = new Date(base)
  const day = start.getDay()
  const diff = day === 0 ? -6 : 1 - day
  start.setDate(start.getDate() + diff)
  start.setHours(0, 0, 0, 0)
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start)
    d.setDate(d.getDate() + i)
    return d
  })
}

function formatTime(d: string): string {
  try {
    return new Date(d).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function formatDateShort(d: Date): string {
  return d.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' })
}

export default function Appointments() {
  const [weekStart, setWeekStart] = useState(() => {
    const d = new Date()
    d.setHours(0, 0, 0, 0)
    return d
  })
  const [appointments, setAppointments] = useState<any[]>([])
  const [customers, setCustomers] = useState<any[]>([])
  const [formVehicles, setFormVehicles] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    customer_id: '',
    vehicle_id: '',
    appointment_type: 'workshop',
    title: '',
    description: '',
    date: '',
    startTime: '09:00',
    endTime: '10:00',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const weekDates = getWeekDates(weekStart)
  const fromDate = new Date(weekDates[0])
  fromDate.setHours(0, 0, 0, 0)
  const toDate = new Date(weekDates[6])
  toDate.setHours(23, 59, 59, 999)

  useEffect(() => {
    Promise.all([
      appointmentsApi.list({
        from_date: fromDate.toISOString(),
        to_date: toDate.toISOString(),
      }),
      customersApi.list(),
    ])
      .then(([apts, custs]) => {
        setAppointments(apts)
        setCustomers(custs)
      })
      .finally(() => setLoading(false))
  }, [fromDate.toISOString(), toDate.toISOString()])

  useEffect(() => {
    if (form.customer_id) {
      vehiclesApi.list({ customer_id: form.customer_id }).then(setFormVehicles)
      setForm((f) => ({ ...f, vehicle_id: '' }))
    } else {
      setFormVehicles([])
    }
  }, [form.customer_id])

  const getCustomerName = (customerId: string | null) => {
    if (!customerId) return '–'
    const c = customers.find((x) => x.id === customerId)
    if (!c) return '–'
    return c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || '–'
  }

  const prevWeek = () => {
    const d = new Date(weekStart)
    d.setDate(d.getDate() - 7)
    setWeekStart(d)
  }

  const nextWeek = () => {
    const d = new Date(weekStart)
    d.setDate(d.getDate() + 7)
    setWeekStart(d)
  }

  const goToday = () => {
    const d = new Date()
    d.setHours(0, 0, 0, 0)
    setWeekStart(d)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    const dateStr = form.date || weekDates[0].toISOString().slice(0, 10)
    const [sh, sm] = form.startTime.split(':').map(Number)
    const [eh, em] = form.endTime.split(':').map(Number)
    const startsAt = new Date(dateStr)
    startsAt.setHours(sh, sm, 0, 0)
    const endsAt = new Date(dateStr)
    endsAt.setHours(eh, em, 0, 0)
    if (startsAt >= endsAt) {
      setError('Ende muss nach Beginn liegen.')
      return
    }
    setSubmitting(true)
    try {
      await appointmentsApi.create({
        customer_id: form.customer_id || undefined,
        vehicle_id: form.vehicle_id || undefined,
        appointment_type: form.appointment_type,
        title: form.title || undefined,
        description: form.description || undefined,
        starts_at: startsAt.toISOString(),
        ends_at: endsAt.toISOString(),
      })
      setShowForm(false)
      setForm({ customer_id: '', vehicle_id: '', appointment_type: 'workshop', title: '', description: '', date: '', startTime: '09:00', endTime: '10:00' })
      const updated = await appointmentsApi.list({
        from_date: fromDate.toISOString(),
        to_date: toDate.toISOString(),
      })
      setAppointments(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Anlegen')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = async (id: string) => {
    if (!confirm('Termin wirklich stornieren?')) return
    try {
      await appointmentsApi.delete(id)
      setAppointments((prev) => prev.filter((a) => a.id !== id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const appointmentsByDay = weekDates.reduce<Record<string, any[]>>((acc, d) => {
    acc[d.toISOString().slice(0, 10)] = []
    return acc
  }, {})
  appointments.forEach((a) => {
    if (a.status === 'cancelled') return
    const key = new Date(a.starts_at).toISOString().slice(0, 10)
    if (appointmentsByDay[key]) appointmentsByDay[key].push(a)
  })

  const vehicles = formVehicles

  return (
    <div className="page">
      <h1>Terminplaner</h1>
      <div className="toolbar">
        <div className="calendar-nav">
          <button type="button" onClick={prevWeek} className="btn-secondary">
            ← Vorherige
          </button>
          <button type="button" onClick={goToday} className="btn-secondary">
            Heute
          </button>
          <button type="button" onClick={nextWeek} className="btn-secondary">
            Nächste →
          </button>
          <span className="calendar-week-label">
            {weekDates[0].toLocaleDateString('de-DE', { day: '2-digit', month: 'short' })} –{' '}
            {weekDates[6].toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' })}
          </span>
        </div>
        <button type="button" onClick={() => setShowForm(true)} className="btn-primary">
          + Neuer Termin
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Neuer Termin</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="apt-type">Typ *</label>
                  <select
                    id="apt-type"
                    value={form.appointment_type}
                    onChange={(e) => setForm({ ...form, appointment_type: e.target.value })}
                    required
                  >
                    <option value="workshop">Werkstatt</option>
                    <option value="test_drive">Probefahrt</option>
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="apt-date">Datum *</label>
                  <input
                    id="apt-date"
                    type="date"
                    value={form.date || weekDates[0].toISOString().slice(0, 10)}
                    onChange={(e) => setForm({ ...form, date: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="apt-start">Von *</label>
                  <input
                    id="apt-start"
                    type="time"
                    value={form.startTime}
                    onChange={(e) => setForm({ ...form, startTime: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="apt-end">Bis *</label>
                  <input
                    id="apt-end"
                    type="time"
                    value={form.endTime}
                    onChange={(e) => setForm({ ...form, endTime: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="apt-customer">Kunde</label>
                <select
                  id="apt-customer"
                  value={form.customer_id}
                  onChange={(e) => setForm({ ...form, customer_id: e.target.value, vehicle_id: '' })}
                >
                  <option value="">– Optional –</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email || c.id}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="apt-vehicle">Fahrzeug</label>
                <select
                  id="apt-vehicle"
                  value={form.vehicle_id}
                  onChange={(e) => setForm({ ...form, vehicle_id: e.target.value })}
                  disabled={!form.customer_id}
                >
                  <option value="">– Optional –</option>
                  {vehicles.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.license_plate || v.vin || 'Fahrzeug'} {v.build_year ? `(${v.build_year})` : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="apt-title">Titel</label>
                <input
                  id="apt-title"
                  type="text"
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="z.B. Ölwechsel"
                />
              </div>
              <div className="form-group">
                <label htmlFor="apt-desc">Beschreibung</label>
                <textarea
                  id="apt-desc"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  rows={2}
                />
              </div>
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
                  Abbrechen
                </button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Wird erstellt...' : 'Termin anlegen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <p>Laden...</p>
      ) : (
        <div className="calendar-grid">
          <div className="calendar-header">
            <div className="calendar-cell calendar-time-header" />
            {weekDates.map((d) => (
              <div key={d.toISOString()} className="calendar-cell calendar-day-header">
                {formatDateShort(d)}
              </div>
            ))}
          </div>
          <div className="calendar-body">
            {[8, 9, 10, 11, 12, 13, 14, 15, 16, 17].map((hour) => (
              <div key={hour} className="calendar-row">
                <div className="calendar-cell calendar-time">
                  {hour}:00
                </div>
                {weekDates.map((d) => (
                  <div key={d.toISOString()} className="calendar-cell calendar-slot" />
                ))}
              </div>
            ))}
          </div>
          <div className="calendar-appointments">
            {weekDates.map((d) => {
              const key = d.toISOString().slice(0, 10)
              const apts = appointmentsByDay[key] || []
              return apts.map((a) => {
                const start = new Date(a.starts_at)
                const end = new Date(a.ends_at)
                const top = (start.getHours() - 8 + start.getMinutes() / 60) * 50
                const height = ((end.getTime() - start.getTime()) / (60 * 60 * 1000)) * 50
                const dayIndex = weekDates.indexOf(d)
                return (
                  <div
                    key={a.id}
                    className="calendar-apt"
                    style={{
                      left: `calc(60px + (100% - 60px) * ${dayIndex} / 7 + 2px)`,
                      width: `calc((100% - 60px) / 7 - 4px)`,
                      top: `${top + 40}px`,
                      height: `${Math.max(height - 2, 24)}px`,
                    }}
                    title={`${getCustomerName(a.customer_id)} – ${a.title || TYPE_LABELS[a.appointment_type]}`}
                  >
                    <span className="calendar-apt-title">{a.title || TYPE_LABELS[a.appointment_type]}</span>
                    <span className="calendar-apt-time">
                      {formatTime(a.starts_at)}–{formatTime(a.ends_at)}
                    </span>
                    {a.customer_id && (
                      <span className="calendar-apt-customer">{getCustomerName(a.customer_id)}</span>
                    )}
                    <button
                      type="button"
                      className="calendar-apt-cancel"
                      onClick={() => handleCancel(a.id)}
                      title="Stornieren"
                    >
                      ×
                    </button>
                  </div>
                )
              })
            })}
          </div>
        </div>
      )}
    </div>
  )
}
