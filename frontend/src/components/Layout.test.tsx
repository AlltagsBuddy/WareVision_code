/**
 * Tests für die Seitenleiste (Gruppen, Rechte, aktive Seite) und das Konto-Menü.
 */
import { render, screen, fireEvent, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Layout from './Layout'

let user: any = null
const logout = vi.fn()
vi.mock('../hooks/useAuth', () => ({ useAuth: () => ({ user, logout }) }))
vi.mock('../api/client', () => ({ authApi: { exportMyData: vi.fn(), changePassword: vi.fn() } }))
vi.mock('./Logo', () => ({ default: () => <span>Logo</span> }))

const renderAt = (path: string) => render(<MemoryRouter initialEntries={[path]}><Layout /></MemoryRouter>)
const sidebar = () => screen.getByRole('complementary', { name: 'Hauptmenü' })

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  window.innerWidth = 1280
  user = { first_name: 'Annett', last_name: 'Schoner', email: 'a@test.de', role_name: 'admin', permissions: null }
})

describe('Seitenleiste', () => {
  it('zeigt Gruppen mit korrekt geschriebenen Einträgen', () => {
    renderAt('/')
    const nav = sidebar()
    for (const title of ['Werkstatt', 'Kunden', 'Lager & Einkauf', 'Finanzen', 'Ablage', 'Verwaltung']) {
      expect(within(nav).getAllByText(title).length).toBeGreaterThan(0)
    }
    expect(within(nav).getByText('Werkstattaufträge')).toBeInTheDocument()
    expect(within(nav).getByText('Wartungspläne')).toBeInTheDocument()
    expect(within(nav).getByText('Hilfe')).toBeInTheDocument()
  })

  it('markiert die aktive Seite (auch Unterseiten)', () => {
    renderAt('/invoices/123')
    const active = within(sidebar()).getByRole('link', { current: 'page' })
    expect(active).toHaveTextContent('Rechnungen')
  })

  it('Dashboard ist nur auf der Startseite aktiv', () => {
    renderAt('/customers')
    expect(within(sidebar()).getByText('Dashboard')).not.toHaveAttribute('aria-current')
  })

  it('Werkstatt-Benutzer sieht keine Verwaltung und keine Buchhaltung', () => {
    user = { ...user, role_name: 'werkstatt', permissions: { invoices: { visible: false, write: false } } }
    renderAt('/')
    const nav = sidebar()
    expect(within(nav).queryByText('Verwaltung')).not.toBeInTheDocument()
    expect(within(nav).queryByText('Buchhaltung')).not.toBeInTheDocument()
    expect(within(nav).queryByText('Rechnungen')).not.toBeInTheDocument()
    expect(within(nav).queryByText('Finanzen')).not.toBeInTheDocument()  // leere Gruppe ausgeblendet
    expect(within(nav).getByRole('link', { name: 'Kunden' })).toBeInTheDocument()
  })
})

describe('Zuklappbare Gruppen', () => {
  const groupButton = (name: string) => within(sidebar()).getByRole('button', { name: new RegExp(name) })

  it('PC: alles offen, Gruppe lässt sich zu- und aufklappen und wird gemerkt', () => {
    const { unmount } = renderAt('/')
    expect(within(sidebar()).getByText('Bestellungen')).toBeInTheDocument()
    fireEvent.click(groupButton('Lager & Einkauf'))
    expect(within(sidebar()).queryByText('Bestellungen')).not.toBeInTheDocument()
    expect(groupButton('Lager & Einkauf')).toHaveAttribute('aria-expanded', 'false')
    unmount()
    renderAt('/')                                     // neu laden: Einstellung bleibt
    expect(within(sidebar()).queryByText('Bestellungen')).not.toBeInTheDocument()
    fireEvent.click(groupButton('Lager & Einkauf'))
    expect(within(sidebar()).getByText('Bestellungen')).toBeInTheDocument()
  })

  it('Handy: nur die Gruppe der aktuellen Seite ist offen', () => {
    window.innerWidth = 390
    renderAt('/invoices')
    expect(within(sidebar()).getByText('Rechnungen')).toBeInTheDocument()
    expect(within(sidebar()).queryByText('Bestellungen')).not.toBeInTheDocument()
    expect(within(sidebar()).queryByText('Terminplaner')).not.toBeInTheDocument()
    expect(within(sidebar()).getByText('Dashboard')).toBeInTheDocument()   // ohne Gruppe immer sichtbar
  })

  it('Handy: Gruppen, die erst nach dem Laden des Benutzers erscheinen, sind ebenfalls zu', () => {
    window.innerWidth = 390
    user = null
    const ui = renderAt('/invoices')
    user = { first_name: 'Annett', last_name: 'Schoner', email: 'a@test.de', role_name: 'admin', permissions: null }
    ui.rerender(<MemoryRouter initialEntries={['/invoices']}><Layout /></MemoryRouter>)
    expect(within(sidebar()).getByRole('button', { name: /Verwaltung/ })).toHaveAttribute('aria-expanded', 'false')
    expect(within(sidebar()).queryByText('Benutzer')).not.toBeInTheDocument()
  })

  it('aktuelle Gruppe bleibt offen, auch wenn sie gespeichert zugeklappt war', () => {
    localStorage.setItem('warevision.nav.collapsed', JSON.stringify(['Finanzen']))
    renderAt('/invoices')
    expect(within(sidebar()).getByText('Rechnungen')).toBeInTheDocument()
    expect(groupButton('Finanzen')).toBeDisabled()
  })

  it('kaputter Speicherinhalt stört nicht', () => {
    localStorage.setItem('warevision.nav.collapsed', '{kaputt')
    renderAt('/')
    expect(within(sidebar()).getByText('Bestellungen')).toBeInTheDocument()
  })
})

describe('Konto-Menü', () => {
  it('öffnet sich per Klick und schließt mit Escape', () => {
    renderAt('/')
    expect(screen.queryByText('Abmelden')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Annett Schoner/ }))
    expect(screen.getByRole('menu')).toHaveTextContent('a@test.de')
    expect(screen.getByRole('menuitem', { name: 'Passwort ändern' })).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })

  it('Abmelden ruft logout auf', () => {
    renderAt('/')
    fireEvent.click(screen.getByRole('button', { name: /Annett Schoner/ }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Abmelden' }))
    expect(logout).toHaveBeenCalled()
  })

  it('Passwort ändern öffnet den Dialog', () => {
    renderAt('/')
    fireEvent.click(screen.getByRole('button', { name: /Annett Schoner/ }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Passwort ändern' }))
    expect(screen.getByText('Aktuelles Passwort')).toBeInTheDocument()
  })
})
