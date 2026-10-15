import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../api/client'
import Logo from '../components/Logo'

export default function Register() {
  const [form, setForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    password_confirm: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.password_confirm) {
      setError('Passwörter stimmen nicht überein.')
      return
    }
    if (form.password.length < 10) {
      setError('Passwort muss mindestens 10 Zeichen haben.')
      return
    }
    setLoading(true)
    try {
      await authApi.register({
        email: form.email.trim(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        password: form.password,
      })
      setSuccess(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registrierung fehlgeschlagen')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="login-page">
        <div className="login-card">
          <Logo size="auth" />
          <p className="subtitle">Registrierung erfolgreich</p>
          <p style={{ marginBottom: '1rem' }}>
            Ihr Konto wurde angelegt. Ein Administrator muss es noch freischalten, bevor Sie sich anmelden können.
          </p>
          <Link to="/login" className="btn-primary" style={{ display: 'block', textAlign: 'center' }}>Zur Anmeldung</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <Logo size="auth" />
        <p className="subtitle">Konto anlegen</p>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">E-Mail *</label>
            <input
              id="email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
              autoFocus
              placeholder="name@beispiel.de"
            />
          </div>
          <div className="form-row" style={{ display: 'flex', gap: '1rem' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label htmlFor="first_name">Vorname *</label>
              <input
                id="first_name"
                type="text"
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                required
              />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label htmlFor="last_name">Nachname *</label>
              <input
                id="last_name"
                type="text"
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                required
              />
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="password">Passwort *</label>
            <input
              id="password"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              minLength={10}
              placeholder="Mind. 10 Zeichen"
            />
          </div>
          <div className="form-group">
            <label htmlFor="password_confirm">Passwort bestätigen *</label>
            <input
              id="password_confirm"
              type="password"
              value={form.password_confirm}
              onChange={(e) => setForm({ ...form, password_confirm: e.target.value })}
              required
            />
          </div>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Wird angelegt...' : 'Konto anlegen'}
          </button>
        </form>
        <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
          Bereits ein Konto? <Link to="/login">Anmelden</Link>
        </p>
      </div>
    </div>
  )
}
