import { useEffect, useState } from 'react'
import { accountingApi } from '../api/client'

/**
 * DATEV-Export: Einstellungen (Berater-/Mandantennummer, Kontenrahmen, Konten),
 * Vorschau mit Hinweisen und Download des ZIP (Buchungsstapel im DATEV-Format).
 */

interface Props {
  /** Liefert den auf der Seite gewählten Zeitraum (JJJJ-MM-TT) */
  getRange: () => { from: string; to: string }
}

const ACCOUNT_KEYS = ['revenue_19', 'revenue_7', 'revenue_0', 'expense_19', 'expense_7', 'expense_0'] as const
const MONTHS = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
const formatEuro = (v: number | string) => Number(v).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })

export default function DatevExport({ getRange }: Props) {
  const [settings, setSettings] = useState<any | null>(null)
  const [form, setForm] = useState<Record<string, string | boolean>>({})
  const [showSettings, setShowSettings] = useState(false)
  const [settingsMsg, setSettingsMsg] = useState<{ type: 'ok' | 'error'; text: string } | null>(null)
  const [includeIncoming, setIncludeIncoming] = useState(true)
  const [preview, setPreview] = useState<any | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const applySettings = (s: any) => {
    setSettings(s)
    const f: Record<string, string | boolean> = {
      consultant_number: s.consultant_number ? String(s.consultant_number) : '',
      client_number: s.client_number ? String(s.client_number) : '',
      chart: s.chart,
      account_length: String(s.account_length),
      fiscal_year_start_month: String(s.fiscal_year_start_month),
      debtor_start: s.debtor_start ? String(s.debtor_start) : '',
      creditor_start: s.creditor_start ? String(s.creditor_start) : '',
      lock_bookings: !!s.lock_bookings,
    }
    ACCOUNT_KEYS.forEach((k) => { f[k] = s[k] || '' })
    setForm(f)
  }

  useEffect(() => {
    accountingApi
      .datevSettings()
      .then((s) => {
        applySettings(s)
        if (s.problems?.length) setShowSettings(true)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'DATEV-Einstellungen konnten nicht geladen werden'))
  }, [])

  const num = (v: string | boolean) => (typeof v === 'string' && v.trim() ? parseInt(v, 10) : null)

  const saveSettings = async () => {
    setSettingsMsg(null)
    for (const key of ['consultant_number', 'client_number', 'debtor_start', 'creditor_start']) {
      const v = String(form[key] ?? '').trim()
      if (v && !/^\d+$/.test(v)) {
        setSettingsMsg({ type: 'error', text: 'Nummern bitte nur mit Ziffern eingeben.' })
        return
      }
    }
    try {
      const saved = await accountingApi.saveDatevSettings({
        consultant_number: num(form.consultant_number),
        client_number: num(form.client_number),
        chart: form.chart,
        account_length: num(form.account_length) ?? 4,
        fiscal_year_start_month: num(form.fiscal_year_start_month) ?? 1,
        debtor_start: num(form.debtor_start),
        creditor_start: num(form.creditor_start),
        lock_bookings: !!form.lock_bookings,
        ...Object.fromEntries(ACCOUNT_KEYS.map((k) => [k, String(form[k] ?? '').trim()])),
      })
      applySettings(saved)
      setSettingsMsg(saved.problems.length
        ? { type: 'error', text: 'Gespeichert, aber noch unvollständig – siehe Hinweise.' }
        : { type: 'ok', text: 'DATEV-Einstellungen gespeichert.' })
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Speichern fehlgeschlagen'
      setSettingsMsg({ type: 'error', text: msg.includes('9999999') || msg.includes('1001') ? 'Beraternummer muss zwischen 1001 und 9999999 liegen.' : msg })
    }
  }

  /** Beim Wechsel des Kontenrahmens die Kontenvorschläge übernehmen (nur bei 4-stelligen Sachkonten) */
  const changeChart = (chart: string) => {
    const defaults = settings?.default_accounts?.[chart]
    const f: Record<string, string | boolean> = { ...form, chart }
    if (defaults && String(form.account_length) === '4') ACCOUNT_KEYS.forEach((k) => { f[k] = defaults[k] })
    setForm(f)
  }

  const checkRange = () => {
    const { from, to } = getRange()
    if (!from || !to) {
      setError('Bitte oben einen Zeitraum wählen.')
      return null
    }
    return { from, to }
  }

  const runPreview = async () => {
    setError('')
    setPreview(null)
    const range = checkRange()
    if (!range) return
    setBusy(true)
    try {
      setPreview(await accountingApi.datevPreview(range.from, range.to, includeIncoming))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Vorschau fehlgeschlagen')
    } finally {
      setBusy(false)
    }
  }

  const runExport = async () => {
    setError('')
    const range = checkRange()
    if (!range) return
    setBusy(true)
    try {
      const blob = await accountingApi.datevExport(range.from, range.to, includeIncoming)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `DATEV_${range.from.replace(/-/g, '')}_${range.to.replace(/-/g, '')}.zip`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'DATEV-Export fehlgeschlagen')
    } finally {
      setBusy(false)
    }
  }

  const problems: string[] = settings?.problems || []
  const field = (key: string, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}) => (
    <div className="form-group" style={{ flex: '1 1 160px' }}>
      <label htmlFor={`datev-${key}`}>{label}</label>
      <input id={`datev-${key}`} value={String(form[key] ?? '')} onChange={(e) => setForm({ ...form, [key]: e.target.value })} {...props} />
    </div>
  )

  return (
    <div className="card form-card" style={{ maxWidth: 780, marginTop: '1.5rem' }}>
      <h3 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '1rem' }}>DATEV-Export (Buchungsstapel)</h3>
      <p className="muted" style={{ marginTop: 0, fontSize: '0.88rem' }}>
        Erzeugt Buchungsdateien im DATEV-Format für den gewählten Zeitraum, die dein Steuerberater direkt in DATEV einlesen kann:
        Ausgangsrechnungen (inkl. Storno und Rechnungskorrekturen), Eingangsrechnungen und die Stammdaten der Kunden- und Lieferantenkonten.
      </p>

      {problems.length > 0 && (
        <div className="error" style={{ fontSize: '0.88rem', marginBottom: '0.5rem' }}>
          <strong>Vor dem ersten Export bitte ergänzen:</strong>
          <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.2rem' }}>
            {problems.map((p) => <li key={p}>{p}</li>)}
          </ul>
        </div>
      )}

      <button type="button" className="btn-secondary btn-sm" onClick={() => setShowSettings(!showSettings)} aria-expanded={showSettings}>
        {showSettings ? 'DATEV-Einstellungen ausblenden' : 'DATEV-Einstellungen'}
      </button>

      {showSettings && settings && (
        <div style={{ marginTop: '0.75rem' }}>
          <p className="muted" style={{ fontSize: '0.85rem', marginTop: 0 }}>
            Diese Angaben bekommst du von deinem Steuerberater. Die Konten sind Vorschläge für den gewählten Kontenrahmen – bitte mit dem Steuerberater abstimmen.
          </p>
          <div className="form-row" style={{ flexWrap: 'wrap' }}>
            {field('consultant_number', 'Beraternummer', { inputMode: 'numeric', placeholder: 'z. B. 1234567' })}
            {field('client_number', 'Mandantennummer', { inputMode: 'numeric', placeholder: 'z. B. 10001' })}
            <div className="form-group" style={{ flex: '1 1 140px' }}>
              <label htmlFor="datev-chart">Kontenrahmen</label>
              <select id="datev-chart" value={String(form.chart)} onChange={(e) => changeChart(e.target.value)}>
                <option value="SKR03">SKR03</option>
                <option value="SKR04">SKR04</option>
              </select>
            </div>
          </div>
          <div className="form-row" style={{ flexWrap: 'wrap' }}>
            <div className="form-group" style={{ flex: '1 1 140px' }}>
              <label htmlFor="datev-account_length">Sachkontenlänge</label>
              <select id="datev-account_length" value={String(form.account_length)} onChange={(e) => setForm({ ...form, account_length: e.target.value })}>
                {[4, 5, 6, 7, 8].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ flex: '1 1 160px' }}>
              <label htmlFor="datev-fy">Wirtschaftsjahr beginnt im</label>
              <select id="datev-fy" value={String(form.fiscal_year_start_month)} onChange={(e) => setForm({ ...form, fiscal_year_start_month: e.target.value })}>
                {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
              </select>
            </div>
            {field('debtor_start', 'Erste Debitorennummer', { inputMode: 'numeric' })}
            {field('creditor_start', 'Erste Kreditorennummer', { inputMode: 'numeric' })}
          </div>
          <div className="form-row" style={{ flexWrap: 'wrap' }}>
            {ACCOUNT_KEYS.map((k) => field(k, settings.account_labels?.[k] || k, { inputMode: 'numeric' }))}
          </div>
          <label style={{ fontWeight: 400, display: 'block', margin: '0.25rem 0 0.75rem' }}>
            <input type="checkbox" checked={!!form.lock_bookings} onChange={(e) => setForm({ ...form, lock_bookings: e.target.checked })} />{' '}
            Buchungen beim Import festschreiben (nur nach Absprache mit dem Steuerberater)
          </label>
          {settingsMsg && <p className={settingsMsg.type === 'ok' ? 'success' : 'error'}>{settingsMsg.text}</p>}
          <button type="button" className="btn-primary btn-sm" onClick={saveSettings}>Einstellungen speichern</button>
        </div>
      )}

      <div style={{ marginTop: '1rem' }}>
        <label style={{ fontWeight: 400 }}>
          <input type="checkbox" checked={includeIncoming} onChange={(e) => { setIncludeIncoming(e.target.checked); setPreview(null) }} />{' '}
          Eingangsrechnungen mit exportieren
        </label>
      </div>

      {error && <p className="error">{error}</p>}

      {preview && (
        <div style={{ fontSize: '0.9rem', margin: '0.75rem 0' }}>
          <div>
            Ausgangsrechnungen: <strong>{preview.outgoing_documents}</strong> Belege, {preview.outgoing_bookings} Buchungen
            {' '}(Soll {formatEuro(preview.outgoing_debit)}, Haben {formatEuro(preview.outgoing_credit)})
          </div>
          {includeIncoming && (
            <div>
              Eingangsrechnungen: <strong>{preview.incoming_documents}</strong> Belege, {preview.incoming_bookings} Buchungen
              {' '}(Haben {formatEuro(preview.incoming_credit)}, Soll {formatEuro(preview.incoming_debit)})
            </div>
          )}
          {preview.new_accounts > 0 && <div>Neue Debitoren/Kreditoren: {preview.new_accounts} (werden beim Export dauerhaft vergeben)</div>}
          {preview.hints.length > 0 && (
            <div className="warning" style={{ marginTop: '0.4rem' }}>
              <strong>Nicht exportiert / bitte prüfen:</strong>
              <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.2rem' }}>
                {preview.hints.map((h: string) => <li key={h}>{h}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
        <button type="button" className="btn-secondary" disabled={busy || problems.length > 0} onClick={runPreview}>Vorschau</button>
        <button type="button" className="btn-primary" disabled={busy || problems.length > 0} onClick={runExport}>
          {busy ? 'Bitte warten…' : 'DATEV-Export herunterladen'}
        </button>
      </div>
    </div>
  )
}
