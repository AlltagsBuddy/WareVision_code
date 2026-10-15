import { useEffect, useRef, useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { authApi } from '../api/client'
import Logo from './Logo'
import TwoFactorModal from './TwoFactorModal'
import { canView, hasRight, isManager } from '../utils/permissions'

interface NavItem {
  path: string
  label: string
  show: boolean
}

interface NavGroup {
  title?: string
  icon?: IconName
  items: NavItem[]
}

type IconName = 'home' | 'wrench' | 'users' | 'box' | 'euro' | 'folder' | 'settings' | 'help'

/** Einfache Linien-Symbole (16 px) für die Seitenleiste */
function NavIcon({ name }: { name: IconName }) {
  const paths: Record<IconName, JSX.Element> = {
    home: <><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V21h14V9.5" /><path d="M10 21v-6h4v6" /></>,
    wrench: <path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z" />,
    users: <><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20c.6-3.6 3.3-5.5 6.5-5.5s5.9 1.9 6.5 5.5" /><path d="M16 4.7a3.5 3.5 0 0 1 0 6.6" /><path d="M18.5 14.8c1.7.8 2.7 2.5 3 5.2" /></>,
    box: <><path d="M3 7.5 12 3l9 4.5v9L12 21l-9-4.5z" /><path d="M3 7.5 12 12l9-4.5" /><path d="M12 12v9" /></>,
    euro: <><circle cx="12" cy="12" r="9" /><path d="M15.5 8.5a4.5 4.5 0 1 0 0 7" /><path d="M7.5 10.5h6M7.5 13.5h6" /></>,
    folder: <path d="M3 6.5A1.5 1.5 0 0 1 4.5 5H9l2 2.5h8.5A1.5 1.5 0 0 1 21 9v9.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z" />,
    settings: <><path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0" /><circle cx="16" cy="6" r="2" /><circle cx="10" cy="12" r="2" /><circle cx="18" cy="18" r="2" /></>,
    help: <><circle cx="12" cy="12" r="9" /><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6" /><path d="M12 17h.01" /></>,
  }
  return (
    <svg className="nav-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name]}
    </svg>
  )
}

/** Aktiver Menüpunkt: exakter Pfad oder Unterseite (außer Dashboard „/“) */
const isActivePath = (current: string, path: string) =>
  path === '/' ? current === '/' : current === path || current.startsWith(path + '/')

const COLLAPSE_KEY = 'warevision.nav.collapsed'
const isSmallScreen = () => typeof window !== 'undefined' && window.innerWidth <= 900

/** Gespeicherte zugeklappte Gruppen lesen (null = noch nie gespeichert) */
function loadCollapsed(): string[] | null {
  try {
    const raw = localStorage.getItem(COLLAPSE_KEY)
    const parsed = raw ? JSON.parse(raw) : null
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === 'string') : null
  } catch {
    return null
  }
}

function saveCollapsed(titles: string[]) {
  try {
    localStorage.setItem(COLLAPSE_KEY, JSON.stringify(titles))
  } catch {
    /* Speichern nicht möglich (z. B. privater Modus) – Menü funktioniert trotzdem */
  }
}

