import { useEffect, useState } from 'react'
import { customersApi, vehiclesApi } from '../api/client'
import { useAuth } from '../hooks/useAuth'

export default function Customers() {
  const { user } = useAuth()
  const [customers, setCustomers] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form, setForm] = useState({
    customer_type: 'B2C',
    company_name: '',
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    vat_id: '',
    notes: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null)
  const [detailCustomer, setDetailCustomer] = useState<any | null>(null)
  const [addresses, setAddresses] = useState<any[]>([])
  const [detailVehicles, setDetailVehicles] = useState<any[]>([])
  const [showAddressForm, setShowAddressForm] = useState(false)
  const [addressForm, setAddressForm] = useState({
    address_type: 'main' as string,
    street: '',
    house_number: '',
    postal_code: '',
    city: '',
    country: 'Deutschland',
  })

  useEffect(() => {
    customersApi.list({ search: search || undefined }).then(setCustomers).finally(() => setLoading(false))
  }, [search])

  const resetForm = () => {
    setForm({
      customer_type: 'B2C',
      company_name: '',
      first_name: '',
      last_name: '',
      email: '',
      phone: '',
      vat_id: '',
      notes: '',
    })
    setEditing(null)
    setError('')
    setDuplicateWarning(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setDuplicateWarning(null)
    const data = {
      customer_type: form.customer_type,
      company_name: form.company_name || undefined,
      first_name: form.first_name || undefined,
      last_name: form.last_name || undefined,
      email: form.email || undefined,
      phone: form.phone || undefined,
      vat_id: form.vat_id || undefined,
      notes: form.notes || undefined,
    }
    setSubmitting(true)
    try {
      if (editing) {
        await customersApi.update(editing.id, data)
        setCustomers((prev) => prev.map((c) => (c.id === editing.id ? { ...c, ...data } : c)))
      } else {
        await customersApi.create(data)
        const updated = await customersApi.list({ search: search || undefined })
        setCustomers(updated)
      }
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

  const handleDelete = async (c: any) => {
    if (!confirm(`Kunde "${c.company_name || `${c.first_name} ${c.last_name}`.trim()}" wirklich deaktivieren?`)) return
    try {
      await customersApi.delete(c.id)
      setCustomers((prev) => prev.filter((x) => x.id !== c.id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleDsgvoDelete = async (c: any) => {
    if (!confirm(`DSGVO-Löschung für "${getName(c)}"? Bei Rechnungen/Aufträgen wird anonymisiert, sonst endgültig gelöscht.`)) return
    try {
      const res = await customersApi.dsgvoDelete(c.id)
      if (res.action === 'deleted') {
        setCustomers((prev) => prev.filter((x) => x.id !== c.id))
        if (detailCustomer?.id === c.id) closeDetail()
      } else {
        setCustomers((prev) => prev.map((x) => (x.id === c.id ? { ...x, company_name: '[Anonymisiert]', first_name: '[Anonymisiert]', last_name: '[Anonymisiert]', email: '[Anonymisiert]', is_active: false } : x)))
        if (detailCustomer?.id === c.id) closeDetail()
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
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
      alert(err instanceof Error ? err.message : 'Export fehlgeschlagen')
    }
  }

  const openDetail = async (c: any) => {
    setDetailCustomer(c)
    setShowAddressForm(false)
    Promise.all([
      customersApi.getAddresses(c.id),
      vehiclesApi.list({ customer_id: c.id }),
    ]).then(([addrs, vehs]) => {
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

  const handleDeleteAddress = async (addressId: string) => {
    if (!detailCustomer || !confirm('Adresse wirklich entfernen?')) return
    try {
      await customersApi.deleteAddress(detailCustomer.id, addressId)
      setAddresses((prev) => prev.filter((a) => a.id !== addressId))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const openEdit = (c: any) => {
    setEditing(c)
    setForm({
      customer_type: c.customer_type,
      company_name: c.company_name || '',
      first_name: c.first_name || '',
      last_name: c.last_name || '',
      email: c.email || '',
      phone: c.phone || '',
      vat_id: c.vat_id || '',
      notes: c.notes || '',
    })
    setShowForm(true)
  }

  const getName = (c: any) => c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email || '–'

  const ADDRESS_TYPE_LABELS: Record<string, string> = { main: 'Hauptadresse', billing: 'Rechnungsadresse', shipping: 'Lieferadresse' }

  return (
    <div className="page">
      <h1>Kunden</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Suchen..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="button" onClick={() => { resetForm(); setShowForm(true) }} className="btn-primary">
          + Neuer Kunde
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => { setShowForm(false); resetForm() }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? 'Kunde bearbeiten' : 'Neuer Kunde'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Typ *</label>
                <select
                  value={form.customer_type}
                  onChange={(e) => setForm({ ...form, customer_type: e.target.value })}
                  required
                >
                  <option value="B2C">Privat (B2C)</option>
                  <option value="B2B">Geschäftlich (B2B)</option>
                </select>
              </div>
              {form.customer_type === 'B2B' && (
                <div className="form-group">
                  <label>Firmenname</label>
                  <input
                    value={form.company_name}
                    onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                    placeholder="Firmenname"
                  />
                </div>
              )}
              <div className="form-row">
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
              <div className="form-group">
                <label>USt-IdNr.</label>
                <input
                  value={form.vat_id}
                  onChange={(e) => setForm({ ...form, vat_id: e.target.value })}
                  placeholder="DE123456789"
                />
              </div>
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
                <button type="button" onClick={() => { setShowForm(false); resetForm() }} className="btn-secondary">Abbrechen</button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Speichern...' : (editing ? 'Speichern' : 'Anlegen')}
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
              <th>Name</th>
              <th>E-Mail</th>
              <th>Telefon</th>
              <th>Typ</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id}>
                <td>{getName(c)}</td>
                <td>{c.email || '–'}</td>
                <td>{c.phone || '–'}</td>
                <td>{c.customer_type}</td>
                <td>
                  <button type="button" onClick={() => openDetail(c)} className="btn-secondary btn-sm">Detail</button>
                  <button type="button" onClick={() => openEdit(c)} className="btn-secondary btn-sm">Bearbeiten</button>
                  {user?.role_name === 'admin' && (
                    <>
                      <button type="button" onClick={() => handleExport(c)} className="btn-secondary btn-sm">Export</button>
                      <button type="button" onClick={() => handleDsgvoDelete(c)} className="btn-secondary btn-sm">DSGVO: Löschen</button>
                    </>
                  )}
                  <button type="button" onClick={() => handleDelete(c)} className="btn-secondary btn-sm">Deaktivieren</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}

      {detailCustomer && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>Kundendetail – {getName(detailCustomer)}</h2>
            <p>{detailCustomer.email || '–'} | {detailCustomer.phone || '–'}</p>
            <h3>Fahrzeuge</h3>
            {detailVehicles.length === 0 ? (
              <p>Keine Fahrzeuge.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, marginBottom: '1rem' }}>
                {detailVehicles.map((v) => (
                  <li key={v.id} style={{ marginBottom: '0.25rem' }}>
                    {v.license_plate || v.vin || 'Fahrzeug'} {v.build_year ? `(${v.build_year})` : ''} – {v.category === 'quad' ? 'Quad' : 'Motorrad'}
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
                  <li key={a.id} style={{ marginBottom: '0.75rem', padding: '0.5rem', border: '1px solid var(--color-border)', borderRadius: 6 }}>
                    <strong>{ADDRESS_TYPE_LABELS[a.address_type] || a.address_type}</strong>
                    <div>{a.street}{a.house_number ? ` ${a.house_number}` : ''}, {a.postal_code} {a.city}</div>
                    {a.country && a.country !== 'Deutschland' && <div>{a.country}</div>}
                    <button type="button" onClick={() => handleDeleteAddress(a.id)} className="btn-secondary btn-sm" style={{ marginTop: 4 }}>Entfernen</button>
                  </li>
                ))}
              </ul>
            )}
            {!showAddressForm ? (
              <button type="button" onClick={() => setShowAddressForm(true)} className="btn-primary" style={{ marginTop: '0.5rem' }}>
                + Adresse hinzufügen
              </button>
            ) : (
              <form onSubmit={handleAddAddress} style={{ marginTop: '1rem', padding: '1rem', border: '1px solid var(--color-border)', borderRadius: 8 }}>
                <h4>Neue Adresse</h4>
                <div className="form-group">
                  <label>Typ</label>
                  <select value={addressForm.address_type} onChange={(e) => setAddressForm({ ...addressForm, address_type: e.target.value })}>
                    <option value="main">Hauptadresse</option>
                    <option value="billing">Rechnungsadresse</option>
                    <option value="shipping">Lieferadresse</option>
                  </select>
                </div>
                <div className="form-row">
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Straße *</label>
                    <input value={addressForm.street} onChange={(e) => setAddressForm({ ...addressForm, street: e.target.value })} required placeholder="Musterstraße" />
                  </div>
                  <div className="form-group" style={{ maxWidth: 80 }}>
                    <label>Nr.</label>
                    <input value={addressForm.house_number} onChange={(e) => setAddressForm({ ...addressForm, house_number: e.target.value })} placeholder="1a" />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>PLZ *</label>
                    <input value={addressForm.postal_code} onChange={(e) => setAddressForm({ ...addressForm, postal_code: e.target.value })} required placeholder="90402" />
                  </div>
                  <div className="form-group" style={{ flex: 1 }}>
                    <label>Ort *</label>
                    <input value={addressForm.city} onChange={(e) => setAddressForm({ ...addressForm, city: e.target.value })} required placeholder="Nürnberg" />
                  </div>
                </div>
                <div className="form-group">
                  <label>Land</label>
                  <input value={addressForm.country} onChange={(e) => setAddressForm({ ...addressForm, country: e.target.value })} placeholder="Deutschland" />
                </div>
                <div className="form-actions">
                  <button type="button" onClick={() => setShowAddressForm(false)} className="btn-secondary">Abbrechen</button>
                  <button type="submit" className="btn-primary">Hinzufügen</button>
                </div>
              </form>
            )}
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={closeDetail} className="btn-secondary">Schließen</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
