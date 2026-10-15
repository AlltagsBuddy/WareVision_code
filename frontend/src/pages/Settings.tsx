import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { settingsApi, tasksApi, healthApi, laborRatesApi } from '../api/client'
import { isManager } from '../utils/permissions'

export default function Settings() {
  const { user } = useAuth()
  const [terminMarktplatzConfigured, setTerminMarktplatzConfigured] = useState(false)
  const [resendConfigured, setResendConfigured] = useState(false)
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
    invoice_vat_exemption_note: '',
    smtp_host: '',
    smtp_port: '587',
    smtp_user: '',
    smtp_password: '',
    smtp_from: '',
    smtp_tls: 'true',
    termin_marktplatz_api_key: '',
    termin_marktplatz_webhook_base_url: '',
    termin_marktplatz_cancel_callback_url: '',
    resend_api_key: '',
    resend_from_email: '',
    resend_from_name: '',
    ai_help_api_key: '',
    ai_help_model: '',
  })
  const [logoSet, setLogoSet] = useState(false)
  const [aiConfigured, setAiConfigured] = useState(false)
  const [aiRemove, setAiRemove] = useState(false)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const [logoUploading, setLogoUploading] = useState(false)
  const [logoError, setLogoError] = useState('')
  const logoInputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [testEmailAddr, setTestEmailAddr] = useState('')
  const [testEmailSending, setTestEmailSending] = useState(false)
  const [testEmailResult, setTestEmailResult] = useState<{ ok: boolean; msg: string } | null>(null)

  // Stundenpreise
  const [laborRates, setLaborRates] = useState<any[]>([])
  const [showLaborForm, setShowLaborForm] = useState(false)
  const [laborForm, setLaborForm] = useState({ name: '', description: '', rate_per_hour: '', is_default: false })
  const [laborSubmitting, setLaborSubmitting] = useState(false)
  const [laborError, setLaborError] = useState('')
  const [editLaborId, setEditLaborId] = useState<string | null>(null)

  useEffect(() => {
    laborRatesApi.list().then(setLaborRates).catch(() => {})
  }, [])

  const handleLaborSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!laborForm.name.trim() || !laborForm.rate_per_hour) {
      setLaborError('Name und Stundenpreis sind erforderlich.')
      return
    }
    setLaborSubmitting(true)
    setLaborError('')
    try {
      const data = {
        name: laborForm.name.trim(),
        description: laborForm.description || undefined,
        rate_per_hour: parseFloat(laborForm.rate_per_hour),
        is_default: laborForm.is_default,
      }
      if (editLaborId) {
        await laborRatesApi.update(editLaborId, data)
      } else {
        await laborRatesApi.create(data)
      }
      const updated = await laborRatesApi.list()
      setLaborRates(updated)
      setShowLaborForm(false)
      setEditLaborId(null)
      setLaborForm({ name: '', description: '', rate_per_hour: '', is_default: false })
    } catch (err) {
      setLaborError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setLaborSubmitting(false)
    }
  }

  const openEditLabor = (r: any) => {
    setEditLaborId(r.id)
    setLaborForm({ name: r.name, description: r.description || '', rate_per_hour: String(Number(r.rate_per_hour)), is_default: r.is_default })
    setLaborError('')
    setShowLaborForm(true)
  }

  const handleDeleteLabor = async (id: string) => {
    if (!confirm('Stundenpreis wirklich löschen?')) return
    await laborRatesApi.delete(id)
    setLaborRates((prev) => prev.filter((r) => r.id !== id))
  }

  useEffect(() => {
    settingsApi
      .get()
      .then((data) => {
        setTerminMarktplatzConfigured(!!data.termin_marktplatz_configured)
        setResendConfigured(!!data.resend_configured)
        setAiConfigured(!!data.ai_help_configured)
        setLogoSet(!!data.company_logo_set)
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
          invoice_vat_exemption_note: data.invoice_vat_exemption_note || '',
          smtp_host: data.smtp_host || '',
          smtp_port: data.smtp_port || '587',
          smtp_user: data.smtp_user || '',
          smtp_password: data.smtp_password || '',
          smtp_from: data.smtp_from || '',
          smtp_tls: data.smtp_tls || 'true',
          termin_marktplatz_api_key: '',
          termin_marktplatz_webhook_base_url: data.termin_marktplatz_webhook_base_url || '',
          termin_marktplatz_cancel_callback_url: data.termin_marktplatz_cancel_callback_url || '',
          resend_api_key: '',
          resend_from_email: data.resend_from_email || '',
          resend_from_name: data.resend_from_name || '',
          ai_help_api_key: '',
          ai_help_model: data.ai_help_model || '',
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
        invoice_vat_exemption_note: form.invoice_vat_exemption_note,
        smtp_host: form.smtp_host,
        smtp_port: form.smtp_port,
        smtp_user: form.smtp_user,
        smtp_password: form.smtp_password,
        smtp_from: form.smtp_from,
        smtp_tls: form.smtp_tls,
        termin_marktplatz_api_key: form.termin_marktplatz_api_key,
        termin_marktplatz_webhook_base_url: form.termin_marktplatz_webhook_base_url || undefined,
        termin_marktplatz_cancel_callback_url: form.termin_marktplatz_cancel_callback_url || undefined,
        resend_api_key: form.resend_api_key || undefined,
        resend_from_email: form.resend_from_email || undefined,
        resend_from_name: form.resend_from_name || undefined,
        ai_help_api_key: form.ai_help_api_key || undefined,
        ai_help_model: form.ai_help_model,
        ai_help_api_key_remove: aiRemove || undefined,
      })
      if (form.ai_help_api_key) setAiConfigured(true)
      if (aiRemove) { setAiConfigured(false); setAiRemove(false) }
      setForm((f) => ({ ...f, ai_help_api_key: '' }))
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

      {isManager(user) && (
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

      <div className="card form-card" style={{ maxWidth: 500, marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 style={{ margin: 0, fontSize: '1rem' }}>Stundenpreise</h3>
          {!showLaborForm && (
            <button type="button" className="btn-primary btn-sm" onClick={() => { setEditLaborId(null); setLaborForm({ name: '', description: '', rate_per_hour: '', is_default: false }); setLaborError(''); setShowLaborForm(true) }}>
              + Hinzufügen
            </button>
          )}
        </div>
        {showLaborForm && (
          <form onSubmit={handleLaborSubmit} style={{ marginBottom: '1rem', padding: '0.75rem', border: '1px solid var(--color-border)', borderRadius: 6 }}>
            <h4 style={{ margin: '0 0 0.75rem' }}>{editLaborId ? 'Stundenpreis bearbeiten' : 'Neuer Stundenpreis'}</h4>
            <div className="form-group">
              <label>Bezeichnung *</label>
              <input value={laborForm.name} onChange={(e) => setLaborForm((f) => ({ ...f, name: e.target.value }))} placeholder="z.B. Werkstattarbeit, Diagnose, Elektrik..." required />
            </div>
            <div className="form-group">
              <label>Beschreibung</label>
              <input value={laborForm.description} onChange={(e) => setLaborForm((f) => ({ ...f, description: e.target.value }))} placeholder="Optional" />
            </div>
            <div className="form-group">
              <label>Preis pro Stunde (€) *</label>
              <input type="number" step="0.01" min="0.01" value={laborForm.rate_per_hour} onChange={(e) => setLaborForm((f) => ({ ...f, rate_per_hour: e.target.value }))} placeholder="z.B. 85.00" required />
            </div>
            <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.5rem' }}>
              <input type="checkbox" id="labor_default" checked={laborForm.is_default} onChange={(e) => setLaborForm((f) => ({ ...f, is_default: e.target.checked }))} style={{ width: 'auto' }} />
              <label htmlFor="labor_default" style={{ margin: 0 }}>Standard (wird im Auftragsformular vorausgewählt)</label>
            </div>
            {laborError && <p className="error">{laborError}</p>}
            <div className="form-actions">
              <button type="button" className="btn-secondary" onClick={() => { setShowLaborForm(false); setEditLaborId(null) }}>Abbrechen</button>
              <button type="submit" className="btn-primary" disabled={laborSubmitting}>{laborSubmitting ? 'Speichern...' : 'Speichern'}</button>
            </div>
          </form>
        )}
        {laborRates.length === 0 ? (
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', margin: 0 }}>Noch keine Stundenpreise angelegt.</p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {laborRates.map((r) => (
              <li key={r.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)' }}>
                <div style={{ flex: 1 }}>
                  <strong>{r.name}</strong>
                  {r.is_default && <span style={{ marginLeft: '0.4rem', fontSize: '0.75rem', background: 'var(--color-primary)', color: '#fff', borderRadius: 3, padding: '1px 5px' }}>Standard</span>}
                  {!r.is_active && <span style={{ marginLeft: '0.4rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>(inaktiv)</span>}
                  {r.description && <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{r.description}</div>}
                  <div style={{ fontSize: '0.85rem', color: 'var(--color-primary)', fontWeight: 600 }}>{Number(r.rate_per_hour).toFixed(2)} €/Std.</div>
                </div>
                <button type="button" className="btn-secondary btn-sm" onClick={() => openEditLabor(r)}>Bearbeiten</button>
                <button type="button" className="btn-secondary btn-sm" onClick={() => handleDeleteLabor(r.id)} style={{ color: 'var(--color-error)' }}>Löschen</button>
              </li>
            ))}
          </ul>
        )}
      </div>

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

        <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', fontSize: '1rem' }}>Firmenlogo (Rechnungen)</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          {logoPreview ? (
            <img src={logoPreview} alt="Logo-Vorschau" style={{ height: 60, objectFit: 'contain', border: '1px solid var(--color-border)', borderRadius: 6, padding: 4, background: '#fff' }} />
          ) : logoSet ? (
            <img src="/api/v1/settings/logo" alt="Aktuelles Logo" style={{ height: 60, objectFit: 'contain', border: '1px solid var(--color-border)', borderRadius: 6, padding: 4, background: '#fff' }} />
          ) : (
            <div style={{ height: 60, width: 120, border: '1px dashed var(--color-border)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
              Kein Logo
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            <input
              ref={logoInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              style={{ display: 'none' }}
              onChange={async (e) => {
                const file = e.target.files?.[0]
                if (!file) return
                setLogoError('')
                // Lokale Vorschau
                const previewUrl = URL.createObjectURL(file)
                setLogoPreview(previewUrl)
                // Hochladen
                setLogoUploading(true)
                try {
                  await settingsApi.uploadLogo(file)
                  setLogoSet(true)
                } catch (err) {
                  setLogoError(err instanceof Error ? err.message : 'Upload fehlgeschlagen')
                  setLogoPreview(null)
                } finally {
                  setLogoUploading(false)
                }
              }}
            />
            <button type="button" className="btn-secondary" onClick={() => logoInputRef.current?.click()} disabled={logoUploading}>
              {logoUploading ? 'Hochladen...' : logoSet || logoPreview ? 'Logo ersetzen' : 'Logo hochladen'}
            </button>
            <span style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>PNG, JPG oder WebP, max. 2 MB</span>
            {logoError && <span style={{ fontSize: '0.82rem', color: 'var(--color-error)' }}>{logoError}</span>}
          </div>
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
        <div className="form-group">
          <label htmlFor="invoice_vat_exemption_note">Hinweis bei 0 % MwSt (Steuerbefreiung)</label>
          <textarea
            id="invoice_vat_exemption_note"
            rows={2}
            value={form.invoice_vat_exemption_note}
            onChange={(e) => setForm((f) => ({ ...f, invoice_vat_exemption_note: e.target.value }))}
            placeholder="z. B. Durchlaufender Posten (TÜV-Gebühr) – nicht umsatzsteuerbar"
          />
          <small style={{ color: 'var(--color-text-muted)' }}>
            Erscheint auf Rechnungen mit 0-%-Positionen und in der E-Rechnung. Den richtigen Text bitte mit dem Steuerberater abstimmen.
          </small>
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

        <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', fontSize: '1rem' }}>KI-Hilfe (Claude)</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
          Mit API-Key beantwortet ein KI-Assistent Fragen zur Bedienung (Seite „Hilfe“). Die Frage wird dafür an Anthropic
          übermittelt; E-Mail-Adressen, Telefonnummern, IBANs und Kennzeichen werden vorher automatisch entfernt. Ohne Key
          nutzt die Hilfe eine Stichwortsuche, und es verlassen keine Daten den Server.
          {aiConfigured && <strong style={{ color: 'var(--color-success)', marginLeft: '0.5rem' }}>✓ KI-Hilfe aktiv</strong>}
        </p>
        <div className="form-group">
          <label htmlFor="ai_help_api_key">Anthropic API-Key</label>
          <input
            id="ai_help_api_key"
            type="password"
            autoComplete="off"
            value={form.ai_help_api_key}
            onChange={(e) => setForm((f) => ({ ...f, ai_help_api_key: e.target.value }))}
            placeholder={aiConfigured ? '(gesetzt – leer lassen = unverändert)' : 'sk-ant-...'}
          />
          {aiConfigured && (
            <label style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', marginTop: '0.4rem', fontWeight: 400 }}>
              <input type="checkbox" checked={aiRemove} onChange={(e) => setAiRemove(e.target.checked)} /> API-Key beim Speichern entfernen
            </label>
          )}
        </div>
        <div className="form-group">
          <label htmlFor="ai_help_model">Modell (optional)</label>
          <input
            id="ai_help_model"
            type="text"
            value={form.ai_help_model}
            onChange={(e) => setForm((f) => ({ ...f, ai_help_model: e.target.value }))}
            placeholder="claude-haiku-5-5 (Standard)"
          />
        </div>

        <h3 style={{ marginTop: '1.5rem', marginBottom: '1rem', fontSize: '1rem' }}>E-Mail-Versand (Resend)</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
          Resend hat Vorrang vor SMTP. Wenn der API-Key gesetzt ist, werden alle E-Mails über Resend versendet.
          {resendConfigured && <strong style={{ color: 'var(--color-success)', marginLeft: '0.5rem' }}>✓ Resend konfiguriert</strong>}
        </p>
        <div className="form-group">
          <label htmlFor="resend_api_key">API-Key</label>
          <input
            id="resend_api_key"
            type="password"
            value={form.resend_api_key}
            onChange={(e) => setForm((f) => ({ ...f, resend_api_key: e.target.value }))}
            placeholder={resendConfigured ? '(gesetzt – leer lassen = unverändert)' : 're_xxxxxxxxxxxxxxxxxxxx'}
          />
        </div>
        <div className="form-group">
          <label htmlFor="resend_from_email">Absender-E-Mail</label>
          <input
            id="resend_from_email"
            type="email"
            value={form.resend_from_email}
            onChange={(e) => setForm((f) => ({ ...f, resend_from_email: e.target.value }))}
            placeholder="info@quadparadies-schoner.de"
          />
        </div>
        <div className="form-group">
          <label htmlFor="resend_from_name">Absender-Name</label>
          <input
            id="resend_from_name"
            type="text"
            value={form.resend_from_name}
            onChange={(e) => setForm((f) => ({ ...f, resend_from_name: e.target.value }))}
            placeholder="Quad Paradies Schoner"
          />
        </div>

        <div style={{ marginTop: '1.5rem', padding: '0.75rem', background: 'var(--color-bg)', borderRadius: 6, border: '1px solid var(--color-border)' }}>
          <strong style={{ fontSize: '0.9rem' }}>E-Mail-Konfiguration testen</strong>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <input
              type="email"
              value={testEmailAddr}
              onChange={(e) => { setTestEmailAddr(e.target.value); setTestEmailResult(null) }}
              placeholder="empfaenger@beispiel.de (leer = company_email)"
              style={{ flex: 1, minWidth: 200 }}
            />
            <button
              type="button"
              className="btn-secondary"
              disabled={testEmailSending}
              onClick={async () => {
                setTestEmailSending(true)
                setTestEmailResult(null)
                try {
                  const r = await settingsApi.sendTestEmail(testEmailAddr || undefined)
                  setTestEmailResult({ ok: true, msg: r.message })
                } catch (err) {
                  setTestEmailResult({ ok: false, msg: err instanceof Error ? err.message : 'Fehler' })
                } finally {
                  setTestEmailSending(false)
                }
              }}
            >
              {testEmailSending ? 'Wird gesendet…' : 'Test-E-Mail senden'}
            </button>
          </div>
          {testEmailResult && (
            <p style={{ margin: '0.4rem 0 0 0', fontSize: '0.85rem', color: testEmailResult.ok ? 'var(--color-success)' : 'var(--color-error)' }}>
              {testEmailResult.msg}
            </p>
          )}
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
        <div className="form-group" style={{ marginTop: '0.75rem' }}>
          <label htmlFor="termin_marktplatz_webhook_base_url">Webhook-Basis-URL *</label>
          <input
            id="termin_marktplatz_webhook_base_url"
            type="text"
            value={form.termin_marktplatz_webhook_base_url}
            onChange={(e) => setForm((f) => ({ ...f, termin_marktplatz_webhook_base_url: e.target.value }))}
            placeholder="z.B. https://abc123.ngrok-free.dev"
          />
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            Nur Basis-URL ohne Pfad, z.B. <code>https://abc123.ngrok-free.dev</code>. <strong>Kein</strong> <code>/api/...</code> anhängen – das wird automatisch ergänzt.
          </p>
        </div>
        <div className="form-group" style={{ marginTop: '0.75rem' }}>
          <label htmlFor="termin_marktplatz_cancel_callback_url">Storno-Callback-URL</label>
          <input
            id="termin_marktplatz_cancel_callback_url"
            type="url"
            value={form.termin_marktplatz_cancel_callback_url}
            onChange={(e) => setForm((f) => ({ ...f, termin_marktplatz_cancel_callback_url: e.target.value }))}
            placeholder="z.B. https://api.terminmarktplatz.de/v1/bookings/cancel"
          />
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
            URL von Terminmarktplatz, an die WareVision Stornierungen meldet. Der API-Schlüssel wird im Header X-API-Key mitgesendet. Der Kunde erhält dann die Stornierungsmail von Terminmarktplatz.
          </p>
        </div>
        {(form.termin_marktplatz_api_key || terminMarktplatzConfigured) && (() => {
          const base = form.termin_marktplatz_webhook_base_url || (typeof window !== 'undefined' ? window.location.origin : '')
          const origin = base ? (() => {
            try {
              const u = new URL(base)
              return `${u.protocol}//${u.host}`
            } catch {
              return base.replace(/\/+$/, '')
            }
          })() : ''
          const webhookUrl = origin ? `${origin}/api/v1/appointments/webhook/termin-marktplatz` : ''
          return (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'var(--color-bg-secondary)', borderRadius: 6, fontSize: '0.85rem' }}>
            <strong>Webhook-URL für Terminmarktplatz:</strong>
            <code style={{ display: 'block', marginTop: '0.5rem', wordBreak: 'break-all' }}>
              {webhookUrl || '(Webhook-Basis-URL eintragen)'}
            </code>
            <p style={{ margin: '0.5rem 0 0 0', color: 'var(--color-text-muted)' }}>
              Diese URL in Terminmarktplatz hinterlegen. Header: <code>X-API-Key: [dein Schlüssel]</code> und bei ngrok: <code>ngrok-skip-browser-warning: 1</code>
            </p>
            {typeof window !== 'undefined' && (!form.termin_marktplatz_webhook_base_url || /localhost|127\.0\.0\.1/i.test(form.termin_marktplatz_webhook_base_url || window.location.origin)) && (
              <p style={{ margin: '0.5rem 0 0 0', color: 'var(--color-accent)', fontWeight: 500 }}>
                Hinweis: localhost/127.0.0.1 ist von Terminmarktplatz nicht erreichbar. Webhook-Basis-URL mit öffentlicher Adresse (z.B. ngrok) eintragen.
              </p>
            )}
          </div>
          )
        })()}
        {error && <p className="error">{error}</p>}
        {success && <p className="success">Einstellungen gespeichert.</p>}
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? 'Speichern…' : 'Speichern'}
        </button>
      </form>

      {isManager(user) && <SystemStatusPanel />}
      {isManager(user) && <TasksPanel />}
    </div>
  )
}

function SystemStatusPanel() {
  const [health, setHealth] = useState<{ status: string; checks: Record<string, string>; timestamp: string } | null>(null)
  const [checking, setChecking] = useState(false)

  const check = async () => {
    setChecking(true)
    try {
      const h = await healthApi.check()
      setHealth(h)
    } catch {
      setHealth({ status: 'error', checks: { api: 'nicht erreichbar' }, timestamp: new Date().toISOString() })
    } finally {
      setChecking(false)
    }
  }

  const statusColor = (s: string) =>
    s === 'ok' ? 'var(--color-success, #27ae60)' : s === 'degraded' ? '#e67e22' : 'var(--color-error)'

  return (
    <div className="card form-card" style={{ maxWidth: 600, marginTop: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem' }}>System-Status</h3>
        <button type="button" className="btn-secondary btn-sm" onClick={check} disabled={checking}>
          {checking ? 'Prüfe…' : 'Jetzt prüfen'}
        </button>
      </div>
      {health ? (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '1.1rem', color: statusColor(health.status) }}>●</span>
            <strong style={{ color: statusColor(health.status) }}>
              {health.status === 'ok' ? 'Alles in Ordnung' : health.status === 'degraded' ? 'Eingeschränkt' : 'Fehler'}
            </strong>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
              {new Date(health.timestamp).toLocaleString('de-DE')}
            </span>
          </div>
          <table style={{ width: '100%', fontSize: '0.85rem', borderCollapse: 'collapse' }}>
            <tbody>
              {Object.entries(health.checks).map(([key, val]) => (
                <tr key={key}>
                  <td style={{ padding: '3px 8px 3px 0', fontWeight: 500, textTransform: 'capitalize' }}>{key}</td>
                  <td style={{ padding: '3px 0', color: val === 'ok' ? statusColor('ok') : statusColor('error') }}>{val}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', margin: 0 }}>
          Klicken Sie auf „Jetzt prüfen" um DB- und Redis-Verbindung zu testen.
        </p>
      )}
    </div>
  )
}

function TasksPanel() {
  const [tasks, setTasks] = useState<any[]>([])
  const [runningId, setRunningId] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, { status: string; result?: any; error?: string }>>({})
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    tasksApi.list()
      .then(setTasks)
      .catch(() => setLoadError('Aufgaben konnten nicht geladen werden (Redis läuft möglicherweise nicht).'))
  }, [])

  const handleRun = async (taskName: string) => {
    setRunningId(taskName)
    try {
      const { task_id } = await tasksApi.run(taskName)
      setResults((r) => ({ ...r, [taskName]: { status: 'Gestartet...' } }))
      // Status bis zu 30s pollen
      let attempts = 0
      const poll = async () => {
        try {
          const s = await tasksApi.status(task_id)
          if (s.status === 'SUCCESS') {
            setResults((r) => ({ ...r, [taskName]: { status: 'Erfolgreich', result: s.result } }))
          } else if (s.status === 'FAILURE') {
            setResults((r) => ({ ...r, [taskName]: { status: 'Fehler', error: s.error } }))
          } else if (attempts < 15) {
            attempts++
            setTimeout(poll, 2000)
            return
          } else {
            setResults((r) => ({ ...r, [taskName]: { status: s.status } }))
          }
        } catch {
          setResults((r) => ({ ...r, [taskName]: { status: 'Status nicht abrufbar' } }))
        }
        setRunningId(null)
      }
      setTimeout(poll, 1500)
    } catch (err) {
      setResults((r) => ({ ...r, [taskName]: { status: 'Fehler beim Starten', error: err instanceof Error ? err.message : String(err) } }))
      setRunningId(null)
    }
  }

  return (
    <div className="card form-card" style={{ maxWidth: 600, marginTop: '2rem' }}>
      <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem' }}>Hintergrundaufgaben</h3>
      {loadError ? (
        <p className="error">{loadError}</p>
      ) : tasks.length === 0 ? (
        <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>Keine Aufgaben gefunden.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {tasks.map((task) => {
            const res = results[task.name]
            return (
              <div key={task.name} style={{ padding: '0.75rem', background: 'var(--color-bg)', borderRadius: 6, border: '1px solid var(--color-border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                  <div>
                    <strong style={{ fontSize: '0.9rem' }}>{task.label}</strong>
                    <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{task.description}</p>
                    <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Automatisch: {task.schedule}</p>
                  </div>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => handleRun(task.name)}
                    disabled={runningId === task.name}
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    {runningId === task.name ? 'Läuft...' : 'Jetzt ausführen'}
                  </button>
                </div>
                {res && (
                  <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', padding: '0.4rem 0.6rem', borderRadius: 4, background: res.error ? '#ffeaea' : '#e8f5e9', color: '#1a1a1a' }}>
                    <strong>Status:</strong> {res.status}
                    {res.result && (
                      <span style={{ marginLeft: '0.5rem' }}>
                        {Object.entries(res.result).filter(([k]) => k !== 'task' && k !== 'date').map(([k, v]) => `${k}: ${v}`).join(' · ')}
                      </span>
                    )}
                    {res.error && <span style={{ marginLeft: '0.5rem', color: '#c0392b' }}>{res.error}</span>}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
