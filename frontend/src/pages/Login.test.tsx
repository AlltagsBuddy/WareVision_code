/**
 * Tests für die Login-Seite.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Login from './Login'

// useAuth mocken
const mockLogin = vi.fn()
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    user: null,
    token: null,
    loading: false,
  }),
}))

// useNavigate mocken
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderLogin(path = '/login') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Login />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Login – Rendering', () => {
  it('zeigt E-Mail- und Passwort-Feld', () => {
    renderLogin()
    expect(screen.getByLabelText('E-Mail')).toBeInTheDocument()
    expect(screen.getByLabelText('Passwort')).toBeInTheDocument()
  })

  it('zeigt Anmelden-Button', () => {
    renderLogin()
    expect(screen.getByRole('button', { name: 'Anmelden' })).toBeInTheDocument()
  })

  it('zeigt Link zur Registrierung', () => {
    renderLogin()
    expect(screen.getByText(/Konto anlegen/i)).toBeInTheDocument()
  })

  it('füllt E-Mail-Feld aus Query-Parameter vor', () => {
    renderLogin('/login?email=max%40test.de')
    expect((screen.getByLabelText('E-Mail') as HTMLInputElement).value).toBe('max@test.de')
  })
})

describe('Login – Formular-Interaktion', () => {
  it('erlaubt Eingabe in E-Mail und Passwort', () => {
    renderLogin()
    const emailInput = screen.getByLabelText('E-Mail') as HTMLInputElement
    const passwordInput = screen.getByLabelText('Passwort') as HTMLInputElement

    fireEvent.change(emailInput, { target: { value: 'test@example.de' } })
    fireEvent.change(passwordInput, { target: { value: 'geheim' } })

    expect(emailInput.value).toBe('test@example.de')
    expect(passwordInput.value).toBe('geheim')
  })

  it('ruft login() mit E-Mail und Passwort auf', async () => {
    mockLogin.mockResolvedValueOnce(undefined)
    renderLogin()

    fireEvent.change(screen.getByLabelText('E-Mail'), { target: { value: 'user@test.de' } })
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'passwort123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }))

    await waitFor(() => expect(mockLogin).toHaveBeenCalledWith('user@test.de', 'passwort123'))
  })

  it('navigiert nach / nach erfolgreichem Login', async () => {
    mockLogin.mockResolvedValueOnce(undefined)
    renderLogin()

    fireEvent.change(screen.getByLabelText('E-Mail'), { target: { value: 'admin@test.de' } })
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'passwort' } })
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }))

    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/'))
  })
})

describe('Login – Fehlerzustände', () => {
  it('zeigt Fehlermeldung bei fehlgeschlagenem Login', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Ungültige Zugangsdaten'))
    renderLogin()

    fireEvent.change(screen.getByLabelText('E-Mail'), { target: { value: 'x@x.de' } })
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'falsch' } })
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }))

    await waitFor(() =>
      expect(screen.getByText('Ungültige Zugangsdaten')).toBeInTheDocument()
    )
  })

  it('deaktiviert Button während des Ladens', async () => {
    let resolve: () => void
    mockLogin.mockReturnValueOnce(new Promise<void>(r => { resolve = r }))
    renderLogin()

    fireEvent.change(screen.getByLabelText('E-Mail'), { target: { value: 'a@b.de' } })
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Anmelden...' })).toBeDisabled()
    )
    resolve!()
  })

  it('zeigt keine Fehlermeldung im Normalzustand', () => {
    renderLogin()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
