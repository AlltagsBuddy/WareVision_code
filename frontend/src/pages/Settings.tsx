import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { settingsApi } from '../api/client'

export default function Settings() {
  const { user } = useAuth()
  const [terminMarktplatzConfigured, setTerminMarktplatzConfigured] = useState(false)
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
    smtp_host: '',
    smtp_port: '587',
    smtp_user: '',
    smtp_password: '',
    smtp_from: '',
    smtp_tls: 'true',
    termin_marktplatz_api_key: '',
  })
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    settingsApi
      .get()
      .then((data: { termin_marktplatz_configured?: boolean } & Record<string, string>) => {
        setTerminMarktplatzConfigured(!!data.termin_marktplatz_configured)
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
          smtp_host: data.smtp_host || '',
          smtp_port: data.smtp_port || '587',
          smtp_user: data.smtp_user || '',
          smtp_password: data.smtp_password || '',
          smtp_from: data.smtp_from || '',
          smtp_tls: data.smtp_tls || 'true',
          termin_marktplatz_api_key: '',
        })
      })
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
        smtp_host: form.smtp_host,
        smtp_port: form.smtp_port,
        smtp_user: form.smtp_user,
        smtp_password: form.smtp_password,
        smtp_from: form.smtp_from,
        smtp_tls: form.smtp_tls,
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

        <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', fontSize: '1rem' }}>E-Mail-Versand (SMTP)</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
          Für den Versand von Rechnungen und Dokumenten per E-Mail. Ohne Konfiguration ist der E-Mail-Button deaktiviert.
        </p>
        <div className="form-group">
          <label htmlFor="smtp_host">SMTP-Host *</label>
          <input
            id="smtp_host"
            type="text"
            value={form.smtp_host}
            onChange={(e) => setForm((f) => ({ ...f, smtp_host: e.target.value }))}
            placeholder="smtp.example.de"
          />
        </div>
        <div className="form-row" style={{ display: 'flex', gap: '1rem' }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label htmlFor="smtp_port">Port</label>
            <input
              id="smtp_port"
              type="text"
              value={form.smtp_port}
              onChange={(e) => setForm((f) => ({ ...f, smtp_port: e.target.value }))}
              placeholder="587"
            />
          </div>
          <div className="form-group" style={{ flex: 2 }}>
            <label>
              <input
                type="checkbox"
                checked={form.smtp_tls === 'true'}
                onChange={(e) => setForm((f) => ({ ...f, smtp_tls: e.target.checked ? 'true' : 'false' }))}
              />
              {' '}TLS verwenden
            </label>
          </div>
        </div>
        <div className="form-group">
          <label htmlFor="smtp_user">Benutzername</label>
          <input
            id="smtp_user"
            type="text"
            value={form.smtp_user}
            onChange={(e) => setForm((f) => ({ ...f, smtp_user: e.target.value }))}
            placeholder="Optional bei Auth"
          />
        </div>
        <div className="form-group">
          <label htmlFor="smtp_password">Passwort</label>
          <input
            id="smtp_password"
            type="password"
            value={form.smtp_password}
            onChange={(e) => setForm((f) => ({ ...f, smtp_password: e.target.value }))}
            placeholder="Leer lassen = unverändert"
          />
        </div>
        <div className="form-group">
          <label htmlFor="smtp_from">Absender-Adresse</label>
          <input
            id="smtp_from"
            type="email"
            value={form.smtp_from}
            onChange={(e) => setForm((f) => ({ ...f, smtp_from: e.target.value }))}
            placeholder="rechnungen@firma.de (sonst Benutzername)"
          />
        </div>

        <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', fontSize: '1rem' }}>Terminmarktplatz</h3>
        <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
          Gebuchte Termine von Terminmarktplatz.de werden automatisch in den Terminplaner übernommen.
        </p>
        <div className="form-group">
          <label htmlFor="termin_marktplatz_api_key">API-Schlüssel</label>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              id="termin_marktplatz_api_key"
              type="password"
              value={form.termin_marktplatz_api_key}
              onChange={(e) => setForm((f) => ({ ...f, termin_marktplatz_api_key: e.target.value }))}
              placeholder="Geheimer Schlüssel für Webhook-Authentifizierung"
              style={{ flex: 1, minWidth: 200 }}
            />
            <button
              type="button"
              className="btn"
              onClick={() => {
                settingsApi.getTerminMarktplatzApiKey().then((r) => {
                  if (r.api_key) {
                    navigator.clipboard.writeText(r.api_key)
                    alert(`API-Schlüssel kopiert: ${r.api_key}`)
                  } else {
                    alert('Noch kein API-Schlüssel hinterlegt. Bitte oben eintragen und speichern.')
                  }
                }).catch(() => alert('Fehler beim Laden'))
              }}
            >
              Anzeigen &amp; kopieren
            </button>
          </div>
        </div>
        {(form.termin_marktplatz_api_key || terminMarktplatzConfigured) && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'var(--color-bg-secondary)', borderRadius: 6, fontSize: '0.85rem' }}>
            <strong>Webhook-URL für Terminmarktplatz:</strong>
            <code style={{ display: 'block', marginTop: '0.5rem', wordBreak: 'break-all' }}>
              {typeof window !== 'undefined' ? `${window.location.origin}/api/v1/appointments/webhook/termin-marktplatz` : ''}
            </code>
            <p style={{ margin: '0.5rem 0 0 0', color: 'var(--color-text-muted)' }}>
              Diese URL in Terminmarktplatz hinterlegen. Header: <code>X-API-Key: [dein Schlüssel]</code>
            </p>
          </div>
        )}
        {error && <p className="error">{error}</p>}
        {success && <p className="success">Einstellungen gespeichert.</p>}
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Speichern…' : 'Speichern'}
        </button>
      </form>
    </div>
  )
}
