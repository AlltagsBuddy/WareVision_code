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
  const [showImportForm, setShowImportForm] = useState(false)
  const [editingAppointment, setEditingAppointment] = useState<any | null>(null)
  const [cancellingAppointment, setCancellingAppointment] = useState<any | null>(null)
  const [cancelReason, setCancelReason] = useState('')
  const [importForm, setImportForm] = useState({
    external_booking_id: '',
    date: '',
    startTime: '09:00',
    endTime: '10:00',
    customer_first_name: '',
    customer_last_name: '',
    customer_email: '',
    customer_phone: '',
    vehicle_license_plate: '',
    vehicle_vin: '',
    title: '',
    description: '',
  })
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

  useEffect(() => {
    if (editingAppointment?.customer_id) {
      vehiclesApi.list({ customer_id: editingAppointment.customer_id }).then(setFormVehicles)
    } else {
      setFormVehicles([])
    }
  }, [editingAppointment?.customer_id])

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

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!importForm.external_booking_id.trim()) {
      setError('Externe Buchungs-ID erforderlich.')
      return
    }
    const dateStr = importForm.date || weekDates[0].toISOString().slice(0, 10)
    const [sh, sm] = importForm.startTime.split(':').map(Number)
    const [eh, em] = importForm.endTime.split(':').map(Number)
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
      await appointmentsApi.importExternal({
        external_booking_id: importForm.external_booking_id.trim(),
        starts_at: startsAt.toISOString(),
        ends_at: endsAt.toISOString(),
        customer_first_name: importForm.customer_first_name || undefined,
        customer_last_name: importForm.customer_last_name || undefined,
        customer_email: importForm.customer_email || undefined,
        customer_phone: importForm.customer_phone || undefined,
        vehicle_license_plate: importForm.vehicle_license_plate || undefined,
        vehicle_vin: importForm.vehicle_vin || undefined,
        title: importForm.title || undefined,
        description: importForm.description || undefined,
      })
      setShowImportForm(false)
      setImportForm({
        external_booking_id: '',
        date: '',
        startTime: '09:00',
        endTime: '10:00',
        customer_first_name: '',
        customer_last_name: '',
        customer_email: '',
        customer_phone: '',
        vehicle_license_plate: '',
        vehicle_vin: '',
        title: '',
        description: '',
      })
      const updated = await appointmentsApi.list({
        from_date: fromDate.toISOString(),
        to_date: toDate.toISOString(),
      })
      setAppointments(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Import')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancelClick = (a: any) => {
    setCancellingAppointment(a)
    setCancelReason('')
  }

  const handleCancelConfirm = async () => {
    if (!cancellingAppointment) return
    try {
      await appointmentsApi.delete(cancellingAppointment.id, {
        reason: cancelReason.trim() || undefined,
      })
      setCancellingAppointment(null)
      setCancelReason('')
      const updated = await appointmentsApi.list({
        from_date: fromDate.toISOString(),
        to_date: toDate.toISOString(),
      })
      setAppointments(updated)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleEditClick = (a: any) => {
    const start = new Date(a.starts_at)
    const end = new Date(a.ends_at)
    setEditingAppointment({
      ...a,
      date: a.starts_at.slice(0, 10),
      startTime: `${String(start.getHours()).padStart(2, '0')}:${String(start.getMinutes()).padStart(2, '0')}`,
      endTime: `${String(end.getHours()).padStart(2, '0')}:${String(end.getMinutes()).padStart(2, '0')}`,
      customer_id: a.customer_id || '',
      vehicle_id: a.vehicle_id || '',
      appointment_type: a.appointment_type,
      title: a.title || '',
      description: a.description || '',
    })
  }

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingAppointment) return
    setError('')
    const [sh, sm] = editingAppointment.startTime.split(':').map(Number)
    const [eh, em] = editingAppointment.endTime.split(':').map(Number)
    const startsAt = new Date(editingAppointment.date)
    startsAt.setHours(sh, sm, 0, 0)
    const endsAt = new Date(editingAppointment.date)
    endsAt.setHours(eh, em, 0, 0)
    if (startsAt >= endsAt) {
      setError('Ende muss nach Beginn liegen.')
      return
    }
    setSubmitting(true)
    try {
      await appointmentsApi.update(editingAppointment.id, {
        customer_id: editingAppointment.customer_id || null,
        vehicle_id: editingAppointment.vehicle_id || null,
        appointment_type: editingAppointment.appointment_type,
        title: editingAppointment.title || undefined,
        description: editingAppointment.description || undefined,
        starts_at: startsAt.toISOString(),
        ends_at: endsAt.toISOString(),
      })
      setEditingAppointment(null)
      const updated = await appointmentsApi.list({
        from_date: fromDate.toISOString(),
        to_date: toDate.toISOString(),
      })
      setAppointments(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern')
    } finally {
      setSubmitting(false)
    }
  }

  const getDisplayName = (a: any) => {
    if (a.customer_first_name || a.customer_last_name) {
      return `${a.customer_first_name || ''} ${a.customer_last_name || ''}`.trim()
    }
    return getCustomerName(a.customer_id)
  }

  const getCustomerEmail = (customerId: string | null, fallback: { customer_email?: string } | null) => {
    if (customerId) {
      const c = customers.find((x) => x.id === customerId)
      return c?.email || ''
    }
    return fallback?.customer_email || ''
  }

  const getCustomerPhone = (customerId: string | null, fallback: { customer_phone?: string } | null) => {
    if (customerId) {
      const c = customers.find((x) => x.id === customerId)
      return c?.phone || ''
    }
    return fallback?.customer_phone || ''
  }

  const getTooltipText = (a: any) => {
    const parts: string[] = [getDisplayName(a), a.title || TYPE_LABELS[a.appointment_type]]
    if (a.customer_email) parts.push(`E-Mail: ${a.customer_email}`)
    if (a.customer_phone) parts.push(`Tel: ${a.customer_phone}`)
    return parts.join(' · ')
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
        <button type="button" onClick={() => setShowImportForm(true)} className="btn-secondary">
          Extern importieren
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
              {form.customer_id && (
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="apt-email">E-Mail</label>
                    <input
                      id="apt-email"
                      type="email"
                      value={getCustomerEmail(form.customer_id, null)}
                      readOnly
                      className="readonly"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="apt-phone">Telefon</label>
                    <input
                      id="apt-phone"
                      type="text"
                      value={getCustomerPhone(form.customer_id, null)}
                      readOnly
                      className="readonly"
                    />
                  </div>
                </div>
              )}
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

      {editingAppointment && (
        <div className="modal-overlay" onClick={() => setEditingAppointment(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Termin bearbeiten</h2>
            <form onSubmit={handleEditSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="edit-apt-type">Typ *</label>
                  <select
                    id="edit-apt-type"
                    value={editingAppointment.appointment_type}
                    onChange={(e) => setEditingAppointment({ ...editingAppointment, appointment_type: e.target.value })}
                    required
                  >
                    <option value="workshop">Werkstatt</option>
                    <option value="test_drive">Probefahrt</option>
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="edit-apt-date">Datum *</label>
                  <input
                    id="edit-apt-date"
                    type="date"
                    value={editingAppointment.date}
                    onChange={(e) => setEditingAppointment({ ...editingAppointment, date: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="edit-apt-start">Von *</label>
                  <input
                    id="edit-apt-start"
                    type="time"
                    value={editingAppointment.startTime}
                    onChange={(e) => setEditingAppointment({ ...editingAppointment, startTime: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="edit-apt-end">Bis *</label>
                  <input
                    id="edit-apt-end"
                    type="time"
                    value={editingAppointment.endTime}
                    onChange={(e) => setEditingAppointment({ ...editingAppointment, endTime: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="edit-apt-customer">Kunde</label>
                <select
                  id="edit-apt-customer"
                  value={editingAppointment.customer_id}
                  onChange={(e) => setEditingAppointment({ ...editingAppointment, customer_id: e.target.value, vehicle_id: '' })}
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
                <label htmlFor="edit-apt-vehicle">Fahrzeug</label>
                <select
                  id="edit-apt-vehicle"
                  value={editingAppointment.vehicle_id}
                  onChange={(e) => setEditingAppointment({ ...editingAppointment, vehicle_id: e.target.value })}
                  disabled={!editingAppointment.customer_id}
                >
                  <option value="">– Optional –</option>
                  {formVehicles.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.license_plate || v.vin || 'Fahrzeug'} {v.build_year ? `(${v.build_year})` : ''}
                    </option>
                  ))}
                </select>
              </div>
              {(editingAppointment.customer_id || editingAppointment.customer_email || editingAppointment.customer_phone) && (
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="edit-apt-email">E-Mail</label>
                    <input
                      id="edit-apt-email"
                      type="email"
                      value={getCustomerEmail(editingAppointment.customer_id, editingAppointment)}
                      readOnly
                      className="readonly"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="edit-apt-phone">Telefon</label>
                    <input
                      id="edit-apt-phone"
                      type="text"
                      value={getCustomerPhone(editingAppointment.customer_id, editingAppointment)}
                      readOnly
                      className="readonly"
                    />
                  </div>
                </div>
              )}
              <div className="form-group">
                <label htmlFor="edit-apt-title">Titel</label>
                <input
                  id="edit-apt-title"
                  type="text"
                  value={editingAppointment.title}
                  onChange={(e) => setEditingAppointment({ ...editingAppointment, title: e.target.value })}
                  placeholder="z.B. Ölwechsel"
                />
              </div>
              <div className="form-group">
                <label htmlFor="edit-apt-desc">Beschreibung</label>
                <textarea
                  id="edit-apt-desc"
                  value={editingAppointment.description}
                  onChange={(e) => setEditingAppointment({ ...editingAppointment, description: e.target.value })}
                  rows={2}
                />
              </div>
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => setEditingAppointment(null)} className="btn-secondary">
                  Abbrechen
                </button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Wird gespeichert...' : 'Speichern'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {cancellingAppointment && (
        <div className="modal-overlay" onClick={() => setCancellingAppointment(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Termin stornieren</h2>
            <p>
              Termin wirklich stornieren?
              {cancellingAppointment.source === 'termin_marktplatz' && (
                <span style={{ display: 'block', marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
                  Der Kunde erhält eine Stornierungsmail von Terminmarktplatz. Optional können Sie einen Grund angeben:
                </span>
              )}
            </p>
            <div className="form-group" style={{ marginTop: '1rem' }}>
              <label htmlFor="cancel-reason">Stornierungsgrund (optional)</label>
              <textarea
                id="cancel-reason"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="z.B. Kapazitätsengpass, Kundentermin verschoben"
                rows={3}
                style={{ width: '100%' }}
              />
            </div>
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={() => setCancellingAppointment(null)} className="btn-secondary">
                Abbrechen
              </button>
              <button type="button" onClick={handleCancelConfirm} className="btn-primary">
                Stornieren
              </button>
            </div>
          </div>
        </div>
      )}

      {showImportForm && (
        <div className="modal-overlay" onClick={() => setShowImportForm(false)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>Externen Termin importieren</h2>
            <p className="muted" style={{ marginBottom: '1rem' }}>
              Termine von Termin-Marktplatz oder anderen Buchungssystemen manuell importieren.
            </p>
            <form onSubmit={handleImportSubmit}>
              <div className="form-group">
                <label htmlFor="imp-ext-id">Externe Buchungs-ID *</label>
                <input
                  id="imp-ext-id"
                  type="text"
                  value={importForm.external_booking_id}
                  onChange={(e) => setImportForm({ ...importForm, external_booking_id: e.target.value })}
                  placeholder="z.B. TMP-2024-001"
                  required
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Datum *</label>
                  <input
                    type="date"
                    value={importForm.date || weekDates[0].toISOString().slice(0, 10)}
                    onChange={(e) => setImportForm({ ...importForm, date: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Von</label>
                  <input
                    type="time"
                    value={importForm.startTime}
                    onChange={(e) => setImportForm({ ...importForm, startTime: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Bis</label>
                  <input
                    type="time"
                    value={importForm.endTime}
                    onChange={(e) => setImportForm({ ...importForm, endTime: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Kunde Vorname</label>
                  <input
                    type="text"
                    value={importForm.customer_first_name}
                    onChange={(e) => setImportForm({ ...importForm, customer_first_name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Kunde Nachname</label>
                  <input
                    type="text"
                    value={importForm.customer_last_name}
                    onChange={(e) => setImportForm({ ...importForm, customer_last_name: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>E-Mail</label>
                  <input
                    type="email"
                    value={importForm.customer_email}
                    onChange={(e) => setImportForm({ ...importForm, customer_email: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Telefon</label>
                  <input
                    type="text"
                    value={importForm.customer_phone}
                    onChange={(e) => setImportForm({ ...importForm, customer_phone: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Kennzeichen</label>
                  <input
                    type="text"
                    value={importForm.vehicle_license_plate}
                    onChange={(e) => setImportForm({ ...importForm, vehicle_license_plate: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>FIN</label>
                  <input
                    type="text"
                    value={importForm.vehicle_vin}
                    onChange={(e) => setImportForm({ ...importForm, vehicle_vin: e.target.value })}
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Titel</label>
                <input
                  type="text"
                  value={importForm.title}
                  onChange={(e) => setImportForm({ ...importForm, title: e.target.value })}
                  placeholder="z.B. Ölwechsel"
                />
              </div>
              <div className="form-group">
                <label>Beschreibung</label>
                <textarea
                  value={importForm.description}
                  onChange={(e) => setImportForm({ ...importForm, description: e.target.value })}
                  rows={2}
                />
              </div>
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => setShowImportForm(false)} className="btn-secondary">
                  Abbrechen
                </button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Wird importiert...' : 'Importieren'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <p>Laden...</p>
      ) : (
        <div className="calendar-wrapper">
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
            {[6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22].map((hour) => (
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
                const top = (start.getHours() - 6 + start.getMinutes() / 60) * 50
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
                    title={getTooltipText(a)}
                  >
                    <span className="calendar-apt-title">{a.title || TYPE_LABELS[a.appointment_type]}</span>
                    <span className="calendar-apt-time">
                      {formatTime(a.starts_at)}–{formatTime(a.ends_at)}
                    </span>
                    {(getDisplayName(a) !== '–' || a.customer_email || a.customer_phone) && (
                      <span className="calendar-apt-customer">
                        {getDisplayName(a) !== '–' && getDisplayName(a)}
                        {a.customer_email && (getDisplayName(a) !== '–' ? ' · ' : '') + a.customer_email}
                        {a.customer_phone && (a.customer_email || getDisplayName(a) !== '–' ? ' · ' : '') + a.customer_phone}
                      </span>
                    )}
                    <div className="calendar-apt-actions">
                      <button
                        type="button"
                        className="calendar-apt-edit"
                        onClick={(e) => { e.stopPropagation(); handleEditClick(a) }}
                        title="Bearbeiten"
                      >
                        ✎
                      </button>
                      <button
                        type="button"
                        className="calendar-apt-cancel"
                        onClick={(e) => { e.stopPropagation(); handleCancelClick(a) }}
                        title="Stornieren"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                )
              })
            })}
          </div>
        </div>
        </div>
      )}
    </div>
  )
}
