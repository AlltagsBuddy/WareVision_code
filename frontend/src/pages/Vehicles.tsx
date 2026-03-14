import { useEffect, useState } from 'react'
import { vehiclesApi, customersApi, manufacturersApi, workshopOrdersApi } from '../api/client'

const STATUS_LABELS: Record<string, string> = {
  new: 'Neu',
  planned: 'Geplant',
  in_progress: 'In Arbeit',
  completed: 'Abgeschlossen',
  invoiced: 'Abgerechnet',
  cancelled: 'Storniert',
}

export default function Vehicles() {
  const [vehicles, setVehicles] = useState<any[]>([])
  const [customers, setCustomers] = useState<any[]>([])
  const [manufacturers, setManufacturers] = useState<any[]>([])
  const [models, setModels] = useState<any[]>([])
  const [customerFilter, setCustomerFilter] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form, setForm] = useState({
    customer_id: '',
    manufacturer_id: '',
    vehicle_model_id: '',
    model_name_free: '',
    category: 'motorcycle',
    build_year: '',
    vin: '',
    license_plate: '',
    mileage: '',
    notes: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [detailVehicle, setDetailVehicle] = useState<any | null>(null)
  const [vehicleOrders, setVehicleOrders] = useState<any[]>([])

  useEffect(() => {
    Promise.all([
      vehiclesApi.list({ customer_id: customerFilter || undefined }),
      customersApi.list(),
      manufacturersApi.list(),
    ]).then(([vehs, custs, manfs]) => {
      setVehicles(vehs)
      setCustomers(custs)
      setManufacturers(manfs)
    }).finally(() => setLoading(false))
  }, [customerFilter])

  useEffect(() => {
    if (form.manufacturer_id) {
      manufacturersApi.getModels(form.manufacturer_id).then(setModels).catch(() => setModels([]))
    } else {
      setModels([])
      setForm((f) => ({ ...f, vehicle_model_id: '' }))
    }
  }, [form.manufacturer_id])

  const getCustomerName = (id: string) => {
    const c = customers.find((x) => x.id === id)
    return c ? (c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || '–') : '–'
  }

  const resetForm = () => {
    setForm({
      customer_id: '',
      manufacturer_id: '',
      vehicle_model_id: '',
      model_name_free: '',
      category: 'motorcycle',
      build_year: '',
      vin: '',
      license_plate: '',
      mileage: '',
      notes: '',
    })
    setEditing(null)
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.customer_id || !form.manufacturer_id) {
      setError('Kunde und Hersteller erforderlich.')
      return
    }
    const data = {
      customer_id: form.customer_id,
      manufacturer_id: form.manufacturer_id,
      vehicle_model_id: form.vehicle_model_id || undefined,
      model_name_free: form.model_name_free || undefined,
      category: form.category,
      build_year: form.build_year ? parseInt(form.build_year, 10) : undefined,
      vin: form.vin || undefined,
      license_plate: form.license_plate || undefined,
      mileage: form.mileage ? parseInt(form.mileage, 10) : undefined,
      notes: form.notes || undefined,
    }
    setSubmitting(true)
    try {
      if (editing) {
        const { customer_id: _, ...updateData } = data
        await vehiclesApi.update(editing.id, updateData)
        setVehicles((prev) => prev.map((v) => (v.id === editing.id ? { ...v, ...data } : v)))
      } else {
        await vehiclesApi.create(data)
        const updated = await vehiclesApi.list({ customer_id: customerFilter || undefined })
        setVehicles(updated)
      }
      setShowForm(false)
      resetForm()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (v: any) => {
    if (!confirm(`Fahrzeug "${v.license_plate || v.vin || v.id}" wirklich löschen?`)) return
    try {
      await vehiclesApi.delete(v.id)
      setVehicles((prev) => prev.filter((x) => x.id !== v.id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const openDetail = async (v: any) => {
    setDetailVehicle(v)
    workshopOrdersApi.list({ vehicle_id: v.id }).then(setVehicleOrders)
  }

  const openEdit = (v: any) => {
    setEditing(v)
    setForm({
      customer_id: v.customer_id,
      manufacturer_id: v.manufacturer_id,
      vehicle_model_id: v.vehicle_model_id || '',
      model_name_free: v.model_name_free || '',
      category: v.category,
      build_year: v.build_year ? String(v.build_year) : '',
      vin: v.vin || '',
      license_plate: v.license_plate || '',
      mileage: v.mileage ? String(v.mileage) : '',
      notes: v.notes || '',
    })
    setShowForm(true)
  }

  return (
    <div className="page">
      <h1>Fahrzeuge</h1>
      <div className="toolbar">
        <select value={customerFilter} onChange={(e) => setCustomerFilter(e.target.value)} className="select">
          <option value="">Alle Kunden</option>
          {customers.map((c) => (
            <option key={c.id} value={c.id}>{getCustomerName(c.id)}</option>
          ))}
        </select>
        <button type="button" onClick={() => { resetForm(); setShowForm(true) }} className="btn-primary">+ Neues Fahrzeug</button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => { setShowForm(false); resetForm() }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? 'Fahrzeug bearbeiten' : 'Neues Fahrzeug'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Kunde *</label>
                <select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} required disabled={!!editing}>
                  <option value="">– Bitte wählen –</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>{getCustomerName(c.id)}</option>
                  ))}
                </select>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Hersteller *</label>
                  <select value={form.manufacturer_id} onChange={(e) => setForm({ ...form, manufacturer_id: e.target.value, vehicle_model_id: '' })} required>
                    <option value="">– Bitte wählen –</option>
                    {manufacturers.map((m) => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Modell</label>
                  <select value={form.vehicle_model_id} onChange={(e) => setForm({ ...form, vehicle_model_id: e.target.value })}>
                    <option value="">– Freitext –</option>
                    {models.map((m) => (
                      <option key={m.id} value={m.id}>{m.name} {m.variant || ''}</option>
                    ))}
                  </select>
                </div>
              </div>
              {form.vehicle_model_id === '' && (
                <div className="form-group">
                  <label>Modell (Freitext)</label>
                  <input value={form.model_name_free} onChange={(e) => setForm({ ...form, model_name_free: e.target.value })} placeholder="z.B. XYZ 450" />
                </div>
              )}
              <div className="form-row">
                <div className="form-group">
                  <label>Kategorie</label>
                  <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                    <option value="motorcycle">Motorrad</option>
                    <option value="quad">Quad</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Baujahr</label>
                  <input type="number" value={form.build_year} onChange={(e) => setForm({ ...form, build_year: e.target.value })} placeholder="2020" min="1900" max="2030" />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Kennzeichen</label>
                  <input value={form.license_plate} onChange={(e) => setForm({ ...form, license_plate: e.target.value })} placeholder="B-XX 1234" />
                </div>
                <div className="form-group">
                  <label>VIN</label>
                  <input value={form.vin} onChange={(e) => setForm({ ...form, vin: e.target.value })} placeholder="Fahrzeug-Identifikationsnummer" />
                </div>
              </div>
              <div className="form-group">
                <label>Kilometerstand</label>
                <input type="number" value={form.mileage} onChange={(e) => setForm({ ...form, mileage: e.target.value })} placeholder="15000" min="0" />
              </div>
              <div className="form-group">
                <label>Notizen</label>
                <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} />
              </div>
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => { setShowForm(false); resetForm() }} className="btn-secondary">Abbrechen</button>
                <button type="submit" disabled={submitting} className="btn-primary">{submitting ? 'Speichern...' : (editing ? 'Speichern' : 'Anlegen')}</button>
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
              <th>Kennzeichen</th>
              <th>VIN</th>
              <th>Kunde</th>
              <th>Kategorie</th>
              <th>Baujahr</th>
              <th>Kilometer</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.map((v) => (
              <tr key={v.id}>
                <td>{v.license_plate || '–'}</td>
                <td>{v.vin || '–'}</td>
                <td>{getCustomerName(v.customer_id)}</td>
                <td>{v.category === 'quad' ? 'Quad' : 'Motorrad'}</td>
                <td>{v.build_year || '–'}</td>
                <td>{v.mileage != null ? `${v.mileage} km` : '–'}</td>
                <td>
                  <button type="button" onClick={() => openDetail(v)} className="btn-secondary btn-sm">Historie</button>
                  <button type="button" onClick={() => openEdit(v)} className="btn-secondary btn-sm">Bearbeiten</button>
                  <button type="button" onClick={() => handleDelete(v)} className="btn-secondary btn-sm">Löschen</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {detailVehicle && (
        <div className="modal-overlay" onClick={() => setDetailVehicle(null)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>Fahrzeughistorie</h2>
            <p>
              <strong>{detailVehicle.license_plate || detailVehicle.vin || 'Fahrzeug'}</strong>
              {' '}– {getCustomerName(detailVehicle.customer_id)}
              {detailVehicle.build_year && ` (${detailVehicle.build_year})`}
            </p>
            <h3>Werkstattaufträge</h3>
            {vehicleOrders.length === 0 ? (
              <p>Keine Aufträge für dieses Fahrzeug.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Auftragsnummer</th>
                    <th>Status</th>
                    <th>Anliegen</th>
                    <th>Erstellt</th>
                  </tr>
                </thead>
                <tbody>
                  {vehicleOrders.map((o) => (
                    <tr key={o.id}>
                      <td><strong>{o.order_number}</strong></td>
                      <td>{STATUS_LABELS[o.status] || o.status}</td>
                      <td>{o.complaint_description ? (o.complaint_description.slice(0, 60) + (o.complaint_description.length > 60 ? '…' : '')) : '–'}</td>
                      <td>{new Date(o.created_at).toLocaleDateString('de-DE')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={() => setDetailVehicle(null)} className="btn-secondary">Schließen</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
