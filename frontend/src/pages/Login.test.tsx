/**
 * Tests für die Login-Seite.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Login from './Login'

// useAuth mocken
const mockLogin = vi.fn()
const mockComplete = vi.fn()
vi.mock('../hooks/useAuth', () => ({
  useAuth: () => ({
    login: mockLogin,
    completeLogin: mockComplete,
    user: null,
    token: null,
    loading: false,
  }),
}))

const auth = { verifyTwoFactor: vi.fn(), startTwoFactorSetup: vi.fn(), confirmTwoFactorSetup: vi.fn() }
vi.mock('../api/client', () => ({
  authApi: new Proxy({}, { get: (_t, k: string) => (...a: unknown[]) => (auth as any)[k](...a) }),
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
    mockLogin.mockResolvedValueOnce({ step: 'ok' })
    renderLogin()

    fireEvent.change(screen.getByLabelText('E-Mail'), { target: { value: 'user@test.de' } })
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'passwort123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }))

    await waitFor(() => expect(mockLogin).toHaveBeenCalledWith('user@test.de', 'passwort123'))
  })

  it('navigiert nach / nach erfolgreichem Login', async () => {
    mockLogin.mockResolvedValueOnce({ step: 'ok' })
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
    let resolve: (v: unknown) => void
    mockLogin.mockReturnValueOnce(new Promise(r => { resolve = r }))
    renderLogin()

    fireEvent.change(screen.getByLabelText('E-Mail'), { target: { value: 'a@b.de' } })
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Anmelden...' })).toBeDisabled()
    )
    resolve!({ step: 'ok' })
  })

  it('zeigt keine Fehlermeldung im Normalzustand', () => {
    renderLogin()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('Login – Zwei-Faktor', () => {
  const submitPassword = () => {
    fireEvent.change(screen.getByLabelText('E-Mail'), { target: { value: 'chef@firma.de' } })
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'langespasswort' } })
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }))
  }

  it('fragt nach dem Code und meldet an', async () => {
    mockLogin.mockResolvedValueOnce({ step: '2fa', challenge: 'ch1' })
    auth.verifyTwoFactor.mockResolvedValueOnce({ access_token: 'tok' })
    renderLogin()
    submitPassword()
    fireEvent.change(await screen.findByLabelText('Code'), { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: 'Bestätigen' }))
    await waitFor(() => expect(auth.verifyTwoFactor).toHaveBeenCalledWith('ch1', { code: '123456' }))
    await waitFor(() => expect(mockComplete).toHaveBeenCalledWith('tok'))
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('falscher Code: Meldung, Eingabe bleibt möglich', async () => {
    mockLogin.mockResolvedValueOnce({ step: '2fa', challenge: 'ch1' })
    auth.verifyTwoFactor.mockRejectedValueOnce(new Error('Code ist falsch oder abgelaufen.'))
    renderLogin()
    submitPassword()
    fireEvent.change(await screen.findByLabelText('Code'), { target: { value: '000000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Bestätigen' }))
    expect(await screen.findByText('Code ist falsch oder abgelaufen.')).toBeInTheDocument()
    expect(screen.getByLabelText('Code')).toBeInTheDocument()
    expect(mockComplete).not.toHaveBeenCalled()
  })

  it('Wiederherstellungscode statt App-Code', async () => {
    mockLogin.mockResolvedValueOnce({ step: '2fa', challenge: 'ch1' })
    auth.verifyTwoFactor.mockResolvedValueOnce({ access_token: 'tok' })
    renderLogin()
    submitPassword()
    fireEvent.click(await screen.findByRole('button', { name: /Wiederherstellungscode/ }))
    fireEvent.change(screen.getByLabelText('Wiederherstellungscode'), { target: { value: 'ABCDE-FGHJK' } })
    fireEvent.click(screen.getByRole('button', { name: 'Bestätigen' }))
    await waitFor(() => expect(auth.verifyTwoFactor).toHaveBeenCalledWith('ch1', { recovery_code: 'ABCDE-FGHJK' }))
  })

  it('Einrichtung: QR-Code, Code bestätigen, Wiederherstellungscodes zeigen', async () => {
    mockLogin.mockResolvedValueOnce({ step: 'setup', challenge: 'ch2' })
    auth.startTwoFactorSetup.mockResolvedValueOnce({ secret: 'ABCSECRET', otpauth_uri: 'otpauth://x', qr_data_uri: 'data:image/svg+xml;charset=utf-8,%3Csvg%3E', account: 'chef@firma.de' })
    auth.confirmTwoFactorSetup.mockResolvedValueOnce({ access_token: 'tok2', recovery_codes: ['AAAAA-BBBBB', 'CCCCC-DDDDD'] })
    renderLogin()
    submitPassword()
    expect(await screen.findByAltText('QR-Code für die Authenticator-App')).toHaveAttribute('src', expect.stringMatching(/^data:image\/svg\+xml/))
    fireEvent.change(screen.getByLabelText('Code aus der App'), { target: { value: '654321' } })
    fireEvent.click(screen.getByRole('button', { name: 'Einrichten' }))
    expect(await screen.findByText('AAAAA-BBBBB')).toBeInTheDocument()
    expect(mockComplete).not.toHaveBeenCalled()  // erst nach Bestätigung der Sicherung
    fireEvent.click(screen.getByRole('button', { name: /Codes gesichert/ }))
    await waitFor(() => expect(mockComplete).toHaveBeenCalledWith('tok2'))
    expect(mockNavigate).toHaveBeenCalledWith('/')
  })
})
