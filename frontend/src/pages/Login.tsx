import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { authApi } from '../api/client'
import Logo from '../components/Logo'

type Step =
  | { kind: 'password' }
  | { kind: 'code'; challenge: string }
  | { kind: 'setup'; challenge: string; qr?: string; secret?: string; account?: string }
  | { kind: 'recovery'; codes: string[]; token: string }

export default function Login() {
  const [searchParams] = useSearchParams()
  const [email, setEmail] = useState(searchParams.get('email') ?? '')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [useRecovery, setUseRecovery] = useState(false)
  const [step, setStep] = useState<Step>({ kind: 'password' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const { login, completeLogin } = useAuth()
  const navigate = useNavigate()

  const fail = (err: unknown, fallback: string) => {
    const msg = err instanceof Error ? err.message : fallback
    setError(msg)
    // Zwischenschritt abgelaufen → zurück zur Passworteingabe
    if (/abgelaufen – bitte erneut/.test(msg)) {
      setStep({ kind: 'password' })
      setCode('')
    }
  }

  const handlePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login(email, password)
      if (res.step === 'ok') {
        navigate('/')
      } else if (res.step === '2fa') {
        setPassword('')
        setStep({ kind: 'code', challenge: res.challenge })
      } else {
        setPassword('')
        const info = await authApi.startTwoFactorSetup(res.challenge)
        setStep({ kind: 'setup', challenge: res.challenge, qr: info.qr_data_uri, secret: info.secret, account: info.account })
      }
    } catch (err: unknown) {
      fail(err, 'Login fehlgeschlagen')
    } finally {
      setLoading(false)
    }
  }

  const handleCode = async (e: React.FormEvent) => {
    e.preventDefault()
    if (step.kind !== 'code') return
    setError('')
    setLoading(true)
    try {
      const res = await authApi.verifyTwoFactor(step.challenge, useRecovery ? { recovery_code: code } : { code })
      if (!res.access_token) throw new Error('Anmeldung fehlgeschlagen')
      await completeLogin(res.access_token)
      navigate('/')
    } catch (err: unknown) {
      fail(err, 'Code ungültig')
      setCode('')
    } finally {
      setLoading(false)
    }
  }

  const handleSetup = async (e: React.FormEvent) => {
    e.preventDefault()
    if (step.kind !== 'setup') return
    setError('')
    setLoading(true)
    try {
      const res = await authApi.confirmTwoFactorSetup(step.challenge, code)
      setCode('')
      setStep({ kind: 'recovery', codes: res.recovery_codes, token: res.access_token })
    } catch (err: unknown) {
      fail(err, 'Code ungültig')
    } finally {
      setLoading(false)
    }
  }

  const finishRecovery = async () => {
    if (step.kind !== 'recovery') return
    setLoading(true)
    try {
      await completeLogin(step.token)
      navigate('/')
    } catch (err: unknown) {
      fail(err, 'Anmeldung fehlgeschlagen')
    } finally {
      setLoading(false)
    }
  }

  const recoveryText = step.kind === 'recovery'
    ? `WareVision – Wiederherstellungscodes für ${email}\nJeder Code funktioniert nur einmal.\n\n${step.codes.join('\n')}\n`
    : ''

  const copyCodes = async () => {
    try {
      await navigator.clipboard.writeText(recoveryText)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  const downloadCodes = () => {
    const url = URL.createObjectURL(new Blob([recoveryText], { type: 'text/plain' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'warevision-wiederherstellungscodes.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  const backToPassword = () => {
    setStep({ kind: 'password' })
    setCode('')
    setError('')
    setUseRecovery(false)
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <Logo size="auth" />
        <p className="subtitle">Warenwirtschafts- und Werkstattsystem</p>

        {step.kind === 'password' && (
          <>
            <form onSubmit={handlePassword}>
              <div className="form-group">
                <label htmlFor="email">E-Mail</label>
                <input
                  id="email"
                  type="text"
                  inputMode="email"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="name@firma.de"
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label htmlFor="password">Passwort</label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              {error && <p className="error">{error}</p>}
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Anmelden...' : 'Anmelden'}
              </button>
            </form>
            <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
              Noch kein Konto? <Link to="/register">Konto anlegen</Link>
            </p>
          </>
        )}

        {step.kind === 'code' && (
          <form onSubmit={handleCode}>
            <h2 style={{ fontSize: '1.1rem' }}>Bestätigungscode</h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
              {useRecovery
                ? 'Einen deiner Wiederherstellungscodes eingeben (jeder gilt nur einmal).'
                : 'Den 6-stelligen Code aus deiner Authenticator-App eingeben.'}
            </p>
            <div className="form-group">
              <label htmlFor="otp">{useRecovery ? 'Wiederherstellungscode' : 'Code'}</label>
              <input
                id="otp"
                type="text"
                inputMode={useRecovery ? 'text' : 'numeric'}
                autoComplete="one-time-code"
                maxLength={useRecovery ? 11 : 7}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                autoFocus
                style={{ fontSize: '1.4rem', letterSpacing: '0.2em', textAlign: 'center' }}
              />
            </div>
            {error && <p className="error">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Prüfen...' : 'Bestätigen'}
            </button>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem', fontSize: '0.85rem', gap: '1rem', flexWrap: 'wrap' }}>
              <button type="button" className="link-button" onClick={() => { setUseRecovery(!useRecovery); setCode(''); setError('') }}>
                {useRecovery ? 'Code aus der App verwenden' : 'Handy nicht zur Hand? Wiederherstellungscode'}
              </button>
              <button type="button" className="link-button" onClick={backToPassword}>Zurück</button>
            </div>
          </form>
        )}

        {step.kind === 'setup' && (
          <form onSubmit={handleSetup}>
            <h2 style={{ fontSize: '1.1rem' }}>Zwei-Faktor-Anmeldung einrichten</h2>
            <ol style={{ fontSize: '0.9rem', paddingLeft: '1.2rem', lineHeight: 1.5 }}>
              <li>Eine Authenticator-App auf dem Handy öffnen (z. B. Google Authenticator oder Microsoft Authenticator).</li>
              <li>Dort „Konto hinzufügen“ bzw. „+“ wählen und diesen QR-Code scannen.</li>
              <li>Den 6-stelligen Code aus der App hier eingeben.</li>
            </ol>
            {step.qr && (
              <img
                src={step.qr.startsWith('data:image/svg+xml') ? step.qr : ''}
                alt="QR-Code für die Authenticator-App"
                style={{ display: 'block', margin: '0.5rem auto', width: 200, height: 200, background: '#fff', borderRadius: 6 }}
              />
            )}
            {step.secret && (
              <details style={{ fontSize: '0.8rem', marginBottom: '0.75rem' }}>
                <summary>QR-Code lässt sich nicht scannen (z. B. am Handy selbst)?</summary>
                <p style={{ margin: '0.5rem 0 0' }}>In der App „Einrichtungsschlüssel eingeben“ wählen:</p>
                <p style={{ margin: '0.25rem 0' }}>Konto: {step.account}</p>
                <code style={{ wordBreak: 'break-all', userSelect: 'all' }}>{step.secret}</code>
              </details>
            )}
            <div className="form-group">
              <label htmlFor="setup-code">Code aus der App</label>
              <input
                id="setup-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={7}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                style={{ fontSize: '1.4rem', letterSpacing: '0.2em', textAlign: 'center' }}
              />
            </div>
            {error && <p className="error">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Prüfen...' : 'Einrichten'}
            </button>
            <p style={{ marginTop: '1rem', fontSize: '0.85rem' }}>
              <button type="button" className="link-button" onClick={backToPassword}>Abbrechen</button>
            </p>
          </form>
        )}

        {step.kind === 'recovery' && (
          <div>
            <h2 style={{ fontSize: '1.1rem' }}>Wiederherstellungscodes</h2>
            <p style={{ fontSize: '0.9rem' }}>
              Zwei-Faktor ist eingerichtet. Bitte diese Codes jetzt <strong>sicher aufbewahren</strong> (ausdrucken oder
              speichern). Mit einem Code kannst du dich anmelden, falls das Handy verloren geht. Jeder Code gilt nur einmal;
              sie werden nicht noch einmal angezeigt.
            </p>
            <ul className="recovery-codes" aria-label="Wiederherstellungscodes">
              {step.codes.map((c) => <li key={c}><code>{c}</code></li>)}
            </ul>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', margin: '0.75rem 0' }}>
              <button type="button" className="btn-secondary" onClick={copyCodes}>{copied ? 'Kopiert' : 'Kopieren'}</button>
              <button type="button" className="btn-secondary" onClick={downloadCodes}>Als Datei speichern</button>
              <button type="button" className="btn-secondary" onClick={() => window.print()}>Drucken</button>
            </div>
            {error && <p className="error">{error}</p>}
            <button type="button" className="btn-primary" disabled={loading} onClick={finishRecovery}>
              Ich habe die Codes gesichert – weiter
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
