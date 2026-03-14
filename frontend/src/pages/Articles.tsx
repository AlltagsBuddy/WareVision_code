import { useEffect, useState } from 'react'
import { articlesApi } from '../api/client'

export default function Articles() {
  const [articles, setArticles] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [barcodeInput, setBarcodeInput] = useState('')
  const [barcodeFilter, setBarcodeFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form, setForm] = useState({
    article_number: '',
    name: '',
    description: '',
    purchase_price: 0,
    sales_price_b2c: 0,
    sales_price_b2b: 0,
    vat_rate: 19,
    minimum_stock: 0,
    barcode: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    articlesApi
      .list({ search: barcodeFilter ? undefined : (search || undefined), barcode: barcodeFilter || undefined })
      .then(setArticles)
      .finally(() => setLoading(false))
  }, [search, barcodeFilter])

  const resetForm = () => {
    setForm({
      article_number: '',
      name: '',
      description: '',
      purchase_price: 0,
      sales_price_b2c: 0,
      sales_price_b2b: 0,
      vat_rate: 19,
      minimum_stock: 0,
      barcode: '',
    })
    setEditing(null)
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      if (editing) {
        const updateData = {
          name: form.name,
          description: form.description || undefined,
          purchase_price: form.purchase_price,
          sales_price_b2c: form.sales_price_b2c,
          sales_price_b2b: form.sales_price_b2b,
          vat_rate: form.vat_rate,
          minimum_stock: form.minimum_stock,
          barcode: form.barcode || undefined,
        }
        await articlesApi.update(editing.id, updateData)
        setArticles((prev) => prev.map((a) => (a.id === editing.id ? { ...a, ...updateData } : a)))
      } else {
        const createData = {
          article_number: form.article_number,
          name: form.name,
          description: form.description || undefined,
          purchase_price: form.purchase_price,
          sales_price_b2c: form.sales_price_b2c,
          sales_price_b2b: form.sales_price_b2b,
          vat_rate: form.vat_rate,
          minimum_stock: form.minimum_stock,
          barcode: form.barcode || undefined,
        }
        await articlesApi.create(createData)
        const updated = await articlesApi.list({ search: search || undefined })
        setArticles(updated)
      }
      setShowForm(false)
      resetForm()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (a: any) => {
    if (!confirm(`Artikel "${a.name}" wirklich löschen?`)) return
    try {
      await articlesApi.delete(a.id)
      setArticles((prev) => prev.filter((x) => x.id !== a.id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const openEdit = (a: any) => {
    setEditing(a)
    setForm({
      article_number: a.article_number,
      name: a.name,
      description: a.description || '',
      purchase_price: Number(a.purchase_price),
      sales_price_b2c: Number(a.sales_price_b2c),
      sales_price_b2b: Number(a.sales_price_b2b),
      vat_rate: Number(a.vat_rate),
      minimum_stock: a.minimum_stock,
      barcode: a.barcode || '',
    })
    setShowForm(true)
  }

  return (
    <div className="page">
      <h1>Artikel</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Artikelnummer oder Name..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setBarcodeFilter('') }}
        />
        <input
          type="text"
          placeholder="Barcode (Enter)"
          value={barcodeInput}
          onChange={(e) => setBarcodeInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              const val = barcodeInput.trim()
              if (val) {
                setBarcodeFilter(val)
                setSearch('')
              }
            }
          }}
          style={{ maxWidth: 160 }}
        />
        <button type="button" onClick={() => { resetForm(); setShowForm(true) }} className="btn-primary">+ Neuer Artikel</button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => { setShowForm(false); resetForm() }}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? 'Artikel bearbeiten' : 'Neuer Artikel'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label>Artikelnummer *</label>
                  <input value={form.article_number} onChange={(e) => setForm({ ...form, article_number: e.target.value })} required disabled={!!editing} />
                </div>
                <div className="form-group">
                  <label>Barcode</label>
                  <input value={form.barcode} onChange={(e) => setForm({ ...form, barcode: e.target.value })} placeholder="EAN/GTIN" />
                </div>
              </div>
              <div className="form-group">
                <label>Bezeichnung *</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Beschreibung</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>EK (€)</label>
                  <input type="number" step="0.01" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: parseFloat(e.target.value) || 0 })} />
                </div>
                <div className="form-group">
                  <label>VK B2C (€)</label>
                  <input type="number" step="0.01" value={form.sales_price_b2c} onChange={(e) => setForm({ ...form, sales_price_b2c: parseFloat(e.target.value) || 0 })} />
                </div>
                <div className="form-group">
                  <label>VK B2B (€)</label>
                  <input type="number" step="0.01" value={form.sales_price_b2b} onChange={(e) => setForm({ ...form, sales_price_b2b: parseFloat(e.target.value) || 0 })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>MwSt %</label>
                  <input type="number" step="0.01" value={form.vat_rate} onChange={(e) => setForm({ ...form, vat_rate: parseFloat(e.target.value) || 19 })} />
                </div>
                <div className="form-group">
                  <label>Mindestbestand</label>
                  <input type="number" value={form.minimum_stock} onChange={(e) => setForm({ ...form, minimum_stock: parseInt(e.target.value, 10) || 0 })} min="0" />
                </div>
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
              <th>Art.-Nr.</th>
              <th>Name</th>
              <th>Barcode</th>
              <th>Bestand</th>
              <th>Mindestbestand</th>
              <th>VK B2C</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {articles.map((a) => (
              <tr key={a.id} className={a.minimum_stock > 0 && a.stock_quantity < a.minimum_stock ? 'warning-row' : ''}>
                <td>{a.article_number}</td>
                <td>{a.name}</td>
                <td>{a.barcode || '–'}</td>
                <td>{a.stock_quantity}</td>
                <td>{a.minimum_stock}</td>
                <td>{Number(a.sales_price_b2c).toFixed(2)} €</td>
                <td>
                  <button type="button" onClick={() => openEdit(a)} className="btn-secondary btn-sm">Bearbeiten</button>
                  <button type="button" onClick={() => handleDelete(a)} className="btn-secondary btn-sm">Löschen</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
