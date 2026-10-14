import { useEffect, useRef, useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { authApi } from '../api/client'
import Logo from './Logo'

interface NavItem {
  path: string
  label: string
  show: boolean
}

interface NavGroup {
  title?: string
  items: NavItem[]
}

/** Aktiver Menüpunkt: exakter Pfad oder Unterseite (außer Dashboard „/“) */
const isActivePath = (current: string, path: string) =>
  path === '/' ? current === '/' : current === path || current.startsWith(path + '/')

export default function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [pwForm, setPwForm] = useState({ current: '', new: '', confirm: '' })
  const [pwError, setPwError] = useState('')
  const [pwSubmitting, setPwSubmitting] = useState(false)

  const isAdmin = user?.role_name === 'admin'
  const perm = (module: string) =>
    isAdmin || user?.permissions?.[module]?.visible !== false

  const groups: NavGroup[] = [
    { items: [{ path: '/', label: 'Dashboard', show: true }] },
    {
      title: 'Werkstatt',
      items: [
        { path: '/appointments', label: 'Terminplaner', show: perm('appointments') },
        { path: '/workshop-orders', label: 'Werkstattaufträge', show: perm('workshop_orders') },
        { path: '/quotes', label: 'Angebote', show: perm('quotes') },
        { path: '/maintenance-plans', label: 'Wartungspläne', show: perm('maintenance_plans') },
      ],
    },
    {
      title: 'Kunden',
      items: [
        { path: '/customers', label: 'Kunden', show: perm('customers') },
        { path: '/vehicles', label: 'Fahrzeuge', show: perm('vehicles') },
      ],
    },
    {
      title: 'Lager & Einkauf',
      items: [
        { path: '/articles', label: 'Artikel', show: perm('articles') },
        { path: '/stock', label: 'Lager', show: perm('stock') },
        { path: '/purchase-orders', label: 'Bestellungen', show: perm('purchase_orders') },
        { path: '/suppliers', label: 'Lieferanten', show: perm('suppliers') },
        { path: '/stock-counts', label: 'Inventur', show: perm('stock_counts') },
      ],
    },
    {
      title: 'Finanzen',
      items: [
        { path: '/invoices', label: 'Rechnungen', show: perm('invoices') },
        { path: '/accounting', label: 'Buchhaltung', show: isAdmin },
      ],
    },
    {
      title: 'Ablage',
      items: [{ path: '/documents', label: 'Dokumente', show: perm('documents') }],
    },
    {
      title: 'Verwaltung',
      items: [
        { path: '/users', label: 'Benutzer', show: isAdmin },
        { path: '/settings', label: 'Einstellungen', show: isAdmin },
        { path: '/audit-logs', label: 'Audit-Log', show: isAdmin },
      ],
    },
  ]
    .map((g) => ({ ...g, items: g.items.filter((i) => i.show) }))
    .filter((g) => g.items.length > 0)

  // Menüs bei Seitenwechsel schließen
  useEffect(() => {
    setNavOpen(false)
    setUserMenuOpen(false)
  }, [location.pathname])

  // Konto-Menü: Klick außerhalb oder Escape schließt es
  useEffect(() => {
    if (!userMenuOpen) return
    const onClick = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) setUserMenuOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setUserMenuOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [userMenuOpen])

  const exportMyData = async () => {
    setUserMenuOpen(false)
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
  }

  const fullName = `${user?.first_name ?? ''} ${user?.last_name ?? ''}`.trim()
  const initials = (`${user?.first_name?.[0] ?? ''}${user?.last_name?.[0] ?? ''}`.toUpperCase()) || '?'

  const link = ({ path, label }: NavItem) => {
    const active = isActivePath(location.pathname, path)
    return (
      <Link key={path} to={path} className={active ? 'side-link active' : 'side-link'} aria-current={active ? 'page' : undefined}>
        {label}
      </Link>
    )
  }

  return (
    <div className={`layout ${navOpen ? 'nav-open' : ''}`}>
      <aside className="sidebar" aria-label="Hauptmenü">
        <Link to="/" className="sidebar-logo">
          <Logo size="header" />
        </Link>
        <nav className="sidebar-nav">
          {groups.map((g, i) => (
            <div key={g.title ?? i} className="side-group">
              {g.title && <div className="side-group-title">{g.title}</div>}
              {g.items.map(link)}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          {link({ path: '/help', label: '? Hilfe', show: true })}
        </div>
      </aside>
      {navOpen && <div className="sidebar-backdrop" onClick={() => setNavOpen(false)} aria-hidden="true" />}

      <div className="content">
        <header className="topbar">
          <button
            type="button"
            className="nav-toggle"
            onClick={() => setNavOpen((o) => !o)}
            aria-label="Menü"
            aria-expanded={navOpen}
          >
            {navOpen ? '✕' : '☰'}
          </button>
          <Link to="/" className="topbar-logo">
            <Logo size="header" />
          </Link>
          <div className="account" ref={userMenuRef}>
            <button
              type="button"
              className="account-button"
              onClick={() => setUserMenuOpen((o) => !o)}
              aria-haspopup="menu"
              aria-expanded={userMenuOpen}
            >
              <span className="account-avatar" aria-hidden="true">{initials}</span>
              <span className="account-name">{fullName}</span>
              <span aria-hidden="true">▾</span>
            </button>
            {userMenuOpen && (
              <div className="account-menu" role="menu">
                <div className="account-menu-head">
                  <strong>{fullName}</strong>
                  {user?.email && <span>{user.email}</span>}
                </div>
                <button type="button" role="menuitem" onClick={exportMyData}>Meine Daten exportieren</button>
                <button type="button" role="menuitem" onClick={() => { setUserMenuOpen(false); setShowPasswordModal(true) }}>
                  Passwort ändern
                </button>
                <button type="button" role="menuitem" className="account-logout" onClick={logout}>Abmelden</button>
              </div>
            )}
          </div>
        </header>
        <main className="main">
          <Outlet />
        </main>
      </div>

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
