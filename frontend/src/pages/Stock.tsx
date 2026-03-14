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
  const [barcodeInput, setBarcodeInput] = useState('')
  const [barcodeError, setBarcodeError] = useState('')

  const [reservations, setReservations] = useState<any[]>([])
  const [showReservationForm, setShowReservationForm] = useState(false)
  const [reservationForm, setReservationForm] = useState({
    article_id: '',
    quantity: 1,
    notes: '',
  })
  const [reservationError, setReservationError] = useState('')
  const [reservationSubmitting, setReservationSubmitting] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([
      stockApi.lowStock(),
      stockApi.movements(),
      stockApi.reservations({ status: 'active' }),
      articlesApi.list(),
    ])
      .then(([low, mov, res, arts]) => {
        setLowStock(low)
        setMovements(mov)
        setReservations(res)
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

  const handleBarcodeScan = async () => {
    const code = barcodeInput.trim()
    if (!code) return
    setBarcodeError('')
    try {
      const article = await articlesApi.getByBarcode(code)
      setForm((f) => ({ ...f, article_id: article.id }))
      setBarcodeInput('')
    } catch {
      setBarcodeError('Artikel mit diesem Barcode nicht gefunden')
    }
  }

  const handleReservationSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setReservationError('')
    if (!reservationForm.article_id || reservationForm.quantity < 1) {
      setReservationError('Bitte Artikel und Menge angeben.')
      return
    }
    setReservationSubmitting(true)
    try {
      await stockApi.createReservation({
        article_id: reservationForm.article_id,
        quantity: reservationForm.quantity,
        notes: reservationForm.notes || undefined,
      })
      setShowReservationForm(false)
      setReservationForm({ article_id: '', quantity: 1, notes: '' })
      load()
    } catch (err) {
      setReservationError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setReservationSubmitting(false)
    }
  }

  const handleReservationCancel = async (id: string) => {
    if (!confirm('Reservierung wirklich stornieren?')) return
    try {
      await stockApi.updateReservationStatus(id, 'cancelled')
      load()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleReservationConsume = async (id: string) => {
    if (!confirm('Reservierung als verbraucht markieren? (Erzeugt keine Lagerbewegung – bitte separat erfassen.)')) return
    try {
      await stockApi.updateReservationStatus(id, 'consumed')
      load()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
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
        <button type="button" onClick={() => setShowReservationForm(true)} className="btn-secondary">
          + Reservierung
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Lagerbewegung erfassen</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Barcode scannen</label>
                <div className="form-row" style={{ gap: '0.5rem', alignItems: 'flex-end' }}>
                  <input
                    type="text"
                    value={barcodeInput}
                    onChange={(e) => { setBarcodeInput(e.target.value); setBarcodeError('') }}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleBarcodeScan())}
                    placeholder="Barcode eingeben oder scannen (Enter)"
                    style={{ flex: 1 }}
                  />
                  <button type="button" onClick={handleBarcodeScan} className="btn-secondary">Suchen</button>
                </div>
                {barcodeError && <p className="error" style={{ marginTop: '0.25rem' }}>{barcodeError}</p>}
              </div>
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

      {showReservationForm && (
        <div className="modal-overlay" onClick={() => setShowReservationForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Bestand reservieren</h2>
            <form onSubmit={handleReservationSubmit}>
              <div className="form-group">
                <label>Artikel *</label>
                <select
                  value={reservationForm.article_id}
                  onChange={(e) => setReservationForm({ ...reservationForm, article_id: e.target.value })}
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
                <label>Menge *</label>
                <input
                  type="number"
                  min="1"
                  value={reservationForm.quantity}
                  onChange={(e) => setReservationForm({ ...reservationForm, quantity: parseInt(e.target.value, 10) || 1 })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Notiz</label>
                <input
                  value={reservationForm.notes}
                  onChange={(e) => setReservationForm({ ...reservationForm, notes: e.target.value })}
                  placeholder="z.B. Auftrag #123"
                />
              </div>
              {reservationError && <p className="error">{reservationError}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => setShowReservationForm(false)} className="btn-secondary">
                  Abbrechen
                </button>
                <button type="submit" disabled={reservationSubmitting} className="btn-primary">
                  {reservationSubmitting ? 'Wird reserviert...' : 'Reservieren'}
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
              <th>Reserviert</th>
              <th>Verfügbar</th>
              <th>Mindestbestand</th>
            </tr>
          </thead>
          <tbody>
            {lowStock.map((a) => (
              <tr key={a.id} className="warning-row">
                <td>{a.article_number}</td>
                <td>{a.name}</td>
                <td>{a.stock_quantity}</td>
                <td>{a.reserved_quantity ?? 0}</td>
                <td>{a.available_quantity ?? a.stock_quantity}</td>
                <td>{a.minimum_stock}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h2>Aktive Reservierungen</h2>
      {loading ? (
        <p>Laden...</p>
      ) : reservations.length === 0 ? (
        <p>Keine aktiven Reservierungen.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Artikel</th>
              <th>Menge</th>
              <th>Notiz</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {reservations.map((r) => (
              <tr key={r.id}>
                <td>{getArticleName(r.article_id)}</td>
                <td>{r.quantity}</td>
                <td>{r.notes || '–'}</td>
                <td>
                  <button
                    type="button"
                    className="btn-sm btn-secondary"
                    onClick={() => handleReservationConsume(r.id)}
                  >
                    Verbraucht
                  </button>
                  {' '}
                  <button
                    type="button"
                    className="btn-sm"
                    onClick={() => handleReservationCancel(r.id)}
                  >
                    Stornieren
                  </button>
                </td>
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
