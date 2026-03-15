import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { settingsApi } from '../api/client'

export default function Settings() {
  const { user } = useAuth()
  const [form, setForm] = useState({
    company_name: '',
    company_address: '',
    company_vat_id: '',
    company_email: '',
    company_phone: '',
    company_website: '',
    company_bank_name: '',
    company_bank_iban: '',
    company_bank_bic: '',
    company_bank_account_holder: '',
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
          company_email: data.company_email || '',
          company_phone: data.company_phone || '',
          company_website: data.company_website || '',
          company_bank_name: data.company_bank_name || '',
          company_bank_iban: data.company_bank_iban || '',
          company_bank_bic: data.company_bank_bic || '',
          company_bank_account_holder: data.company_bank_account_holder || '',
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
        company_email: form.company_email,
        company_phone: form.company_phone,
        company_website: form.company_website,
        company_bank_name: form.company_bank_name,
        company_bank_iban: form.company_bank_iban,
        company_bank_bic: form.company_bank_bic,
        company_bank_account_holder: form.company_bank_account_holder,
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

      {user?.role_name === 'admin' && (
        <div className="card" style={{ maxWidth: 500, marginBottom: '1.5rem', padding: '1rem' }}>
          <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1rem' }}>Benutzerverwaltung</h3>
          <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
            Benutzer anlegen, bearbeiten oder deaktivieren.
          </p>
          <Link to="/users" className="btn-primary" style={{ display: 'inline-block', marginTop: '0.75rem' }}>
            Benutzer verwalten
          </Link>
        </div>
      )}

      <form onSubmit={handleSubmit} className="card form-card" style={{ maxWidth: 500 }}>
        <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem' }}>Firmendaten</h3>
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
            placeholder="Straße, Hausnummer, PLZ Ort"
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

        <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', fontSize: '1rem' }}>Kontakt</h3>
        <div className="form-group">
          <label htmlFor="company_email">E-Mail</label>
          <input
            id="company_email"
            type="email"
            value={form.company_email}
            onChange={(e) => setForm((f) => ({ ...f, company_email: e.target.value }))}
            placeholder="info@firma.de"
          />
        </div>
        <div className="form-group">
          <label htmlFor="company_phone">Telefon</label>
          <input
            id="company_phone"
            type="tel"
            value={form.company_phone}
            onChange={(e) => setForm((f) => ({ ...f, company_phone: e.target.value }))}
            placeholder="+49 123 456789"
          />
        </div>
        <div className="form-group">
          <label htmlFor="company_website">Website</label>
          <input
            id="company_website"
            type="url"
            value={form.company_website}
            onChange={(e) => setForm((f) => ({ ...f, company_website: e.target.value }))}
            placeholder="https://www.firma.de"
          />
        </div>

        <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', fontSize: '1rem' }}>Bankverbindung (für Überweisungen)</h3>
        <div className="form-group">
          <label htmlFor="company_bank_account_holder">Kontoinhaber</label>
          <input
            id="company_bank_account_holder"
            type="text"
            value={form.company_bank_account_holder}
            onChange={(e) => setForm((f) => ({ ...f, company_bank_account_holder: e.target.value }))}
            placeholder="Firmenname oder Inhaber (leer = Firmenname)"
          />
        </div>
        <div className="form-group">
          <label htmlFor="company_bank_name">Bank</label>
          <input
            id="company_bank_name"
            type="text"
            value={form.company_bank_name}
            onChange={(e) => setForm((f) => ({ ...f, company_bank_name: e.target.value }))}
            placeholder="z.B. Sparkasse Musterstadt"
          />
        </div>
        <div className="form-group">
          <label htmlFor="company_bank_iban">IBAN</label>
          <input
            id="company_bank_iban"
            type="text"
            value={form.company_bank_iban}
            onChange={(e) => setForm((f) => ({ ...f, company_bank_iban: e.target.value }))}
            placeholder="DE89 3704 0044 0532 0130 00"
          />
        </div>
        <div className="form-group">
          <label htmlFor="company_bank_bic">BIC / SWIFT</label>
          <input
            id="company_bank_bic"
            type="text"
            value={form.company_bank_bic}
            onChange={(e) => setForm((f) => ({ ...f, company_bank_bic: e.target.value }))}
            placeholder="COBADEFFXXX"
          />
        </div>

        <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', fontSize: '1rem' }}>Sonstiges</h3>
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
