import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import { workshopOrdersApi, customersApi, vehiclesApi, articlesApi, appointmentsApi, manufacturersApi, maintenancePlansApi, laborRatesApi } from '../api/client'
import { buildYearLabel } from '../utils/buildYear'
import PreviewModal from '../components/PreviewModal'
import OrderPhotos from '../components/OrderPhotos'

// Wiederverwendbare Suchbox: Dropdown wird via Portal am body gerendert (umgeht Modal-Overflow/Stacking)
function ComboBox({
  options,
  value,
  onChange,
  placeholder = '– Suchen oder auswählen –',
  disabled = false,
  emptyLabel = '– Keine Auswahl –',
}: {
  options: { value: string; label: string; sub?: string }[]
  value: string
  onChange: (v: string) => void
  placeholder?: string
  disabled?: boolean
  emptyLabel?: string
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [rect, setRect] = useState<DOMRect | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const target = e.target as Node
      if (
        inputRef.current && !inputRef.current.contains(target) &&
        dropRef.current && !dropRef.current.contains(target)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const selectedLabel = options.find((o) => o.value === value)?.label ?? ''
  const q = query.toLowerCase()
  const filtered = q
    ? options.filter((o) => o.label.toLowerCase().includes(q) || (o.sub || '').toLowerCase().includes(q))
    : options

  const handleOpen = () => {
    if (disabled) return
    if (inputRef.current) setRect(inputRef.current.getBoundingClientRect())
    setOpen(true)
    setQuery('')
  }

  const dropdown = open && !disabled && rect && createPortal(
    <div
      ref={dropRef}
      style={{
        position: 'fixed',
        zIndex: 9999,
        top: rect.bottom + 4,
        left: rect.left,
        width: rect.width,
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 6,
        maxHeight: 220,
        overflowY: 'auto',
        boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
      }}
    >
      <div
        style={{ padding: '0.45rem 0.75rem', cursor: 'pointer', color: 'var(--color-text-muted)', fontSize: '0.88rem' }}
        onMouseDown={() => { onChange(''); setOpen(false); setQuery('') }}
      >
        {emptyLabel}
      </div>
      {filtered.length === 0 && (
        <div style={{ padding: '0.45rem 0.75rem', color: 'var(--color-text-muted)', fontSize: '0.88rem' }}>
          Keine Treffer
        </div>
      )}
      {filtered.map((o) => (
        <div
          key={o.value}
          onMouseDown={() => { onChange(o.value); setOpen(false); setQuery('') }}
          style={{
            padding: '0.45rem 0.75rem',
            cursor: 'pointer',
            background: o.value === value ? 'var(--color-primary)' : 'transparent',
            color: o.value === value ? '#fff' : 'var(--color-text)',
          }}
        >
          <div style={{ fontSize: '0.9rem' }}>{o.label}</div>
          {o.sub && <div style={{ fontSize: '0.78rem', opacity: 0.7 }}>{o.sub}</div>}
        </div>
      ))}
    </div>,
    document.body
  )

  return (
    <div style={{ position: 'relative' }}>
      <input
        ref={inputRef}
        type="text"
        value={open ? query : selectedLabel}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={handleOpen}
        placeholder={disabled ? '' : placeholder}
        disabled={disabled}
        style={{ width: '100%', boxSizing: 'border-box' }}
        autoComplete="off"
      />
      {dropdown}
    </div>
  )
}

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
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState('created_at')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  // Hersteller, Wartungspläne und Stundenpreise für das Formular
  const [manufacturers, setManufacturers] = useState<any[]>([])
  const [vehicleModels, setVehicleModels] = useState<any[]>([])
  const [maintenancePlans, setMaintenancePlans] = useState<any[]>([])
  const [planTasks, setPlanTasks] = useState<any[]>([])
  const [laborRates, setLaborRates] = useState<any[]>([])

  const [form, setForm] = useState({
    customer_id: '',
    vehicle_id: '',
    // Marke + Modell (aus Fahrzeug befüllt, manuell überschreibbar)
    manufacturer_id: '',
    vehicle_model_id: '',
    maintenance_plan_id: '',
    labor_rate_id: '',
    appointment_id: '',
    // Neuen Termin direkt anlegen
    apt_mode: 'existing' as 'existing' | 'new',
    new_apt_date: new Date().toISOString().slice(0, 10),
    new_apt_start: '08:00',
    new_apt_end: '09:00',
    new_apt_title: 'Werkstatttermin',
    complaint_description: '',
    internal_notes: '',
    mileage_at_checkin: '',
    estimated_work_minutes: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [detailOrder, setDetailOrder] = useState<any | null>(null)
  const [items, setItems] = useState<any[]>([])
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null)
  const [articles, setArticles] = useState<any[]>([])
  const [showItemForm, setShowItemForm] = useState(false)
  const [itemForm, setItemForm] = useState({
    item_type: 'labor' as string,
    article_id: '',
    labor_rate_id: '',
    description: '',
    quantity: 1,
    unit: 'Std.',
    unit_price: 0,
    vat_rate: 19,
  })
  const [itemSubmitting, setItemSubmitting] = useState(false)
  const [itemError, setItemError] = useState('')
  const [stockWarning, setStockWarning] = useState('')

  useEffect(() => {
    Promise.all([
      workshopOrdersApi.list({ status_filter: statusFilter || undefined }),
      customersApi.list(),
      vehiclesApi.list(),
      manufacturersApi.list(),
      maintenancePlansApi.list(),
      laborRatesApi.list(),
    ])
      .then(([ordersData, customersData, vehiclesData, manuData, plansData, ratesData]) => {
        setOrders(ordersData)
        setCustomers(customersData)
        setAllVehicles(vehiclesData)
        setManufacturers(manuData)
        setMaintenancePlans(plansData)
        setLaborRates(ratesData)
        // Standard-Stundenpreis vorauswählen
        const defaultRate = ratesData.find((r: any) => r.is_default && r.is_active)
        if (defaultRate) setForm((f) => ({ ...f, labor_rate_id: defaultRate.id }))
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
      setForm((f) => ({ ...f, vehicle_id: '', appointment_id: '', manufacturer_id: '', vehicle_model_id: '' }))
    }
  }, [form.customer_id])

  // Wenn Fahrzeug gewählt: Marke + Modell automatisch befüllen
  useEffect(() => {
    if (!form.vehicle_id) return
    const v = (customerVehicles[form.customer_id] || allVehicles).find((x: any) => x.id === form.vehicle_id)
    if (v) {
      const newManufacturerId = v.manufacturer_id || ''
      setForm((f) => ({ ...f, manufacturer_id: newManufacturerId, vehicle_model_id: v.vehicle_model_id || '' }))
      if (newManufacturerId) {
        manufacturersApi.getModels(newManufacturerId).then(setVehicleModels).catch(() => setVehicleModels([]))
      }
    }
  }, [form.vehicle_id])

  // Modelle nachladen wenn Marke manuell gewechselt wird
  useEffect(() => {
    if (form.manufacturer_id) {
      manufacturersApi.getModels(form.manufacturer_id).then(setVehicleModels).catch(() => setVehicleModels([]))
    } else {
      setVehicleModels([])
    }
  }, [form.manufacturer_id])

  // Wartungsplan-Aufgaben laden wenn Plan ausgewählt wird
  useEffect(() => {
    if (form.maintenance_plan_id) {
      maintenancePlansApi.getTasks(form.maintenance_plan_id).then(setPlanTasks).catch(() => setPlanTasks([]))
    } else {
      setPlanTasks([])
    }
  }, [form.maintenance_plan_id])

  const openDetail = async (order: any) => {
    setDetailOrder(order)
    setShowItemForm(false)
    articlesApi.list().then(setArticles)
    workshopOrdersApi.getItems(order.id).then(setItems)
  }

  const closeDetail = () => {
    if (pdfPreviewUrl) {
      URL.revokeObjectURL(pdfPreviewUrl)
      setPdfPreviewUrl(null)
    }
    setDetailOrder(null)
    setItems([])
  }

  const openPdfPreview = async () => {
    if (!detailOrder) return
    try {
      const blob = await workshopOrdersApi.getPdf(detailOrder.id)
      const url = URL.createObjectURL(blob)
      setPdfPreviewUrl(url)
    } catch {
      alert('PDF konnte nicht geladen werden')
    }
  }

  const closePdfPreview = () => {
    if (pdfPreviewUrl) URL.revokeObjectURL(pdfPreviewUrl)
    setPdfPreviewUrl(null)
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
      setStockWarning('')
      setItemForm({
        item_type: 'labor',
        article_id: '',
        labor_rate_id: '',
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
      // Neuen Termin anlegen wenn gewünscht
      let appointmentId = form.appointment_id || undefined
      if (form.apt_mode === 'new' && form.new_apt_date) {
        const starts = new Date(`${form.new_apt_date}T${form.new_apt_start}:00`)
        const ends = new Date(`${form.new_apt_date}T${form.new_apt_end}:00`)
        if (ends <= starts) {
          setError('Endzeit muss nach Startzeit liegen.')
          setSubmitting(false)
          return
        }
        const apt = await appointmentsApi.create({
          customer_id: form.customer_id,
          vehicle_id: form.vehicle_id,
          appointment_type: 'workshop',
          title: form.new_apt_title || 'Werkstatttermin',
          starts_at: starts.toISOString(),
          ends_at: ends.toISOString(),
        })
        appointmentId = apt.id
      }

      await workshopOrdersApi.create({
        customer_id: form.customer_id,
        vehicle_id: form.vehicle_id,
        appointment_id: appointmentId,
        maintenance_plan_id: form.maintenance_plan_id || undefined,
        labor_rate_id: (form.labor_rate_id && form.estimated_work_minutes) ? form.labor_rate_id : undefined,
        complaint_description: form.complaint_description || undefined,
        internal_notes: form.internal_notes || undefined,
        mileage_at_checkin: form.mileage_at_checkin ? parseInt(form.mileage_at_checkin, 10) : undefined,
        estimated_work_minutes: form.estimated_work_minutes ? parseInt(form.estimated_work_minutes, 10) : undefined,
      })
      setShowForm(false)
      const defaultRate = laborRates.find((r: any) => r.is_default && r.is_active)
      setForm({ customer_id: '', vehicle_id: '', manufacturer_id: '', vehicle_model_id: '', maintenance_plan_id: '', labor_rate_id: defaultRate?.id || '', appointment_id: '', apt_mode: 'existing', new_apt_date: new Date().toISOString().slice(0, 10), new_apt_start: '08:00', new_apt_end: '09:00', new_apt_title: 'Werkstatttermin', complaint_description: '', internal_notes: '', mileage_at_checkin: '', estimated_work_minutes: '' })
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

  const handleSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortField(field); setSortDir('asc') }
  }
  const sortIcon = (field: string) => sortField === field ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ↕'

  const q = search.toLowerCase()
  const displayed = [...orders]
    .filter((o) =>
      !q ||
      getCustomerName(o.customer_id).toLowerCase().includes(q) ||
      getVehicleLabel(o.vehicle_id).toLowerCase().includes(q) ||
      (o.order_number || '').toLowerCase().includes(q)
    )
    .sort((a, b) => {
      let va = '', vb = ''
      if (sortField === 'order_number') { va = a.order_number || ''; vb = b.order_number || '' }
      else if (sortField === 'customer') { va = getCustomerName(a.customer_id); vb = getCustomerName(b.customer_id) }
      else if (sortField === 'vehicle') { va = getVehicleLabel(a.vehicle_id); vb = getVehicleLabel(b.vehicle_id) }
      else if (sortField === 'status') { va = a.status || ''; vb = b.status || '' }
      else { va = a.created_at || ''; vb = b.created_at || '' }
      return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va)
    })

  return (
    <div className="page">
      <h1>Werkstattaufträge</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Kunde, Fahrzeug, Auftragsnr...."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
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
                <label>Kunde *</label>
                <ComboBox
                  options={customers.map((c) => ({
                    value: c.id,
                    label: c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email || c.id,
                    sub: c.email || c.phone || undefined,
                  }))}
                  value={form.customer_id}
                  onChange={(v) => setForm({ ...form, customer_id: v, vehicle_id: '' })}
                  placeholder="Kunde suchen..."
                  emptyLabel="– Kein Kunde –"
                />
              </div>
              <div className="form-group">
                <label>Fahrzeug *</label>
                <ComboBox
                  options={vehicles.map((v) => {
                    const manu = manufacturers.find((m: any) => m.id === v.manufacturer_id)
                    const label = [v.license_plate, v.vin].filter(Boolean).join(' / ') || 'Fahrzeug'
                    const sub = [manu?.name, v.model_name_free, v.build_year ? `Bj. ${v.build_year}` : ''].filter(Boolean).join(' – ')
                    return { value: v.id, label, sub }
                  })}
                  value={form.vehicle_id}
                  onChange={(v) => setForm({ ...form, vehicle_id: v })}
                  placeholder={form.customer_id ? 'Fahrzeug suchen (Kennzeichen, FIN...)' : 'Erst Kunde wählen'}
                  disabled={!form.customer_id}
                  emptyLabel="– Kein Fahrzeug –"
                />
                {form.customer_id && vehicles.length === 0 && (
                  <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                    Keine Fahrzeuge fuer diesen Kunden hinterlegt.
                  </p>
                )}
              </div>

              {/* Marke + Modell */}
              <div className="form-row">
                <div className="form-group" style={{ flex: 1 }}>
                  <label>Marke (optional)</label>
                  <ComboBox
                    options={manufacturers.map((m: any) => ({ value: m.id, label: m.name }))}
                    value={form.manufacturer_id}
                    onChange={(v) => setForm({ ...form, manufacturer_id: v, vehicle_model_id: '' })}
                    placeholder="Marke suchen..."
                    emptyLabel="– Alle Marken –"
                  />
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label>Modell (optional)</label>
                  <ComboBox
                    options={vehicleModels.map((m: any) => ({ value: m.id, label: m.name + (m.variant ? ` ${m.variant}` : '') }))}
                    value={form.vehicle_model_id}
                    onChange={(v) => setForm({ ...form, vehicle_model_id: v })}
                    placeholder={form.manufacturer_id ? 'Modell suchen...' : 'Erst Marke wählen'}
                    disabled={!form.manufacturer_id}
                    emptyLabel="– Alle Modelle –"
                  />
                </div>
              </div>

              {/* Wartungsplan */}
              <div className="form-group">
                <label>Wartungsplan (optional)</label>
                <ComboBox
                  options={maintenancePlans
                    .filter((p: any) => !form.manufacturer_id || p.manufacturer_id === form.manufacturer_id)
                    .map((p: any) => {
                      const manu = manufacturers.find((m: any) => m.id === p.manufacturer_id)
                      const years = buildYearLabel(p)
                      const sub = [manu?.name, years !== 'alle' ? `Baujahr ${years}` : ''].filter(Boolean).join(' · ')
                      return { value: p.id, label: p.name, sub: sub || undefined }
                    })}
                  value={form.maintenance_plan_id}
                  onChange={(v) => setForm({ ...form, maintenance_plan_id: v })}
                  placeholder="Wartungsplan suchen..."
                  emptyLabel="– Automatisch ermitteln –"
                />
                {planTasks.filter((t) => t.article_id).length > 0 && (
                  <div style={{ background: 'var(--color-surface-2)', borderRadius: 6, padding: '0.75rem', marginTop: '0.5rem' }}>
                    <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text)' }}>
                      Wird automatisch hinzugefügt:
                    </p>
                    {planTasks.filter((t) => t.article_id).map((t) => (
                      <div key={t.id} style={{ fontSize: '0.82rem', color: 'var(--color-primary)', marginBottom: '0.2rem' }}>
                        • {t.name}: {t.article_number && <span style={{ fontFamily: 'monospace' }}>{t.article_number}</span>} {t.article_name} × {Number(t.quantity)} {t.unit || 'Stück'}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Termin */}
              <div className="form-group">
                <label>Termin</label>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <button
                    type="button"
                    className={form.apt_mode === 'existing' ? 'btn-primary' : 'btn-secondary'}
                    style={{ fontSize: '0.85rem', padding: '0.3rem 0.75rem' }}
                    onClick={() => setForm({ ...form, apt_mode: 'existing' })}
                  >
                    Vorhandenen wählen
                  </button>
                  <button
                    type="button"
                    className={form.apt_mode === 'new' ? 'btn-primary' : 'btn-secondary'}
                    style={{ fontSize: '0.85rem', padding: '0.3rem 0.75rem' }}
                    onClick={() => setForm({ ...form, apt_mode: 'new' })}
                  >
                    Neuen Termin anlegen
                  </button>
                </div>

                {form.apt_mode === 'existing' && (
                  <select
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
                )}

                {form.apt_mode === 'new' && (
                  <div style={{ padding: '0.75rem', border: '1px solid var(--color-border)', borderRadius: 6 }}>
                    <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                      <label>Titel</label>
                      <input
                        value={form.new_apt_title}
                        onChange={(e) => setForm({ ...form, new_apt_title: e.target.value })}
                        placeholder="Werkstatttermin"
                      />
                    </div>
                    <div className="form-row">
                      <div className="form-group" style={{ flex: 2 }}>
                        <label>Datum *</label>
                        <input
                          type="date"
                          value={form.new_apt_date}
                          onChange={(e) => setForm({ ...form, new_apt_date: e.target.value })}
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label>Von</label>
                        <input
                          type="time"
                          value={form.new_apt_start}
                          onChange={(e) => setForm({ ...form, new_apt_start: e.target.value })}
                        />
                      </div>
                      <div className="form-group">
                        <label>Bis</label>
                        <input
                          type="time"
                          value={form.new_apt_end}
                          onChange={(e) => setForm({ ...form, new_apt_end: e.target.value })}
                        />
                      </div>
                    </div>
                  </div>
                )}
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
              {laborRates.filter((r) => r.is_active).length > 0 && (
                <div className="form-group">
                  <label htmlFor="labor_rate">Stundenpreis (für Arbeitszeit-Posten)</label>
                  <select
                    id="labor_rate"
                    value={form.labor_rate_id}
                    onChange={(e) => setForm({ ...form, labor_rate_id: e.target.value })}
                  >
                    <option value="">– Kein Arbeitszeit-Posten –</option>
                    {laborRates.filter((r) => r.is_active).map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} – {Number(r.rate_per_hour).toFixed(2)} €/Std.
                      </option>
                    ))}
                  </select>
                  {form.labor_rate_id && form.estimated_work_minutes && (
                    <p style={{ margin: '0.3rem 0 0', fontSize: '0.82rem', color: 'var(--color-primary)' }}>
                      → {(parseInt(form.estimated_work_minutes, 10) / 60).toFixed(2)} Std. × {Number(laborRates.find((r) => r.id === form.labor_rate_id)?.rate_per_hour || 0).toFixed(2)} €/Std. = {((parseInt(form.estimated_work_minutes, 10) / 60) * Number(laborRates.find((r) => r.id === form.labor_rate_id)?.rate_per_hour || 0)).toFixed(2)} €
                    </p>
                  )}
                </div>
              )}
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
              <th onClick={() => handleSort('order_number')} style={{ cursor: 'pointer' }}>Auftragsnummer{sortIcon('order_number')}</th>
              <th onClick={() => handleSort('status')} style={{ cursor: 'pointer' }}>Status{sortIcon('status')}</th>
              <th onClick={() => handleSort('customer')} style={{ cursor: 'pointer' }}>Kunde{sortIcon('customer')}</th>
              <th onClick={() => handleSort('vehicle')} style={{ cursor: 'pointer' }}>Fahrzeug{sortIcon('vehicle')}</th>
              <th>Anliegen</th>
              <th onClick={() => handleSort('created_at')} style={{ cursor: 'pointer' }}>Erstellt{sortIcon('created_at')}</th>
            </tr>
          </thead>
          <tbody>
            {displayed.length === 0 ? (
              <tr>
                <td colSpan={6}>Keine Werkstattaufträge vorhanden.</td>
              </tr>
            ) : (
              displayed.map((o) => (
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

            {detailOrder.maintenance_plan_id && (
              <div style={{
                margin: '0.75rem 0 1rem',
                padding: '0.75rem',
                background: 'var(--color-bg-secondary)',
                borderRadius: 6,
                fontSize: '0.9rem',
              }}>
                <strong>Wartungsplan:</strong> {detailOrder.maintenance_plan_name || 'Vorhanden'}
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  style={{ marginLeft: '0.75rem' }}
                  onClick={() => {
                    const token = localStorage.getItem('token')
                    fetch(`/api/v1/maintenance-plans/${detailOrder.maintenance_plan_id}/document`, {
                      headers: token ? { Authorization: `Bearer ${token}` } : {},
                    }).then((r) => {
                      if (!r.ok) { alert('Kein Dokument vorhanden'); return null }
                      return r.blob().then((blob) => ({ blob, disposition: r.headers.get('content-disposition') || '' }))
                    }).then((data) => {
                      if (!data) return
                      const match = data.disposition.match(/filename="?([^"]+)"?/)
                      const filename = match?.[1] || 'wartungsplan.pdf'
                      const a = document.createElement('a')
                      a.href = URL.createObjectURL(data.blob)
                      a.download = filename
                      a.click()
                      URL.revokeObjectURL(a.href)
                    }).catch(() => alert('Download fehlgeschlagen'))
                  }}
                >
                  Dokument öffnen
                </button>
              </div>
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
                  {itemForm.item_type === 'labor' && laborRates.filter((r) => r.is_active).length > 0 && (
                    <div className="form-group" style={{ flex: 1 }}>
                      <label>Stundensatz</label>
                      <select
                        value={itemForm.labor_rate_id}
                        onChange={(e) => {
                          const rate = laborRates.find((r) => r.id === e.target.value)
                          setItemForm({
                            ...itemForm,
                            labor_rate_id: e.target.value,
                            unit_price: rate ? Number(rate.rate_per_hour) : itemForm.unit_price,
                            description: itemForm.description || (rate ? rate.name : ''),
                          })
                        }}
                      >
                        <option value="">– Manuell –</option>
                        {laborRates.filter((r) => r.is_active).map((r) => (
                          <option key={r.id} value={r.id}>{r.name} – {Number(r.rate_per_hour).toFixed(2)} €/Std.</option>
                        ))}
                      </select>
                    </div>
                  )}
                  {itemForm.item_type === 'material' && (
                    <div className="form-group" style={{ flex: 1 }}>
                      <label>Artikel</label>
                      <select
                        value={itemForm.article_id}
                        onChange={(e) => {
                          const a = articles.find((x) => x.id === e.target.value)
                          const newForm = {
                            ...itemForm,
                            article_id: e.target.value,
                            description: a ? a.name : itemForm.description,
                            unit_price: a ? Number(a.sales_price_b2c) : itemForm.unit_price,
                          }
                          setItemForm(newForm)
                          if (a && a.stock_quantity < newForm.quantity) {
                            setStockWarning(`Nicht genug verfügbarer Bestand. Verfügbar: ${a.stock_quantity} Stück`)
                          } else {
                            setStockWarning('')
                          }
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
                      onChange={(e) => {
                        const qty = parseFloat(e.target.value) || 1
                        setItemForm({ ...itemForm, quantity: qty })
                        if (itemForm.item_type === 'material' && itemForm.article_id) {
                          const a = articles.find((x) => x.id === itemForm.article_id)
                          if (a && a.stock_quantity < qty) {
                            setStockWarning(`Nicht genug verfügbarer Bestand. Verfügbar: ${a.stock_quantity} Stück`)
                          } else {
                            setStockWarning('')
                          }
                        }
                      }}
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
                {stockWarning && (
                  <p style={{ color: 'var(--color-warning, #d97706)', margin: '0.5rem 0 0', fontSize: '0.9rem' }}>
                    ⚠ {stockWarning}
                  </p>
                )}
                {itemError && <p className="error">{itemError}</p>}
                <div className="form-actions">
                  <button type="button" onClick={() => { setShowItemForm(false); setStockWarning('') }} className="btn-secondary">Abbrechen</button>
                  <button type="submit" disabled={itemSubmitting} className="btn-primary">{itemSubmitting ? 'Speichern...' : 'Hinzufügen'}</button>
                </div>
              </form>
            )}

            <OrderPhotos orderId={detailOrder.id} />

            <div className="form-actions" style={{ marginTop: '1.5rem' }}>
              <button type="button" onClick={openPdfPreview} className="btn-secondary">
                Auftrag drucken / Vorschau
              </button>
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

      {pdfPreviewUrl && (
        <PreviewModal
          title={detailOrder ? `Auftrag ${detailOrder.order_number}` : 'Werkstattauftrag'}
          url={pdfPreviewUrl}
          type="pdf"
          onClose={closePdfPreview}
        />
      )}
    </div>
  )
}
