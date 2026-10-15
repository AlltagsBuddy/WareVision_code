/**
 * Eigene Zwei-Faktor-Anmeldung: Status und neue Wiederherstellungscodes.
 */
import { useEffect, useState } from 'react'
import { authApi } from '../api/client'

type Status = { enabled: boolean; required: boolean; enabled_at: string | null; recovery_codes_left: number }

export default function TwoFactorModal({ onClose }: { onClose: () => void }) {
  const [status, setStatus] = useState<Status | null>(null)
  const [code, setCode] = useState('')
  const [codes, setCodes] = useState<string[] | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    authApi.twoFactorStatus().then(setStatus).catch((e) => setError(e instanceof Error ? e.message : 'Fehler'))
  }, [])

  const renew = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const fresh = await authApi.renewRecoveryCodes(code)
      setCodes(fresh)
      setCode('')
      setStatus((s) => (s ? { ...s, recovery_codes_left: fresh.length } : s))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setBusy(false)
    }
  }

  const download = () => {
    if (!codes) return
    const text = `WareVision – Wiederherstellungscodes\nJeder Code funktioniert nur einmal.\n\n${codes.join('\n')}\n`
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'warevision-wiederherstellungscodes.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal card" role="dialog" aria-label="Zwei-Faktor-Anmeldung" onClick={(e) => e.stopPropagation()}>
        <h3>Zwei-Faktor-Anmeldung</h3>
        {!status && !error && <p>Laden…</p>}
        {status && !status.enabled && (
          <p>
            Noch nicht eingerichtet.{' '}
            {status.required
              ? 'Die Einrichtung startet bei der nächsten Anmeldung automatisch.'
              : 'Sie ist auf diesem System nicht vorgeschrieben.'}
          </p>
        )}
        {status?.enabled && (
          <>
            <p>
              Eingerichtet{status.enabled_at ? ` am ${new Date(status.enabled_at).toLocaleDateString('de-DE')}` : ''}.
              Noch <strong>{status.recovery_codes_left}</strong> Wiederherstellungscode(s) übrig.
            </p>
            {codes ? (
              <>
                <p style={{ fontSize: '0.9rem' }}>Neue Codes – bitte jetzt sichern. Die alten gelten nicht mehr.</p>
                <ul className="recovery-codes" aria-label="Neue Wiederherstellungscodes">
                  {codes.map((c) => <li key={c}><code>{c}</code></li>)}
                </ul>
                <button type="button" className="btn-secondary" onClick={download}>Als Datei speichern</button>
              </>
            ) : (
              <form onSubmit={renew}>
                <div className="form-group">
                  <label htmlFor="renew-code">Neue Wiederherstellungscodes erstellen – aktuellen Code aus der App eingeben</label>
                  <input id="renew-code" inputMode="numeric" autoComplete="one-time-code" maxLength={7}
                    value={code} onChange={(e) => setCode(e.target.value)} required />
                </div>
                <button type="submit" className="btn-secondary" disabled={busy}>Neue Codes erstellen</button>
              </form>
            )}
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginTop: '1rem' }}>
              Neues Handy? Ein Admin kann die Zwei-Faktor-Anmeldung unter Benutzer zurücksetzen; danach richtest du sie
              bei der nächsten Anmeldung neu ein.
            </p>
          </>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        <div className="form-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>Schließen</button>
        </div>
      </div>
    </div>
  )
}
