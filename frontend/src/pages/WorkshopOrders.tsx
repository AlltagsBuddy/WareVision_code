import { useEffect, useState } from 'react'
import { workshopOrdersApi, customersApi, vehiclesApi } from '../api/client'

const STATUS_LABELS: Record<string, string> = {
  new: 'Neu',
  planned: 'Geplant',
  in_progress: 'In Arbeit',
  completed: 'Abgeschlossen',
  invoiced: 'Abgerechnet',
  cancelled: 'Storniert',
}

export default function WorkshopOrders() {
  const [orders, setOrders] = useState<any[]>([])
  const [customers, setCustomers] = useState<any[]>([])
  const [allVehicles, setAllVehicles] = useState<any[]>([])
  const [customerVehicles, setCustomerVehicles] = useState<Record<string, any[]>>({})
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [form, setForm] = useState({
    customer_id: '',
    vehicle_id: '',
    complaint_description: '',
    internal_notes: '',
    mileage_at_checkin: '',
    estimated_work_minutes: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      workshopOrdersApi.list({ status_filter: statusFilter || undefined }),
      customersApi.list(),
      vehiclesApi.list(),
    ])
      .then(([ordersData, customersData, vehiclesData]) => {
        setOrders(ordersData)
        setCustomers(customersData)
        setAllVehicles(vehiclesData)
      })
      .finally(() => setLoading(false))
  }, [statusFilter])

  useEffect(() => {
    if (form.customer_id) {
      vehiclesApi.list({ customer_id: form.customer_id }).then((vehicles) => {
        setCustomerVehicles((prev) => ({ ...prev, [form.customer_id]: vehicles }))
      })
    } else {
      setForm((f) => ({ ...f, vehicle_id: '' }))
    }
  }, [form.customer_id])

  const getCustomerName = (customerId: string) => {
    const c = customers.find((x) => x.id === customerId)
    if (!c) return '–'
    return c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || '–'
  }

  const getVehicleLabel = (vehicleId: string) => {
    const v = allVehicles.find((x) => x.id === vehicleId)
    if (!v) return '–'
    return v.license_plate || v.vin || v.id?.slice(0, 8) || '–'
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.customer_id || !form.vehicle_id) {
      setError('Bitte Kunde und Fahrzeug auswählen.')
      return
    }
    setSubmitting(true)
    try {
      await workshopOrdersApi.create({
        customer_id: form.customer_id,
        vehicle_id: form.vehicle_id,
        complaint_description: form.complaint_description || undefined,
        internal_notes: form.internal_notes || undefined,
        mileage_at_checkin: form.mileage_at_checkin ? parseInt(form.mileage_at_checkin, 10) : undefined,
        estimated_work_minutes: form.estimated_work_minutes ? parseInt(form.estimated_work_minutes, 10) : undefined,
      })
      setShowForm(false)
      setForm({ customer_id: '', vehicle_id: '', complaint_description: '', internal_notes: '', mileage_at_checkin: '', estimated_work_minutes: '' })
      const updated = await workshopOrdersApi.list({ status_filter: statusFilter || undefined })
      setOrders(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Anlegen')
    } finally {
      setSubmitting(false)
    }
  }

  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    } catch {
      return '–'
    }
  }

  const vehicles = form.customer_id ? (customerVehicles[form.customer_id] || []) : []

  return (
    <div className="page">
      <h1>Werkstattaufträge</h1>
      <div className="toolbar">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="select"
        >
          <option value="">Alle Status</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <button type="button" onClick={() => setShowForm(true)} className="btn-primary">
          + Neuer Auftrag
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Neuer Werkstattauftrag</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="customer">Kunde *</label>
                <select
                  id="customer"
                  value={form.customer_id}
                  onChange={(e) => setForm({ ...form, customer_id: e.target.value, vehicle_id: '' })}
                  required
                >
                  <option value="">– Bitte wählen –</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email || c.id}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="vehicle">Fahrzeug *</label>
                <select
                  id="vehicle"
                  value={form.vehicle_id}
                  onChange={(e) => setForm({ ...form, vehicle_id: e.target.value })}
                  required
                  disabled={!form.customer_id}
                >
                  <option value="">– Bitte wählen –</option>
                  {vehicles.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.license_plate || v.vin || 'Fahrzeug'} {v.build_year ? `(${v.build_year})` : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="complaint">Kundenbeschwerde / Anliegen</label>
                <textarea
                  id="complaint"
                  value={form.complaint_description}
                  onChange={(e) => setForm({ ...form, complaint_description: e.target.value })}
                  rows={3}
                  placeholder="Beschreibung des Problems..."
                />
              </div>
              <div className="form-group">
                <label htmlFor="notes">Interne Notizen</label>
                <textarea
                  id="notes"
                  value={form.internal_notes}
                  onChange={(e) => setForm({ ...form, internal_notes: e.target.value })}
                  rows={2}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="mileage">Kilometerstand bei Abgabe</label>
                  <input
                    id="mileage"
                    type="number"
                    value={form.mileage_at_checkin}
                    onChange={(e) => setForm({ ...form, mileage_at_checkin: e.target.value })}
                    placeholder="z.B. 15000"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="est_min">Geschätzte Arbeitszeit (Min.)</label>
                  <input
                    id="est_min"
                    type="number"
                    value={form.estimated_work_minutes}
                    onChange={(e) => setForm({ ...form, estimated_work_minutes: e.target.value })}
                    placeholder="z.B. 60"
                  />
                </div>
              </div>
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
                  Abbrechen
                </button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Wird erstellt...' : 'Auftrag anlegen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <p>Laden...</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Auftragsnummer</th>
              <th>Status</th>
              <th>Kunde</th>
              <th>Fahrzeug</th>
              <th>Anliegen</th>
              <th>Erstellt</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 ? (
              <tr>
                <td colSpan={6}>Keine Werkstattaufträge vorhanden.</td>
              </tr>
            ) : (
              orders.map((o) => (
                <tr key={o.id}>
                  <td><strong>{o.order_number}</strong></td>
                  <td>{STATUS_LABELS[o.status] || o.status}</td>
                  <td>{getCustomerName(o.customer_id)}</td>
                  <td>{getVehicleLabel(o.vehicle_id)}</td>
                  <td>{o.complaint_description ? (o.complaint_description.slice(0, 50) + (o.complaint_description.length > 50 ? '…' : '')) : '–'}</td>
                  <td>{formatDate(o.created_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
