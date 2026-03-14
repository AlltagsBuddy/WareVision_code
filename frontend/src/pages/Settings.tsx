import { useEffect, useState } from 'react'
import { settingsApi } from '../api/client'

export default function Settings() {
  const [form, setForm] = useState({
    company_name: '',
    company_address: '',
    company_vat_id: '',
    termin_marktplatz_api_key: '',
  })
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    settingsApi
      .get()
      .then((data) =>
        setForm({
          company_name: data.company_name || '',
          company_address: data.company_address || '',
          company_vat_id: data.company_vat_id || '',
          termin_marktplatz_api_key: '',
        })
      )
      .catch(() => setError('Einstellungen konnten nicht geladen werden.'))
      .finally(() => setLoading(false))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess(false)
    setSubmitting(true)
    try {
      await settingsApi.update({
        company_name: form.company_name,
        company_address: form.company_address,
        company_vat_id: form.company_vat_id,
        termin_marktplatz_api_key: form.termin_marktplatz_api_key,
      })
      setSuccess(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <div className="loading">Laden...</div>

  return (
    <div className="page">
      <h1>Einstellungen</h1>
      <p className="muted">Firmenangaben für Rechnungen und Dokumente.</p>

      <form onSubmit={handleSubmit} className="card form-card" style={{ maxWidth: 500 }}>
        <div className="form-group">
          <label htmlFor="company_name">Firmenname</label>
          <input
            id="company_name"
            type="text"
            value={form.company_name}
            onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
            placeholder="z.B. WareVision GmbH"
          />
        </div>
        <div className="form-group">
          <label htmlFor="company_address">Adresse</label>
          <textarea
            id="company_address"
            value={form.company_address}
            onChange={(e) => setForm((f) => ({ ...f, company_address: e.target.value }))}
            placeholder="Straße, PLZ Ort"
            rows={3}
          />
        </div>
        <div className="form-group">
          <label htmlFor="company_vat_id">USt-IdNr.</label>
          <input
            id="company_vat_id"
            type="text"
            value={form.company_vat_id}
            onChange={(e) => setForm((f) => ({ ...f, company_vat_id: e.target.value }))}
            placeholder="DE123456789"
          />
        </div>
        <div className="form-group">
          <label htmlFor="termin_marktplatz_api_key">Termin-Marktplatz API-Schlüssel</label>
          <input
            id="termin_marktplatz_api_key"
            type="password"
            value={form.termin_marktplatz_api_key}
            onChange={(e) => setForm((f) => ({ ...f, termin_marktplatz_api_key: e.target.value }))}
            placeholder="Optional – für Webhook-Authentifizierung"
          />
        </div>
        {error && <p className="error">{error}</p>}
        {success && <p className="success">Einstellungen gespeichert.</p>}
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Speichern…' : 'Speichern'}
        </button>
      </form>
    </div>
  )
}
