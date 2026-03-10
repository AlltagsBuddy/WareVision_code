import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export default function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const nav = [
    { path: '/', label: 'Dashboard' },
    { path: '/customers', label: 'Kunden' },
    { path: '/vehicles', label: 'Fahrzeuge' },
    { path: '/articles', label: 'Artikel' },
    { path: '/stock', label: 'Lager' },
  ]

  return (
    <div className="layout">
      <header className="header">
        <Link to="/" className="logo">WareVision</Link>
        <nav className="nav">
          {nav.map(({ path, label }) => (
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
          <button type="button" onClick={logout} className="btn-logout">
            Abmelden
          </button>
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