export default function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [showTwoFactor, setShowTwoFactor] = useState(false)
  const [pwForm, setPwForm] = useState({ current: '', new: '', confirm: '' })
  const [pwError, setPwError] = useState('')
  const [pwSubmitting, setPwSubmitting] = useState(false)

  const isAdmin = isManager(user)
  const perm = (module: string) => canView(user, module)

  const groups: NavGroup[] = ([
    { icon: 'home', items: [{ path: '/', label: 'Dashboard', show: true }] },
    {
      title: 'Werkstatt',
      icon: 'wrench',
      items: [
        { path: '/appointments', label: 'Terminplaner', show: perm('appointments') },
        { path: '/workshop-orders', label: 'Werkstattaufträge', show: perm('workshop_orders') },
        { path: '/quotes', label: 'Angebote', show: perm('quotes') },
        { path: '/maintenance-plans', label: 'Wartungspläne', show: perm('maintenance_plans') },
      ],
    },
    {
      title: 'Kunden',
      icon: 'users',
      items: [
        { path: '/customers', label: 'Kunden', show: perm('customers') },
        { path: '/vehicles', label: 'Fahrzeuge', show: perm('vehicles') },
      ],
    },
    {
      title: 'Lager & Einkauf',
      icon: 'box',
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
      icon: 'euro',
      items: [
        { path: '/invoices', label: 'Rechnungen', show: perm('invoices') },
        { path: '/accounting', label: 'Buchhaltung', show: hasRight(user, 'accounting') },
      ],
    },
    {
      title: 'Ablage',
      icon: 'folder',
      items: [{ path: '/documents', label: 'Dokumente', show: perm('documents') }],
    },
    {
      title: 'Verwaltung',
      icon: 'settings',
      items: [
        { path: '/users', label: 'Benutzer', show: isAdmin },
        { path: '/settings', label: 'Einstellungen', show: isAdmin },
        { path: '/audit-logs', label: 'Audit-Log', show: isAdmin },
      ],
    },
  ] as NavGroup[])
    .map((g) => ({ ...g, items: g.items.filter((i) => i.show) }))
    .filter((g) => g.items.length > 0)

  const activeGroup = groups.find((g) => g.title && g.items.some((i) => isActivePath(location.pathname, i.path)))?.title

  // Zugeklappte Gruppen: gespeicherte Wahl. Ohne gespeicherte Wahl: PC = alles offen,
  // Handy = nur die Gruppe der aktuellen Seite offen (wird bei jedem Seitenwechsel neu bestimmt).
  const [savedCollapsed, setSavedCollapsed] = useState<string[] | null>(() => loadCollapsed())
  const defaultCollapsed = () =>
    isSmallScreen() ? groups.filter((g) => g.title && g.title !== activeGroup).map((g) => g.title as string) : []
  const collapsed = savedCollapsed ?? defaultCollapsed()

  const toggleGroup = (title: string) => {
    const next = collapsed.includes(title) ? collapsed.filter((t) => t !== title) : [...collapsed, title]
    saveCollapsed(next)
    setSavedCollapsed(next)
  }

  // Die Gruppe der aktuellen Seite ist immer offen
  const isOpen = (title?: string) => !title || title === activeGroup || !collapsed.includes(title)

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

  const link = ({ path, label }: NavItem, icon?: IconName) => {
    const active = isActivePath(location.pathname, path)
    const cls = `${icon ? 'side-top' : 'side-link'}${active ? ' active' : ''}`
    return (
      <Link key={path} to={path} className={cls} aria-current={active ? 'page' : undefined}>
        {icon && <NavIcon name={icon} />}
        <span>{label}</span>
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
          {groups.map((g, i) => {
            const open = isOpen(g.title)
            const id = `nav-group-${i}`
            return (
              <div key={g.title ?? i} className={`side-group${g.title === activeGroup ? ' current' : ''}`}>
                {!g.title && g.items.map((item) => link(item, g.icon))}
                {g.title && (
                  <button
                    type="button"
                    className="side-group-title"
                    aria-expanded={open}
                    aria-controls={id}
                    disabled={g.title === activeGroup}
                    title={g.title === activeGroup ? 'Aktueller Bereich' : open ? 'Zuklappen' : 'Aufklappen'}
                    onClick={() => toggleGroup(g.title as string)}
                  >
                    {g.icon && <NavIcon name={g.icon} />}
                    <span className="side-group-label">{g.title}</span>
                    <svg className={`side-group-chevron${open ? ' open' : ''}`} width="14" height="14" viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="m9 6 6 6-6 6" />
                    </svg>
                  </button>
                )}
                {g.title && open && <div id={id} className="side-sub">{g.items.map((item) => link(item))}</div>}
              </div>
            )
          })}
        </nav>
        <div className="sidebar-footer">
          {link({ path: '/help', label: 'Hilfe', show: true }, 'help')}
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
                <button type="button" role="menuitem" onClick={() => { setUserMenuOpen(false); setShowTwoFactor(true) }}>
                  Zwei-Faktor-Anmeldung
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

      {showTwoFactor && <TwoFactorModal onClose={() => setShowTwoFactor(false)} />}

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
                if (pwForm.new.length < 10) {
                  setPwError('Neues Passwort muss mindestens 10 Zeichen haben.')
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
                  minLength={10}
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
