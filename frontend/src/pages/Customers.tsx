import { useEffect, useState } from 'react'
import { customersApi } from '../api/client'

export default function Customers() {
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
                  <button type="button" onClick={() => openEdit(c)} className="btn-secondary btn-sm">Bearbeiten</button>
                  <button type="button" onClick={() => handleDelete(c)} className="btn-secondary btn-sm">Deaktivieren</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
