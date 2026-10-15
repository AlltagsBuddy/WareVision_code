import { useEffect, useRef, useState } from 'react'
import { customersApi, vehiclesApi } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import { hasRight } from '../utils/permissions'

export default function Customers() {
  const { user } = useAuth()
  const [customers, setCustomers] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const PAGE_SIZE = 50
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [editingAddressId, setEditingAddressId] = useState<string | null>(null)

  const emptyForm = {
    customer_type: 'B2C',
    company_name: '',
    salutation: '',
    first_name: '',
    last_name: '',
    contact_position: '',
    email: '',
    phone: '',
    vat_id: '',
    notes: '',
    street: '',
    house_number: '',
    postal_code: '',
    city: '',
    country: 'Deutschland',
  }

  const [form, setForm] = useState(emptyForm)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null)
  const [detailCustomer, setDetailCustomer] = useState<any | null>(null)
  const [addresses, setAddresses] = useState<any[]>([])
  const [detailVehicles, setDetailVehicles] = useState<any[]>([])
  const [showAddressForm, setShowAddressForm] = useState(false)

  // Bestaetigungs-Modal (ersetzt confirm())
  const [confirmModal, setConfirmModal] = useState<{ message: string; onConfirm: () => void } | null>(null)
  const [actionError, setActionError] = useState('')

  // DSGVO-Einwilligungs-Modal
  const [dsgvoCustomer, setDsgvoCustomer] = useState<any | null>(null)
  const [dsgvoPdfUrl, setDsgvoPdfUrl] = useState<string | null>(null)
  const [dsgvoMode, setDsgvoMode] = useState<'preview' | 'sign'>('preview')
  const [dsgvoSigning, setDsgvoSigning] = useState(false)
  const [dsgvoSuccess, setDsgvoSuccess] = useState('')
  const [dsgvoError, setDsgvoError] = useState('')
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const isDrawingRef = useRef(false)
  const [addressForm, setAddressForm] = useState({
    address_type: 'main' as string,
    street: '',
    house_number: '',
    postal_code: '',
    city: '',
    country: 'Deutschland',
  })

  useEffect(() => {
    setLoading(true)
    customersApi
      .list({ search: search || undefined, include_inactive: includeInactive, limit: PAGE_SIZE, skip: 0 })
      .then((data) => {
        setCustomers(data)
        setHasMore(data.length === PAGE_SIZE)
      })
      .finally(() => setLoading(false))
  }, [search, includeInactive])

  const handleLoadMore = async () => {
    setLoadingMore(true)
    try {
      const more = await customersApi.list({
        search: search || undefined,
        include_inactive: includeInactive,
        limit: PAGE_SIZE,
        skip: customers.length,
      })
      setCustomers((prev) => [...prev, ...more])
      setHasMore(more.length === PAGE_SIZE)
    } finally {
      setLoadingMore(false)
    }
  }

  const resetForm = () => {
    setForm(emptyForm)
    setEditing(null)
    setEditingAddressId(null)
    setError('')
    setDuplicateWarning(null)
  }

  const buildCustomerPayload = (): Record<string, unknown> => {
    const base: Record<string, unknown> = {
      customer_type: form.customer_type,
      salutation: form.salutation || undefined,
      email: form.email.trim() || undefined,
      phone: form.phone.trim() || undefined,
      notes: form.notes.trim() || undefined,
    }
    if (form.customer_type === 'B2C') {
      return {
        ...base,
        first_name: form.first_name.trim() || undefined,
        last_name: form.last_name.trim() || undefined,
        company_name: null,
        vat_id: null,
        contact_position: null,
      }
    }
    return {
      ...base,
      company_name: form.company_name.trim(),
      first_name: form.first_name.trim() || undefined,
      last_name: form.last_name.trim() || undefined,
      contact_position: form.contact_position.trim() || undefined,
      vat_id: form.vat_id.trim() || undefined,
    }
  }

  const hasAddress = () => form.street.trim() && form.postal_code.trim() && form.city.trim()

  const saveAddress = async (customerId: string) => {
    if (!hasAddress()) return
    if (editingAddressId) {
      await customersApi.deleteAddress(customerId, editingAddressId)
    }
    await customersApi.addAddress(customerId, {
      address_type: 'main',
      street: form.street.trim(),
      house_number: form.house_number.trim() || undefined,
      postal_code: form.postal_code.trim(),
      city: form.city.trim(),
      country: form.country.trim() || 'Deutschland',
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setDuplicateWarning(null)
    if (form.customer_type === 'B2B' && !form.company_name.trim()) {
      setError('Fuer Geschaeftskunden ist der Firmenname erforderlich.')
      return
    }
    if (form.customer_type === 'B2B' && !form.last_name.trim()) {
      setError('Bitte einen Ansprechpartner (Nachname) hinterlegen.')
      return
    }
    const data = buildCustomerPayload()
    setSubmitting(true)
    try {
      let customerId: string
      if (editing) {
        await customersApi.update(editing.id, data)
        customerId = editing.id
        setCustomers((prev) => prev.map((c) => (c.id === editing.id ? { ...c, ...data } : c)))
      } else {
        const created: any = await customersApi.create(data)
        customerId = created.id
        const updated = await customersApi.list({ search: search || undefined, include_inactive: includeInactive })
        setCustomers(updated)
      }
      await saveAddress(customerId)
      setShowForm(false)
      resetForm()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Fehler'
      if (msg.includes('existiert bereits')) {
        setDuplicateWarning(msg)
      } else {
        setError(msg)
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = (c: any) => {
    setConfirmModal({
      message: `Kunde "${getName(c)}" wirklich deaktivieren?`,
      onConfirm: async () => {
        setConfirmModal(null)
        try {
          await customersApi.delete(c.id)
          setCustomers((prev) =>
            includeInactive
              ? prev.map((x) => (x.id === c.id ? { ...x, is_active: false } : x))
              : prev.filter((x) => x.id !== c.id)
          )
        } catch (err) {
          setActionError(err instanceof Error ? err.message : 'Fehler beim Deaktivieren')
        }
      },
    })
  }

  const handleDsgvoDelete = (c: any) => {
    setConfirmModal({
      message: `DSGVO-Loeschung fuer "${getName(c)}"?\n\nHat der Kunde Rechnungen oder Auftraege, werden seine Daten anonymisiert (GoBD). Andernfalls wird er vollstaendig geloescht. Diese Aktion kann nicht rueckgaengig gemacht werden.`,
      onConfirm: async () => {
        setConfirmModal(null)
        try {
          const res = await customersApi.dsgvoDelete(c.id)
          if (res.action === 'deleted') {
            setCustomers((prev) => prev.filter((x) => x.id !== c.id))
            if (detailCustomer?.id === c.id) closeDetail()
          } else {
            setCustomers((prev) =>
              prev.map((x) =>
                x.id === c.id
                  ? { ...x, company_name: '[Anonymisiert]', first_name: '[Anonymisiert]', last_name: '[Anonymisiert]', email: '[Anonymisiert]', is_active: false }
                  : x
              )
            )
            if (detailCustomer?.id === c.id) closeDetail()
          }
        } catch (err) {
          setActionError(err instanceof Error ? err.message : 'DSGVO-Loeschung fehlgeschlagen')
        }
      },
    })
  }

  const handleExport = async (c: any) => {
    try {
      const data = await customersApi.exportData(c.id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Kunde_${c.id}_Export.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Export fehlgeschlagen')
    }
  }

  const openDetail = async (c: any) => {
    setDetailCustomer(c)
    setShowAddressForm(false)
    Promise.all([customersApi.getAddresses(c.id), vehiclesApi.list({ customer_id: c.id })]).then(([addrs, vehs]) => {
      setAddresses(addrs)
      setDetailVehicles(vehs)
    })
  }

  const closeDetail = () => setDetailCustomer(null)

  const handleAddAddress = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detailCustomer || !addressForm.street.trim() || !addressForm.postal_code.trim() || !addressForm.city.trim()) return
    try {
      await customersApi.addAddress(detailCustomer.id, {
        address_type: addressForm.address_type,
        street: addressForm.street.trim(),
        house_number: addressForm.house_number || undefined,
        postal_code: addressForm.postal_code.trim(),
        city: addressForm.city.trim(),
        country: addressForm.country || 'Deutschland',
      })
      const updated = await customersApi.getAddresses(detailCustomer.id)
      setAddresses(updated)
      setShowAddressForm(false)
      setAddressForm({ address_type: 'main', street: '', house_number: '', postal_code: '', city: '', country: 'Deutschland' })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleDeleteAddress = (addressId: string) => {
    if (!detailCustomer) return
    setConfirmModal({
      message: 'Adresse wirklich entfernen?',
      onConfirm: async () => {
        setConfirmModal(null)
        try {
          await customersApi.deleteAddress(detailCustomer.id, addressId)
          setAddresses((prev) => prev.filter((a) => a.id !== addressId))
        } catch (err) {
          setActionError(err instanceof Error ? err.message : 'Fehler beim Entfernen der Adresse')
        }
      },
    })
  }

  const openEdit = async (c: any) => {
    setEditing(c)
    const base = {
      customer_type: c.customer_type,
      company_name: c.company_name || '',
      salutation: c.salutation || '',
      first_name: c.first_name || '',
      last_name: c.last_name || '',
      contact_position: c.contact_position || '',
      email: c.email || '',
      phone: c.phone || '',
      vat_id: c.vat_id || '',
      notes: c.notes || '',
      street: '',
      house_number: '',
      postal_code: '',
      city: '',
      country: 'Deutschland',
    }
    try {
      const addrs: any[] = await customersApi.getAddresses(c.id)
      const main = addrs.find((a) => a.address_type === 'main') || addrs[0]
      if (main) {
        base.street = main.street || ''
        base.house_number = main.house_number || ''
        base.postal_code = main.postal_code || ''
        base.city = main.city || ''
        base.country = main.country || 'Deutschland'
        setEditingAddressId(main.id)
      }
    } catch {
      // Adresse nicht laden – kein Fehler
    }
    setForm(base)
    setShowForm(true)
  }

  const openDsgvoModal = async (c: any) => {
    setDsgvoCustomer(c)
    setDsgvoMode('preview')
    setDsgvoSuccess('')
    setDsgvoError('')
    try {
      const blob = await customersApi.getDsgvoConsentPdf(c.id)
      setDsgvoPdfUrl(URL.createObjectURL(blob))
    } catch {
      setDsgvoError('PDF konnte nicht geladen werden.')
    }
  }

  const closeDsgvoModal = () => {
    if (dsgvoPdfUrl) URL.revokeObjectURL(dsgvoPdfUrl)
    setDsgvoCustomer(null)
    setDsgvoPdfUrl(null)
    setDsgvoMode('preview')
    setDsgvoSuccess('')
    setDsgvoError('')
  }

  const clearCanvas = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (ctx) { ctx.clearRect(0, 0, canvas.width, canvas.height) }
  }

  const getCanvasPos = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return { x: 0, y: 0 }
    const rect = canvas.getBoundingClientRect()
    if ('touches' in e) {
      return { x: e.touches[0].clientX - rect.left, y: e.touches[0].clientY - rect.top }
    }
    return { x: (e as React.MouseEvent).clientX - rect.left, y: (e as React.MouseEvent).clientY - rect.top }
  }

  const handleCanvasStart = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    isDrawingRef.current = true
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const { x, y } = getCanvasPos(e)
    ctx.beginPath()
    ctx.moveTo(x, y)
  }

  const handleCanvasMove = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    if (!isDrawingRef.current) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const { x, y } = getCanvasPos(e)
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.strokeStyle = '#000'
    ctx.lineTo(x, y)
    ctx.stroke()
  }

  const handleCanvasEnd = () => { isDrawingRef.current = false }

  const handleDsgvoSign = async () => {
    if (!dsgvoCustomer || !canvasRef.current) return
    const canvas = canvasRef.current
    // Leere Unterschrift pruefen
    const ctx = canvas.getContext('2d')
    const imageData = ctx?.getImageData(0, 0, canvas.width, canvas.height)
    const hasSignature = imageData ? Array.from(imageData.data).some((v, i) => i % 4 === 3 && v > 0) : false
    if (!hasSignature) {
      setDsgvoError('Bitte zuerst unterschreiben.')
      return
    }
    setDsgvoSigning(true)
    setDsgvoError('')
    try {
      const dataUrl = canvas.toDataURL('image/png')
      await customersApi.signDsgvoConsent(dsgvoCustomer.id, dataUrl)
      setDsgvoSuccess('Einwilligung wurde unterschrieben und bei den Kundendokumenten gespeichert.')
      setDsgvoMode('preview')
    } catch (err) {
      setDsgvoError(err instanceof Error ? err.message : 'Fehler beim Speichern')
    } finally {
      setDsgvoSigning(false)
    }
  }

  const getName = (c: any) =>
    c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email || '-'

  const customerTypeLabel = (t: string) => (t === 'B2B' ? 'Gewerbe' : 'Privat')

  const ADDRESS_TYPE_LABELS: Record<string, string> = {
    main: 'Hauptadresse',
    billing: 'Rechnungsadresse',
    shipping: 'Lieferadresse',
  }

  return (
    <div className="page">
      <h1>Kunden</h1>

      {actionError && (
        <div className="error" style={{ marginBottom: '1rem' }}>
          {actionError}
          <button type="button" onClick={() => setActionError('')} style={{ marginLeft: '1rem', cursor: 'pointer', background: 'none', border: 'none', color: 'inherit', fontWeight: 700 }}>
            ✕
          </button>
        </div>
      )}

      <div className="toolbar">
        <input
          type="search"
          placeholder="Suchen..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', whiteSpace: 'nowrap' }}>
          <input type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} />
          Deaktivierte anzeigen
        </label>
        <button type="button" onClick={() => { resetForm(); setShowForm(true) }} className="btn-primary">
          + Neuer Kunde
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => { setShowForm(false); resetForm() }}>
          <div className="modal" style={{ maxWidth: 560 }} onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? 'Kunde bearbeiten' : 'Neuer Kunde'}</h2>

            {/* Typ-Auswahl */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
              {(['B2C', 'B2B'] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setForm({ ...form, customer_type: type })}
                  style={{
                    flex: 1,
                    padding: '0.5rem',
                    border: `2px solid ${form.customer_type === type ? 'var(--color-primary)' : 'var(--color-border)'}`,
                    borderRadius: 6,
                    background: form.customer_type === type ? 'var(--color-primary)' : 'transparent',
                    color: form.customer_type === type ? '#fff' : 'var(--color-text)',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontSize: '0.95rem',
                  }}
                >
                  {type === 'B2C' ? 'Privatkunde' : 'Unternehmen'}
                </button>
              ))}
            </div>

            <form onSubmit={handleSubmit}>

              {/* ---- B2B: Firmendaten ---- */}
              {form.customer_type === 'B2B' && (
                <>
                  <div className="form-row">
                    <div className="form-group" style={{ flex: 2 }}>
                      <label>Firmenname *</label>
                      <input
                        value={form.company_name}
                        onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                        placeholder="Muster GmbH"
                        required
                      />
                    </div>
                    <div className="form-group" style={{ flex: 1 }}>
                      <label>USt-IdNr.</label>
                      <input
                        value={form.vat_id}
                        onChange={(e) => setForm({ ...form, vat_id: e.target.value })}
                        placeholder="DE123456789"
                      />
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>E-Mail</label>
                      <input
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                        placeholder="info@firma.de"
                      />
                    </div>
                    <div className="form-group">
                      <label>Telefon</label>
                      <input
                        value={form.phone}
                        onChange={(e) => setForm({ ...form, phone: e.target.value })}
                        placeholder="+49 123 456789"
                      />
                    </div>
                  </div>
                </>
              )}

              {/* ---- B2C: Persondaten ---- */}
              {form.customer_type === 'B2C' && (
                <div className="form-row">
                  <div className="form-group" style={{ maxWidth: 110 }}>
                    <label>Anrede</label>
                    <select value={form.salutation} onChange={(e) => setForm({ ...form, salutation: e.target.value })}>
                      <option value="">-</option>
                      <option value="Herr">Herr</option>
                      <option value="Frau">Frau</option>
                      <option value="Divers">Divers</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Vorname</label>
                    <input
                      value={form.first_name}
                      onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                      placeholder="Vorname"
                    />
                  </div>
                  <div className="form-group">
                    <label>Nachname</label>
                    <input
                      value={form.last_name}
                      onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                      placeholder="Nachname"
                    />
                  </div>
                </div>
              )}

              {/* ---- B2C: Kontakt ---- */}
              {form.customer_type === 'B2C' && (
                <div className="form-row">
                  <div className="form-group">
                    <label>E-Mail</label>
                    <input
                      type="email"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      placeholder="email@beispiel.de"
                    />
                  </div>
                  <div className="form-group">
                    <label>Telefon</label>
                    <input
                      value={form.phone}
                      onChange={(e) => setForm({ ...form, phone: e.target.value })}
                      placeholder="+49 123 456789"
                    />
                  </div>
                </div>
              )}

              {/* ---- Adresse (beide Typen) ---- */}
              <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem', marginTop: '0.25rem', marginBottom: '0.75rem' }}>
                <div style={{ fontWeight: 600, fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
                  Adresse
                </div>
                <div className="form-row">
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Strasse</label>
                    <input
                      value={form.street}
                      onChange={(e) => setForm({ ...form, street: e.target.value })}
                      placeholder="Musterstrasse"
                    />
                  </div>
                  <div className="form-group" style={{ maxWidth: 80 }}>
                    <label>Nr.</label>
                    <input
                      value={form.house_number}
                      onChange={(e) => setForm({ ...form, house_number: e.target.value })}
                      placeholder="12a"
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group" style={{ maxWidth: 110 }}>
                    <label>PLZ</label>
                    <input
                      value={form.postal_code}
                      onChange={(e) => setForm({ ...form, postal_code: e.target.value })}
                      placeholder="90402"
                    />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Ort</label>
                    <input
                      value={form.city}
                      onChange={(e) => setForm({ ...form, city: e.target.value })}
                      placeholder="Nuernberg"
                    />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Land</label>
                    <input
                      value={form.country}
                      onChange={(e) => setForm({ ...form, country: e.target.value })}
                      placeholder="Deutschland"
                    />
                  </div>
                </div>
              </div>

              {/* ---- B2B: Ansprechpartner ---- */}
              {form.customer_type === 'B2B' && (
                <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem', marginBottom: '0.75rem' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
                    Ansprechpartner *
                  </div>
                  <div className="form-row">
                    <div className="form-group" style={{ maxWidth: 110 }}>
                      <label>Anrede</label>
                      <select value={form.salutation} onChange={(e) => setForm({ ...form, salutation: e.target.value })}>
                        <option value="">-</option>
                        <option value="Herr">Herr</option>
                        <option value="Frau">Frau</option>
                        <option value="Divers">Divers</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Vorname</label>
                      <input
                        value={form.first_name}
                        onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                        placeholder="Vorname"
                      />
                    </div>
                    <div className="form-group">
                      <label>Nachname *</label>
                      <input
                        value={form.last_name}
                        onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                        placeholder="Nachname"
                        required
                      />
                    </div>
                  </div>
                  <div className="form-group">
                    <label>Position / Funktion</label>
                    <input
                      value={form.contact_position}
                      onChange={(e) => setForm({ ...form, contact_position: e.target.value })}
                      placeholder="z.B. Geschaeftsfuehrer, Einkauf"
                    />
                  </div>
                </div>
              )}

              <div className="form-group">
                <label>Notizen</label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  rows={2}
                />
              </div>

              {duplicateWarning && <p className="error">{duplicateWarning}</p>}
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => { setShowForm(false); resetForm() }} className="btn-secondary">
                  Abbrechen
                </button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Speichern...' : editing ? 'Speichern' : 'Anlegen'}
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
                <th>Name / Ansprechpartner</th>
                <th>E-Mail</th>
                <th>Telefon</th>
                <th>Typ</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.id} className={!c.is_active ? 'inactive' : ''}>
                  <td>
                    <div>
                      {getName(c)}
                      {!c.is_active && (
                        <span className="badge" style={{ marginLeft: '0.5rem', fontSize: '0.75rem' }}>
                          inaktiv
                        </span>
                      )}
                    </div>
                    {c.customer_type === 'B2B' && (c.first_name || c.last_name) && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
                        AP: {[c.salutation, c.first_name, c.last_name].filter(Boolean).join(' ')}
                        {c.contact_position && ` (${c.contact_position})`}
                      </div>
                    )}
                  </td>
                  <td>{c.email || '-'}</td>
                  <td>{c.phone || '-'}</td>
                  <td>{customerTypeLabel(c.customer_type)}</td>
                  <td>
                    <button type="button" onClick={() => openDetail(c)} className="btn-secondary btn-sm">
                      Detail
                    </button>
                    <button type="button" onClick={() => openEdit(c)} className="btn-secondary btn-sm">
                      Bearbeiten
                    </button>
                    {hasRight(user, 'dsgvo_export') && (
                      <button type="button" onClick={() => handleExport(c)} className="btn-secondary btn-sm">
                        Export
                      </button>
                    )}
                    {hasRight(user, 'dsgvo_delete') && (
                      <button type="button" onClick={() => handleDsgvoDelete(c)} className="btn-secondary btn-sm">
                        DSGVO: Löschen
                      </button>
                    )}
                    {c.is_active && (
                      <button type="button" onClick={() => handleDelete(c)} className="btn-secondary btn-sm">
                        Deaktivieren
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {hasMore && (
            <div style={{ textAlign: 'center', marginTop: '1rem' }}>
              <button type="button" onClick={handleLoadMore} disabled={loadingMore} className="btn-secondary">
                {loadingMore ? 'Laden...' : `Weitere laden (${customers.length} geladen)`}
              </button>
            </div>
          )}
        </div>
      )}

      {detailCustomer && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>Kundendetail - {getName(detailCustomer)}</h2>

            {detailCustomer.customer_type === 'B2B' && (detailCustomer.first_name || detailCustomer.last_name) && (
              <p style={{ marginBottom: '0.25rem' }}>
                <strong>Ansprechpartner:</strong>{' '}
                {[detailCustomer.salutation, detailCustomer.first_name, detailCustomer.last_name].filter(Boolean).join(' ')}
                {detailCustomer.contact_position && (
                  <span style={{ color: 'var(--color-text-muted)' }}> - {detailCustomer.contact_position}</span>
                )}
              </p>
            )}
            {detailCustomer.customer_type === 'B2C' && detailCustomer.salutation && (
              <p style={{ marginBottom: '0.25rem', color: 'var(--color-text-muted)' }}>{detailCustomer.salutation}</p>
            )}
            <p style={{ marginBottom: '0.75rem' }}>
              {detailCustomer.email || '-'} | {detailCustomer.phone || '-'}
            </p>

            <h3>Fahrzeuge</h3>
            {detailVehicles.length === 0 ? (
              <p>Keine Fahrzeuge.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, marginBottom: '1rem' }}>
                {detailVehicles.map((v) => (
                  <li key={v.id} style={{ marginBottom: '0.25rem' }}>
                    {v.license_plate || v.vin || 'Fahrzeug'} {v.build_year ? `(${v.build_year})` : ''} -{' '}
                    {v.category === 'quad' ? 'Quad' : 'Motorrad'}
                  </li>
                ))}
              </ul>
            )}

            <h3>Adressen</h3>
            {addresses.length === 0 ? (
              <p>Keine Adressen hinterlegt.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {addresses.map((a) => (
                  <li
                    key={a.id}
                    style={{
                      marginBottom: '0.75rem',
                      padding: '0.5rem 0.75rem',
                      border: '1px solid var(--color-border)',
                      borderRadius: 6,
                    }}
                  >
                    <strong>{ADDRESS_TYPE_LABELS[a.address_type] || a.address_type}</strong>
                    <div>
                      {a.street}
                      {a.house_number ? ` ${a.house_number}` : ''}, {a.postal_code} {a.city}
                    </div>
                    {a.country && a.country !== 'Deutschland' && <div>{a.country}</div>}
                    <button
                      type="button"
                      onClick={() => handleDeleteAddress(a.id)}
                      className="btn-secondary btn-sm"
                      style={{ marginTop: 4 }}
                    >
                      Entfernen
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {!showAddressForm ? (
              <button
                type="button"
                onClick={() => setShowAddressForm(true)}
                className="btn-primary"
                style={{ marginTop: '0.5rem' }}
              >
                + Weitere Adresse
              </button>
            ) : (
              <form
                onSubmit={handleAddAddress}
                style={{ marginTop: '1rem', padding: '1rem', border: '1px solid var(--color-border)', borderRadius: 8 }}
              >
                <h4 style={{ marginTop: 0 }}>Neue Adresse</h4>
                <div className="form-group">
                  <label>Typ</label>
                  <select
                    value={addressForm.address_type}
                    onChange={(e) => setAddressForm({ ...addressForm, address_type: e.target.value })}
                  >
                    <option value="main">Hauptadresse</option>
                    <option value="billing">Rechnungsadresse</option>
                    <option value="shipping">Lieferadresse</option>
                  </select>
                </div>
                <div className="form-row">
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Strasse *</label>
                    <input
                      value={addressForm.street}
                      onChange={(e) => setAddressForm({ ...addressForm, street: e.target.value })}
                      required
                      placeholder="Musterstrasse"
                    />
                  </div>
                  <div className="form-group" style={{ maxWidth: 80 }}>
                    <label>Nr.</label>
                    <input
                      value={addressForm.house_number}
                      onChange={(e) => setAddressForm({ ...addressForm, house_number: e.target.value })}
                      placeholder="1a"
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>PLZ *</label>
                    <input
                      value={addressForm.postal_code}
                      onChange={(e) => setAddressForm({ ...addressForm, postal_code: e.target.value })}
                      required
                      placeholder="90402"
                    />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Ort *</label>
                    <input
                      value={addressForm.city}
                      onChange={(e) => setAddressForm({ ...addressForm, city: e.target.value })}
                      required
                      placeholder="Nuernberg"
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label>Land</label>
                  <input
                    value={addressForm.country}
                    onChange={(e) => setAddressForm({ ...addressForm, country: e.target.value })}
                    placeholder="Deutschland"
                  />
                </div>
                <div className="form-actions">
                  <button type="button" onClick={() => setShowAddressForm(false)} className="btn-secondary">
                    Abbrechen
                  </button>
                  <button type="submit" className="btn-primary">
                    Hinzufuegen
                  </button>
                </div>
              </form>
            )}

            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button
                type="button"
                onClick={() => { closeDetail(); openDsgvoModal(detailCustomer) }}
                className="btn-secondary"
              >
                Datenschutz-Einwilligung
              </button>
              <button type="button" onClick={closeDetail} className="btn-secondary">
                Schliessen
              </button>
            </div>
          </div>
        </div>
      )}
      {dsgvoCustomer && (
        <div className="modal-overlay" onClick={closeDsgvoModal}>
          <div
            className="modal"
            style={{ maxWidth: 760, width: '95vw' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2>Datenschutz-Einwilligung</h2>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '1rem', fontSize: '0.9rem' }}>
              {getName(dsgvoCustomer)} &mdash; gem. DSGVO Art. 6 / Art. 7
            </p>

            {dsgvoSuccess && (
              <div style={{ padding: '0.75rem 1rem', background: 'var(--color-bg-secondary)', border: '1px solid var(--color-border)', borderRadius: 6, marginBottom: '1rem', color: 'var(--color-success, #16a34a)' }}>
                {dsgvoSuccess}
              </div>
            )}
            {dsgvoError && <p className="error">{dsgvoError}</p>}

            {/* Modus-Tabs */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              <button
                type="button"
                className={dsgvoMode === 'preview' ? 'btn-primary' : 'btn-secondary'}
                onClick={() => setDsgvoMode('preview')}
              >
                Vorschau / Drucken
              </button>
              <button
                type="button"
                className={dsgvoMode === 'sign' ? 'btn-primary' : 'btn-secondary'}
                onClick={() => { setDsgvoMode('sign'); setDsgvoError('') }}
              >
                Digital unterschreiben
              </button>
            </div>

            {dsgvoMode === 'preview' && (
              <>
                {dsgvoPdfUrl ? (
                  <iframe
                    src={dsgvoPdfUrl}
                    title="DSGVO-Einwilligung Vorschau"
                    style={{ width: '100%', height: 480, border: '1px solid var(--color-border)', borderRadius: 6 }}
                  />
                ) : (
                  <p>PDF wird geladen...</p>
                )}
                <div className="form-actions" style={{ marginTop: '1rem' }}>
                  {dsgvoPdfUrl && (
                    <a
                      href={dsgvoPdfUrl}
                      download={`DSGVO_Einwilligung_${getName(dsgvoCustomer)}.pdf`}
                      className="btn-secondary"
                    >
                      PDF herunterladen (drucken &amp; unterschreiben)
                    </a>
                  )}
                  <button type="button" onClick={closeDsgvoModal} className="btn-secondary">
                    Schliessen
                  </button>
                </div>
              </>
            )}

            {dsgvoMode === 'sign' && (
              <>
                <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
                  Bitte mit Maus oder Finger unterschreiben:
                </p>
                <div style={{ border: '2px solid var(--color-border)', borderRadius: 6, background: '#fff', display: 'inline-block', touchAction: 'none' }}>
                  <canvas
                    ref={canvasRef}
                    width={680}
                    height={140}
                    style={{ display: 'block', cursor: 'crosshair', maxWidth: '100%' }}
                    onMouseDown={handleCanvasStart}
                    onMouseMove={handleCanvasMove}
                    onMouseUp={handleCanvasEnd}
                    onMouseLeave={handleCanvasEnd}
                    onTouchStart={handleCanvasStart}
                    onTouchMove={handleCanvasMove}
                    onTouchEnd={handleCanvasEnd}
                  />
                </div>
                <div className="form-actions" style={{ marginTop: '1rem' }}>
                  <button type="button" onClick={clearCanvas} className="btn-secondary">
                    Unterschrift loeschen
                  </button>
                  <button
                    type="button"
                    onClick={handleDsgvoSign}
                    disabled={dsgvoSigning}
                    className="btn-primary"
                  >
                    {dsgvoSigning ? 'Wird gespeichert...' : 'Unterschrift bestaetigen &amp; speichern'}
                  </button>
                  <button type="button" onClick={closeDsgvoModal} className="btn-secondary">
                    Abbrechen
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {confirmModal && (
        <div className="modal-overlay" onClick={() => setConfirmModal(null)}>
          <div className="modal" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0 }}>Bestaetigung erforderlich</h3>
            <p style={{ whiteSpace: 'pre-wrap' }}>{confirmModal.message}</p>
            <div className="form-actions">
              <button type="button" onClick={() => setConfirmModal(null)} className="btn-secondary">
                Abbrechen
              </button>
              <button type="button" onClick={confirmModal.onConfirm} className="btn-primary">
                Bestaetigen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
