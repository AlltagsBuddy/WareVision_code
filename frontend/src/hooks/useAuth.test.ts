/**
 * Tests für den useAuth-Hook.
 */
import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuth } from './useAuth'

// authApi aus client.ts mocken
vi.mock('../api/client', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
  },
}))

import { authApi } from '../api/client'

const mockAuthApi = authApi as {
  login: ReturnType<typeof vi.fn>
  me: ReturnType<typeof vi.fn>
}

const ADMIN_USER = {
  id: 'uuid-admin',
  email: 'admin@test.de',
  first_name: 'Test',
  last_name: 'Admin',
  role_name: 'admin',
  is_active: true,
}

const WERKSTATT_USER = {
  id: 'uuid-wk',
  email: 'werkstatt@test.de',
  first_name: 'Test',
  last_name: 'Werkstatt',
  role_name: 'werkstatt',
  is_active: true,
  permissions: {
    invoices: { visible: false, write: false },
    customers: { visible: true, write: false },
  },
}

beforeEach(() => {
  // resetAllMocks verwirft auch nicht verbrauchte Einmal-Antworten (mockResolvedValueOnce) aus vorherigen Tests
  vi.resetAllMocks()
  // Standard: /auth/me liefert den Admin (der Hook ruft me() nach dem Login ein zweites Mal über den Token-Effekt auf)
  mockAuthApi.me.mockResolvedValue(ADMIN_USER)
  localStorage.clear()
})

describe('useAuth – Initialzustand', () => {
  it('ist nicht eingeloggt wenn kein Token vorhanden', async () => {
    mockAuthApi.me.mockRejectedValueOnce(new Error('Unauthorized'))
    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.user).toBeNull()
    expect(result.current.token).toBeNull()
  })

  it('lädt Benutzer wenn Token im localStorage vorhanden', async () => {
    localStorage.setItem('token', 'valid-token')
    mockAuthApi.me.mockResolvedValueOnce(ADMIN_USER)
    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.user?.email).toBe('admin@test.de')
  })
})

describe('useAuth – Login', () => {
  it('setzt Token und Benutzer nach erfolgreichem Login', async () => {
    mockAuthApi.login.mockResolvedValueOnce({ access_token: 'jwt-token' })
    mockAuthApi.me.mockResolvedValueOnce(ADMIN_USER)

    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.loading).toBe(false))

    await act(async () => {
      await result.current.login('admin@test.de', 'passwort')
    })

    expect(localStorage.getItem('token')).toBe('jwt-token')
    expect(result.current.user?.email).toBe('admin@test.de')
  })

  it('wirft Fehler bei fehlgeschlagenem Login', async () => {
    mockAuthApi.login.mockRejectedValueOnce(new Error('Ungültige Zugangsdaten'))

    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.loading).toBe(false))

    await expect(
      act(async () => { await result.current.login('x@x.de', 'falsch') })
    ).rejects.toThrow('Ungültige Zugangsdaten')
    expect(result.current.user).toBeNull()
  })
})

describe('useAuth – Logout', () => {
  it('löscht Token und Benutzer beim Logout', async () => {
    localStorage.setItem('token', 'valid-token')
    mockAuthApi.me.mockResolvedValueOnce(ADMIN_USER)

    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.user).not.toBeNull())

    act(() => { result.current.logout() })

    expect(result.current.user).toBeNull()
    expect(result.current.token).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
  })
})

describe('useAuth – canView / canWrite', () => {
  it('Admin darf alles sehen und schreiben', async () => {
    localStorage.setItem('token', 'token')
    mockAuthApi.me.mockResolvedValueOnce(ADMIN_USER)

    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.user?.role_name).toBe('admin'))

    expect(result.current.canView('invoices')).toBe(true)
    expect(result.current.canWrite('invoices')).toBe(true)
    expect(result.current.canView('irgendwas')).toBe(true)
  })

  it('Werkstatt-Benutzer: sichtbares Modul', async () => {
    localStorage.setItem('token', 'token')
    mockAuthApi.me.mockResolvedValueOnce(WERKSTATT_USER)

    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.user?.role_name).toBe('werkstatt'))

    expect(result.current.canView('customers')).toBe(true)
    expect(result.current.canWrite('customers')).toBe(false)
  })

  it('Werkstatt-Benutzer: verborgenes Modul', async () => {
    localStorage.setItem('token', 'token')
    mockAuthApi.me.mockResolvedValueOnce(WERKSTATT_USER)

    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.user?.role_name).toBe('werkstatt'))

    expect(result.current.canView('invoices')).toBe(false)
    expect(result.current.canWrite('invoices')).toBe(false)
  })

  it('gibt false zurück wenn kein Benutzer eingeloggt', () => {
    const { result } = renderHook(() => useAuth())
    expect(result.current.canView('customers')).toBe(false)
    expect(result.current.canWrite('customers')).toBe(false)
  })
})

describe('useAuth – Zwei-Faktor', () => {
  it('liefert den 2FA-Schritt ohne Token zu speichern', async () => {
    mockAuthApi.login.mockResolvedValueOnce({ access_token: null, two_factor_required: true, two_factor_setup_required: false, challenge_token: 'ch' })
    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.loading).toBe(false))
    let step: unknown
    await act(async () => { step = await result.current.login('a@b.de', 'langespasswort') })
    expect(step).toEqual({ step: '2fa', challenge: 'ch' })
    expect(localStorage.getItem('token')).toBeNull()
  })

  it('liefert den Einrichtungsschritt', async () => {
    mockAuthApi.login.mockResolvedValueOnce({ access_token: null, two_factor_required: false, two_factor_setup_required: true, challenge_token: 'ch2' })
    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.loading).toBe(false))
    let step: unknown
    await act(async () => { step = await result.current.login('a@b.de', 'langespasswort') })
    expect(step).toEqual({ step: 'setup', challenge: 'ch2' })
  })
})
