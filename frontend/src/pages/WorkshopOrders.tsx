import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { workshopOrdersApi, customersApi, vehiclesApi, articlesApi, appointmentsApi, documentsApi } from '../api/client'

const STATUS_LABELS: Record<string, string> = {
  new: 'Neu',
  planned: 'Geplant',
  in_progress: 'In Arbeit',
  completed: 'Abgeschlossen',
  invoiced: 'Abgerechnet',
  cancelled: 'Storniert',
}

const ITEM_TYPE_LABELS: Record<string, string> = {
  labor: 'Arbeit',
  material: 'Teile',
  service: 'Service',
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
    appointment_id: '',
    complaint_description: '',
    internal_notes: '',
    mileage_at_checkin: '',
    estimated_work_minutes: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [detailOrder, setDetailOrder] = useState<any | null>(null)
  const [items, setItems] = useState<any[]>([])
  const [orderDocuments, setOrderDocuments] = useState<any[]>([])
  const [articles, setArticles] = useState<any[]>([])
  const [showItemForm, setShowItemForm] = useState(false)
  const [itemForm, setItemForm] = useState({
    item_type: 'labor' as string,
    article_id: '',
    description: '',
    quantity: 1,
    unit: 'Std.',
    unit_price: 0,
    vat_rate: 19,
  })
  const [itemSubmitting, setItemSubmitting] = useState(false)
  const [itemError, setItemError] = useState('')

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

  const [customerAppointments, setCustomerAppointments] = useState<Record<string, any[]>>({})

  useEffect(() => {
    if (form.customer_id) {
      vehiclesApi.list({ customer_id: form.customer_id }).then((vehicles) => {
        setCustomerVehicles((prev) => ({ ...prev, [form.customer_id]: vehicles }))
      })
      const from = new Date()
      const to = new Date()
      to.setDate(to.getDate() + 60)
      appointmentsApi.list({
        customer_id: form.customer_id,
        from_date: from.toISOString(),
        to_date: to.toISOString(),
      }).then((apts) => {
        setCustomerAppointments((prev) => ({ ...prev, [form.customer_id]: apts.filter((a: any) => a.status !== 'cancelled') }))
      }).catch(() => setCustomerAppointments((prev) => ({ ...prev, [form.customer_id]: [] })))
    } else {
      setForm((f) => ({ ...f, vehicle_id: '', appointment_id: '' }))
    }
  }, [form.customer_id])

  const openDetail = async (order: any) => {
    setDetailOrder(order)
    setShowItemForm(false)
    articlesApi.list().then(setArticles)
    workshopOrdersApi.getItems(order.id).then(setItems)
    documentsApi.list({ vehicle_id: order.vehicle_id }).then(setOrderDocuments)
  }

  const closeDetail = () => {
    setDetailOrder(null)
    setItems([])
  }

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detailOrder || !itemForm.description.trim()) {
      setItemError('Bitte Beschreibung angeben.')
      return
    }
    setItemSubmitting(true)
    setItemError('')
    try {
      const data = {
        item_type: itemForm.item_type,
        description: itemForm.description.trim(),
        quantity: itemForm.quantity,
        unit: itemForm.unit || undefined,
        unit_price: itemForm.unit_price,
        vat_rate: itemForm.vat_rate,
        ...(itemForm.item_type === 'material' && itemForm.article_id ? { article_id: itemForm.article_id } : {}),
      }
      await workshopOrdersApi.addItem(detailOrder.id, data)
      const updated = await workshopOrdersApi.getItems(detailOrder.id)
      setItems(updated)
      setShowItemForm(false)
      setItemForm({
        item_type: 'labor',
        article_id: '',
        description: '',
        quantity: 1,
        unit: 'Std.',
        unit_price: 0,
        vat_rate: 19,
      })
    } catch (err) {
      setItemError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setItemSubmitting(false)
    }
  }

  const handleDeleteItem = async (itemId: string) => {
    if (!detailOrder || !confirm('Position wirklich entfernen?')) return
    try {
      await workshopOrdersApi.deleteItem(detailOrder.id, itemId)
      setItems((prev) => prev.filter((i) => i.id !== itemId))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleStatusChange = async (newStatus: string) => {
    if (!detailOrder) return
    try {
      await workshopOrdersApi.update(detailOrder.id, { status: newStatus })
      setDetailOrder((o: any) => ({ ...o, status: newStatus }))
      const updated = await workshopOrdersApi.list({ status_filter: statusFilter || undefined })
      setOrders(updated)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const itemsTotal = items.reduce((sum, i) => sum + Number(i.quantity) * Number(i.unit_price), 0)

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
        appointment_id: form.appointment_id || undefined,
        complaint_description: form.complaint_description || undefined,
        internal_notes: form.internal_notes || undefined,
        mileage_at_checkin: form.mileage_at_checkin ? parseInt(form.mileage_at_checkin, 10) : undefined,
        estimated_work_minutes: form.estimated_work_minutes ? parseInt(form.estimated_work_minutes, 10) : undefined,
      })
      setShowForm(false)
      setForm({ customer_id: '', vehicle_id: '', appointment_id: '', complaint_description: '', internal_notes: '', mileage_at_checkin: '', estimated_work_minutes: '' })
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
                <label htmlFor="appointment">Termin (optional)</label>
                <select
                  id="appointment"
                  value={form.appointment_id}
                  onChange={(e) => setForm({ ...form, appointment_id: e.target.value })}
                  disabled={!form.customer_id}
                >
                  <option value="">– Kein Termin –</option>
                  {(customerAppointments[form.customer_id] || []).map((a: any) => (
                    <option key={a.id} value={a.id}>
                      {new Date(a.starts_at).toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })} – {a.title || a.appointment_type}
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
        <div className="table-wrapper">
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
                <tr key={o.id} onClick={() => openDetail(o)} style={{ cursor: 'pointer' }}>
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
        </div>
      )}

      {detailOrder && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>Auftrag {detailOrder.order_number}</h2>
            <p>
              <strong>Kunde:</strong> {getCustomerName(detailOrder.customer_id)} &nbsp;
              <strong>Fahrzeug:</strong> {getVehicleLabel(detailOrder.vehicle_id)}
              {detailOrder.appointment_id && (
                <> &nbsp; <strong>Termin verknüpft</strong></>
              )}
            </p>
            <p>{detailOrder.complaint_description || '–'}</p>
            <div className="form-row" style={{ marginBottom: '1rem' }}>
              <label>Status:</label>
              <select
                value={detailOrder.status}
                onChange={(e) => handleStatusChange(e.target.value)}
                className="select"
              >
                {Object.entries(STATUS_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>

            {orderDocuments.length > 0 && (
              <>
                <h3>Dokumente (Fahrzeug)</h3>
                <ul style={{ listStyle: 'none', padding: 0, marginBottom: '1rem' }}>
                  {orderDocuments.map((d) => (
                    <li key={d.id} style={{ marginBottom: '0.25rem' }}>
                      <button
                        type="button"
                        onClick={() => documentsApi.download(d.id, d.filename)}
                        className="btn-secondary btn-sm"
                        style={{ padding: '0.25rem 0.5rem' }}
                      >
                        {d.filename}
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
            <h3>Positionen</h3>
            {items.length === 0 ? (
              <p>Keine Positionen.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Typ</th>
                    <th>Beschreibung</th>
                    <th>Menge</th>
                    <th>Einheit</th>
                    <th>Preis</th>
                    <th>Gesamt</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((i) => (
                    <tr key={i.id}>
                      <td>{ITEM_TYPE_LABELS[i.item_type] || i.item_type}</td>
                      <td>{i.description}</td>
                      <td>{Number(i.quantity)}</td>
                      <td>{i.unit || '–'}</td>
                      <td>{Number(i.unit_price).toFixed(2)} €</td>
                      <td>{(Number(i.quantity) * Number(i.unit_price)).toFixed(2)} €</td>
                      <td>
                        <button type="button" onClick={() => handleDeleteItem(i.id)} className="btn-secondary btn-sm">Entfernen</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <td colSpan={5}><strong>Summe</strong></td>
                    <td><strong>{itemsTotal.toFixed(2)} €</strong></td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            )}

            {!showItemForm ? (
              <button type="button" onClick={() => setShowItemForm(true)} className="btn-primary" style={{ marginTop: '0.5rem' }}>
                + Position hinzufügen
              </button>
            ) : (
              <form onSubmit={handleAddItem} style={{ marginTop: '1rem', padding: '1rem', border: '1px solid var(--color-border)', borderRadius: 8 }}>
                <h4>Neue Position</h4>
                <div className="form-row">
                  <div className="form-group">
                    <label>Typ</label>
                    <select
                      value={itemForm.item_type}
                      onChange={(e) => {
                        const t = e.target.value
                        setItemForm({
                          ...itemForm,
                          item_type: t,
                          unit: t === 'labor' ? 'Std.' : t === 'material' ? 'Stück' : '',
                        })
                      }}
                    >
                      <option value="labor">Arbeit</option>
                      <option value="material">Teile</option>
                      <option value="service">Service</option>
                    </select>
                  </div>
                  {itemForm.item_type === 'material' && (
                    <div className="form-group" style={{ flex: 1 }}>
                      <label>Artikel</label>
                      <select
                        value={itemForm.article_id}
                        onChange={(e) => {
                          const a = articles.find((x) => x.id === e.target.value)
                          setItemForm({
                            ...itemForm,
                            article_id: e.target.value,
                            description: a ? a.name : itemForm.description,
                            unit_price: a ? Number(a.sales_price_b2c) : itemForm.unit_price,
                          })
                        }}
                      >
                        <option value="">– Manuell –</option>
                        {articles.map((a) => (
                          <option key={a.id} value={a.id}>{a.article_number} – {a.name} ({Number(a.sales_price_b2c).toFixed(2)} €)</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>
                <div className="form-group">
                  <label>Beschreibung *</label>
                  <input
                    value={itemForm.description}
                    onChange={(e) => setItemForm({ ...itemForm, description: e.target.value })}
                    placeholder="z.B. Ölwechsel, Bremsbeläge"
                    required
                  />
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Menge</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={itemForm.quantity}
                      onChange={(e) => setItemForm({ ...itemForm, quantity: parseFloat(e.target.value) || 1 })}
                    />
                  </div>
                  <div className="form-group">
                    <label>Einheit</label>
                    <input
                      value={itemForm.unit}
                      onChange={(e) => setItemForm({ ...itemForm, unit: e.target.value })}
                      placeholder="Std. / Stück"
                    />
                  </div>
                  <div className="form-group">
                    <label>Preis (€)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={itemForm.unit_price}
                      onChange={(e) => setItemForm({ ...itemForm, unit_price: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="form-group">
                    <label>MwSt %</label>
                    <input
                      type="number"
                      step="0.01"
                      value={itemForm.vat_rate}
                      onChange={(e) => setItemForm({ ...itemForm, vat_rate: parseFloat(e.target.value) || 19 })}
                    />
                  </div>
                </div>
                {itemError && <p className="error">{itemError}</p>}
                <div className="form-actions">
                  <button type="button" onClick={() => setShowItemForm(false)} className="btn-secondary">Abbrechen</button>
                  <button type="submit" disabled={itemSubmitting} className="btn-primary">{itemSubmitting ? 'Speichern...' : 'Hinzufügen'}</button>
                </div>
              </form>
            )}

            <div className="form-actions" style={{ marginTop: '1.5rem' }}>
              {detailOrder.status !== 'invoiced' && detailOrder.status !== 'cancelled' && items.length > 0 && (
                <Link
                  to="/invoices"
                  state={{ workshopOrderId: detailOrder.id }}
                  onClick={closeDetail}
                  className="btn-primary"
                >
                  Rechnung erstellen
                </Link>
              )}
              <button type="button" onClick={closeDetail} className="btn-secondary">Schließen</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
