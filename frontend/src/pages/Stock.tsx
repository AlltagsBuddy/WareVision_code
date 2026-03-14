import { useEffect, useState } from 'react'
import { stockApi, articlesApi } from '../api/client'

const MOVEMENT_LABELS: Record<string, string> = {
  incoming: 'Wareneingang',
  outgoing: 'Warenausgang',
  correction: 'Korrektur',
  workshop_consumption: 'Werkstattverbrauch',
  invoice_consumption: 'Rechnungsverbrauch',
}

export default function Stock() {
  const [lowStock, setLowStock] = useState<any[]>([])
  const [movements, setMovements] = useState<any[]>([])
  const [articles, setArticles] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    article_id: '',
    movement_type: 'incoming' as string,
    quantity: 1,
    notes: '',
  })

  const load = () => {
    setLoading(true)
    Promise.all([
      stockApi.lowStock(),
      stockApi.movements(),
      articlesApi.list(),
    ])
      .then(([low, mov, arts]) => {
        setLowStock(low)
        setMovements(mov)
        setArticles(arts)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.article_id || form.quantity < 1) {
      setError('Bitte Artikel und Menge angeben.')
      return
    }
    setSubmitting(true)
    try {
      await stockApi.createMovement({
        article_id: form.article_id,
        movement_type: form.movement_type,
        quantity: form.quantity,
        notes: form.notes || undefined,
      })
      setShowForm(false)
      setForm({ article_id: '', movement_type: 'incoming', quantity: 1, notes: '' })
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setSubmitting(false)
    }
  }

  const getArticleName = (id: string) => {
    const a = articles.find((x) => x.id === id)
    return a ? `${a.article_number} – ${a.name}` : id
  }

  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return '–'
    }
  }

  return (
    <div className="page">
      <h1>Lager</h1>
      <div className="toolbar">
        <button type="button" onClick={() => setShowForm(true)} className="btn-primary">
          + Wareneingang / Warenausgang
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Lagerbewegung erfassen</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Artikel *</label>
                <select
                  value={form.article_id}
                  onChange={(e) => setForm({ ...form, article_id: e.target.value })}
                  required
                >
                  <option value="">– Bitte wählen –</option>
                  {articles.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.article_number} – {a.name} (Bestand: {a.stock_quantity})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Bewegungstyp *</label>
                <select
                  value={form.movement_type}
                  onChange={(e) => setForm({ ...form, movement_type: e.target.value })}
                >
                  <option value="incoming">Wareneingang</option>
                  <option value="outgoing">Warenausgang</option>
                  <option value="correction">Korrektur</option>
                  <option value="workshop_consumption">Werkstattverbrauch</option>
                  <option value="invoice_consumption">Rechnungsverbrauch</option>
                </select>
              </div>
              <div className="form-group">
                <label>Menge *</label>
                <input
                  type="number"
                  min="1"
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: parseInt(e.target.value, 10) || 1 })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Notiz</label>
                <input
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="Optional"
                />
              </div>
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
                  Abbrechen
                </button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Wird erfasst...' : 'Speichern'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <h2>Mindestbestand (Warnung)</h2>
      {loading ? (
        <p>Laden...</p>
      ) : lowStock.length === 0 ? (
        <p>Keine Artikel unter Mindestbestand.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Artikelnummer</th>
              <th>Name</th>
              <th>Bestand</th>
              <th>Mindestbestand</th>
            </tr>
          </thead>
          <tbody>
            {lowStock.map((a) => (
              <tr key={a.id} className="warning-row">
                <td>{a.article_number}</td>
                <td>{a.name}</td>
                <td className="warning">{a.stock_quantity}</td>
                <td>{a.minimum_stock}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Letzte Lagerbewegungen</h2>
      {loading ? (
        <p>Laden...</p>
      ) : movements.length === 0 ? (
        <p>Keine Lagerbewegungen vorhanden.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Datum</th>
              <th>Artikel</th>
              <th>Typ</th>
              <th>Menge</th>
              <th>Notiz</th>
            </tr>
          </thead>
          <tbody>
            {movements.map((m) => (
              <tr key={m.id}>
                <td>{formatDate(m.created_at)}</td>
                <td>{getArticleName(m.article_id)}</td>
                <td>{MOVEMENT_LABELS[m.movement_type] || m.movement_type}</td>
                <td>{m.movement_type === 'incoming' || m.movement_type === 'correction' ? '+' : '-'}{m.quantity}</td>
                <td>{m.notes || '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
