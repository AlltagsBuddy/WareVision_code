import { useEffect, useState } from 'react'
import { suppliersApi } from '../api/client'

const EMPTY_FORM = {
  name: '',
  email: '',
  phone: '',
  contact_person: '',
  street: '',
  house_number: '',
  postal_code: '',
  city: '',
  country: 'Deutschland',
  customer_number: '',
  notes: '',
}

export default function Suppliers() {
  const [suppliers, setSuppliers] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState('name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form, setForm] = useState({ ...EMPTY_FORM })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    suppliersApi.list().then(setSuppliers).finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const resetForm = () => {
    setForm({ ...EMPTY_FORM })
    setEditing(null)
    setError('')
  }

  const openNew = () => {
    resetForm()
    setShowForm(true)
  }

  const openEdit = (s: any) => {
    setEditing(s)
    setForm({
      name: s.name,
      email: s.email || '',
      phone: s.phone || '',
      contact_person: s.contact_person || '',
      street: s.street || '',
      house_number: s.house_number || '',
      postal_code: s.postal_code || '',
      city: s.city || '',
      country: s.country || 'Deutschland',
      customer_number: s.customer_number || '',
      notes: s.notes || '',
    })
    setError('')
    setShowForm(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const data = {
        name: form.name.trim(),
        email: form.email || undefined,
        phone: form.phone || undefined,
        contact_person: form.contact_person || undefined,
        street: form.street || undefined,
        house_number: form.house_number || undefined,
        postal_code: form.postal_code || undefined,
        city: form.city || undefined,
        country: form.country || undefined,
        customer_number: form.customer_number.trim() || null,
        notes: form.notes || undefined,
      }
      if (editing) {
        await suppliersApi.update(editing.id, data)
      } else {
        await suppliersApi.create(data)
      }
      setShowForm(false)
      resetForm()
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (s: any) => {
    if (!confirm(`Lieferant "${s.name}" wirklich löschen?`)) return
    try {
      await suppliersApi.delete(s.id)
      setSuppliers((prev) => prev.filter((x) => x.id !== s.id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortField(field); setSortDir('asc') }
  }
  const sortIcon = (field: string) => sortField === field ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ↕'

  const q = search.toLowerCase()
  const displayed = [...suppliers]
    .filter((s) =>
      !q ||
      s.name.toLowerCase().includes(q) ||
      (s.contact_person || '').toLowerCase().includes(q) ||
      (s.city || '').toLowerCase().includes(q)
    )
    .sort((a, b) => {
      let va = '', vb = ''
      if (sortField === 'city') { va = a.city || ''; vb = b.city || '' }
      else if (sortField === 'contact_person') { va = a.contact_person || ''; vb = b.contact_person || '' }
      else if (sortField === 'created_at') { va = a.created_at || ''; vb = b.created_at || '' }
      else { va = a.name || ''; vb = b.name || '' }
      return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va)
    })

  return (
    <div className="page">
      <h1>Lieferanten</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Name, Ansprechpartner, Ort..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button type="button" onClick={openNew} className="btn-primary">+ Neuer Lieferant</button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => { setShowForm(false); resetForm() }}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? 'Lieferant bearbeiten' : 'Neuer Lieferant'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label>Name *</label>
                  <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label>Ansprechpartner</label>
                  <input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} placeholder="Vor- und Nachname" />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>E-Mail</label>
                  <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Telefon</label>
                  <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group" style={{ flex: 3 }}>
                  <label>Straße</label>
                  <input value={form.street} onChange={(e) => setForm({ ...form, street: e.target.value })} />
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label>Hausnummer</label>
                  <input value={form.house_number} onChange={(e) => setForm({ ...form, house_number: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group" style={{ flex: 1 }}>
                  <label>PLZ</label>
                  <input value={form.postal_code} onChange={(e) => setForm({ ...form, postal_code: e.target.value })} />
                </div>
                <div className="form-group" style={{ flex: 2 }}>
                  <label>Ort</label>
                  <input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
                </div>
                <div className="form-group" style={{ flex: 2 }}>
                  <label>Land</label>
                  <input value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })} />
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="sup-customer-no">Unsere Kundennummer beim Lieferanten</label>
                <input id="sup-customer-no" maxLength={100} value={form.customer_number} onChange={(e) => setForm({ ...form, customer_number: e.target.value })} placeholder="steht auf der Bestellung" />
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
      ) : suppliers.length === 0 ? (
        <p>Keine Lieferanten vorhanden.</p>
      ) : (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>Name{sortIcon('name')}</th>
                <th onClick={() => handleSort('contact_person')} style={{ cursor: 'pointer' }}>Ansprechpartner{sortIcon('contact_person')}</th>
                <th>E-Mail</th>
                <th>Telefon</th>
                <th onClick={() => handleSort('city')} style={{ cursor: 'pointer' }}>Ort{sortIcon('city')}</th>
                <th onClick={() => handleSort('created_at')} style={{ cursor: 'pointer' }}>Erstellt{sortIcon('created_at')}</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {displayed.map((s) => (
                <tr key={s.id}>
                  <td><strong>{s.name}</strong></td>
                  <td>{s.contact_person || '–'}</td>
                  <td>{s.email ? <a href={`mailto:${s.email}`}>{s.email}</a> : '–'}</td>
                  <td>{s.phone || '–'}</td>
                  <td>{s.city ? `${s.postal_code ? s.postal_code + ' ' : ''}${s.city}` : '–'}</td>
                  <td>{s.created_at ? new Date(s.created_at).toLocaleDateString('de-DE') : '–'}</td>
                  <td>
                    <button type="button" onClick={() => openEdit(s)} className="btn-secondary btn-sm">Bearbeiten</button>
                    <button type="button" onClick={() => handleDelete(s)} className="btn-secondary btn-sm">Löschen</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
