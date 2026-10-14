import { useEffect, useState } from 'react'
import { archiveApi } from '../api/client'

/**
 * Belegarchiv (GoBD): zeigt, ob alle ausgegebenen Belege als unveränderbares Original gesichert sind,
 * zieht fehlende Originale nach und prüft die Prüfsummen.
 */
const LABELS: Record<string, string> = {
  invoices: 'Rechnungen / Storno / Korrekturen',
  reminders: 'Mahnbriefe',
  quotes: 'Angebote',
  purchase_orders: 'Bestellungen',
}

export default function ArchivePanel() {
  const [status, setStatus] = useState<any | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [problems, setProblems] = useState<string[]>([])

  const load = () => archiveApi.status().then(setStatus).catch((e) => setMessage({ type: 'error', text: e instanceof Error ? e.message : 'Status konnte nicht geladen werden' }))

  useEffect(() => {
    load()
  }, [])

  const backfill = async () => {
    setBusy(true)
    setMessage(null)
    try {
      const res = await archiveApi.backfill()
      setStatus(res.status)
      const total = Object.values(res.created as Record<string, number>).reduce((a, b) => a + b, 0)
      const hints = (res.hints || []).length ? ` Hinweise: ${res.hints.join(' · ')}` : ''
      setMessage({ type: 'success', text: `${total} Beleg(e) nachträglich archiviert.${hints}` })
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : 'Nachziehen fehlgeschlagen' })
    } finally {
      setBusy(false)
    }
  }

  const verify = async () => {
    setBusy(true)
    setMessage(null)
    try {
      const res = await archiveApi.verify()
      setProblems(res.problems)
      setMessage(res.problems.length
        ? { type: 'error', text: `${res.problems.length} von ${res.checked} Archivdateien fehlen oder wurden verändert!` }
        : { type: 'success', text: `Alle ${res.checked} Archivdateien sind vollständig und unverändert.` })
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : 'Prüfung fehlgeschlagen' })
    } finally {
      setBusy(false)
    }
  }

  const missing: Record<string, number> = status?.missing || {}

  return (
    <div className="card form-card" style={{ maxWidth: 780, marginTop: '1.5rem' }}>
      <h3 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '1rem' }}>Belegarchiv (GoBD)</h3>
      <p className="muted" style={{ marginTop: 0, fontSize: '0.88rem' }}>
        Ausgestellte Rechnungen, Storno- und Korrekturbelege, Mahnbriefe sowie versendete Angebote und Bestellungen werden beim Ausgeben
        einmalig als Original gespeichert und mit einer Prüfsumme gesichert. Danach wird immer genau dieses Original angezeigt und versendet –
        auch wenn sich Firmen- oder Kundendaten später ändern.
      </p>
      {status && (
        <div style={{ fontSize: '0.9rem' }}>
          <div>Archivierte Originale: <strong>{status.archived_documents}</strong>
            {status.backfilled_documents > 0 && <span className="muted"> (davon {status.backfilled_documents} nachträglich erzeugt)</span>}
          </div>
          {status.missing_total > 0 ? (
            <div className="warning" style={{ marginTop: '0.4rem' }}>
              <strong>{status.missing_total} ausgegebene Belege ohne Original:</strong>
              <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.2rem' }}>
                {Object.entries(missing).filter(([, n]) => n > 0).map(([k, n]) => <li key={k}>{LABELS[k] || k}: {n}</li>)}
              </ul>
              <div style={{ marginTop: '0.3rem' }}>
                Das betrifft Belege von vor dem Update. Bitte einmalig „Fehlende Originale erzeugen“ klicken – am besten, bevor Firmen- oder Kundendaten geändert werden.
              </div>
            </div>
          ) : (
            <div style={{ marginTop: '0.4rem' }}>✓ Alle ausgegebenen Belege sind archiviert.</div>
          )}
        </div>
      )}
      {message && <p className={message.type === 'success' ? 'success' : 'error'}>{message.text}</p>}
      {problems.length > 0 && (
        <ul className="error" style={{ fontSize: '0.85rem' }}>
          {problems.map((p) => <li key={p}>{p}</li>)}
        </ul>
      )}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
        {status?.missing_total > 0 && (
          <button type="button" className="btn-primary" disabled={busy} onClick={backfill}>Fehlende Originale erzeugen</button>
        )}
        <button type="button" className="btn-secondary" disabled={busy} onClick={verify}>Archiv prüfen</button>
      </div>
    </div>
  )
}
