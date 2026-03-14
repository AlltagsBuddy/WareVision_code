import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { authApi } from '../api/client'

export default function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [pwForm, setPwForm] = useState({ current: '', new: '', confirm: '' })
  const [pwError, setPwError] = useState('')
  const [pwSubmitting, setPwSubmitting] = useState(false)

  const navItems = [
    { path: '/', label: 'Dashboard' },
    { path: '/customers', label: 'Kunden' },
    { path: '/vehicles', label: 'Fahrzeuge' },
    { path: '/articles', label: 'Artikel' },
    { path: '/stock', label: 'Lager' },
    { path: '/workshop-orders', label: 'Werkstattaufträge' },
    { path: '/maintenance-plans', label: 'Wartungspläne' },
    { path: '/appointments', label: 'Terminplaner' },
    { path: '/invoices', label: 'Rechnungen' },
    { path: '/documents', label: 'Dokumente' },
    ...(user?.role_name === 'admin'
      ? [
          { path: '/users', label: 'Benutzer' },
          { path: '/settings', label: 'Einstellungen' },
          { path: '/audit-logs', label: 'Audit-Log' },
        ]
      : []),
  ]

  return (
    <div className="layout">
      <header className="header">
        <button
          type="button"
          className="nav-toggle"
          onClick={() => setNavOpen((o) => !o)}
          aria-label="Menü"
        >
          {navOpen ? '✕' : '☰'}
        </button>
        <Link to="/" className="logo" onClick={() => setNavOpen(false)}>WareVision</Link>
        <nav className={`nav ${navOpen ? 'open' : ''}`} onClick={() => setNavOpen(false)}>
          {navItems.map(({ path, label }) => (
            <Link
              key={path}
              to={path}
              className={location.pathname === path ? 'nav-link active' : 'nav-link'}
            >
              {label}
            </Link>
          ))}
        </nav>
        <div className="user-menu">
          <span>{user?.first_name} {user?.last_name}</span>
          <button
            type="button"
            onClick={async () => {
              try {
                const data = await authApi.exportMyData()
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
                const a = document.createElement('a')
                a.href = URL.createObjectURL(blob)
                a.download = `Meine_Daten_${new Date().toISOString().slice(0, 10)}.json`
                a.click()
                URL.revokeObjectURL(a.href)
              } catch {
                alert('Export fehlgeschlagen')
              }
            }}
            className="btn-logout"
          >
            Meine Daten exportieren
          </button>
          <button type="button" onClick={() => setShowPasswordModal(true)} className="btn-logout">
            Passwort ändern
          </button>
          <button type="button" onClick={logout} className="btn-logout">
            Abmelden
          </button>
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>

      {showPasswordModal && (
        <div className="modal-overlay" onClick={() => setShowPasswordModal(false)}>
          <div className="modal card" onClick={(e) => e.stopPropagation()}>
            <h3>Passwort ändern</h3>
            <form
              onSubmit={async (e) => {
                e.preventDefault()
                setPwError('')
                if (pwForm.new !== pwForm.confirm) {
                  setPwError('Neues Passwort und Bestätigung stimmen nicht überein.')
                  return
                }
                if (pwForm.new.length < 6) {
                  setPwError('Neues Passwort muss mindestens 6 Zeichen haben.')
                  return
                }
                setPwSubmitting(true)
                try {
                  await authApi.changePassword(pwForm.current, pwForm.new)
                  setShowPasswordModal(false)
                  setPwForm({ current: '', new: '', confirm: '' })
                } catch (err) {
                  setPwError(err instanceof Error ? err.message : 'Fehler')
                } finally {
                  setPwSubmitting(false)
                }
              }}
            >
              <div className="form-group">
                <label>Aktuelles Passwort</label>
                <input
                  type="password"
                  value={pwForm.current}
                  onChange={(e) => setPwForm((f) => ({ ...f, current: e.target.value }))}
                  required
                />
              </div>
              <div className="form-group">
                <label>Neues Passwort</label>
                <input
                  type="password"
                  value={pwForm.new}
                  onChange={(e) => setPwForm((f) => ({ ...f, new: e.target.value }))}
                  required
                  minLength={6}
                />
              </div>
              <div className="form-group">
                <label>Neues Passwort bestätigen</label>
                <input
                  type="password"
                  value={pwForm.confirm}
                  onChange={(e) => setPwForm((f) => ({ ...f, confirm: e.target.value }))}
                  required
                />
              </div>
              {pwError && <p className="error">{pwError}</p>}
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                <button type="submit" className="btn btn-primary" disabled={pwSubmitting}>
                  {pwSubmitting ? 'Speichern…' : 'Speichern'}
                </button>
                <button type="button" className="btn" onClick={() => setShowPasswordModal(false)}>
                  Abbrechen
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
