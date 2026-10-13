/**
 * Tests für useAuth-Hook.
 * authApi wird direkt gemockt um useEffect-Doppelaufrufe zu vermeiden.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAuth } from './useAuth'

// authApi aus client.ts mocken
vi.mock('../api/client', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
    exportMyData: vi.fn(),
  },
}))

import { authApi } from '../api/client'

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(global, 'localStorage', { value: localStorageMock })

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
    // me() schlägt fehl wenn kein Token → verhindert unerwünschte useEffect-Aufrufe
    vi.mocked(authApi.me).mockRejectedValue(new Error('Kein Token'))
  })

  it('ist initial nicht eingeloggt wenn kein Token im Storage', () => {
    const { result } = renderHook(() => useAuth())
    expect(result.current.token).toBeNull()
    expect(result.current.user).toBeNull()
  })

  it('token wird aus localStorage geladen', async () => {
    localStorageMock.setItem('token', 'gespeicherter-token')
    const mockUser = { id: '1', email: 'test@test.de', first_name: 'Test', last_name: 'User', role_name: 'admin', is_active: true }
    vi.mocked(authApi.me).mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth())

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50))
    })

    expect(result.current.token).toBe('gespeicherter-token')
    expect(result.current.user?.email).toBe('test@test.de')
  })

  it('logout entfernt Token und Benutzer', async () => {
    localStorageMock.setItem('token', 'test-token')
    vi.mocked(authApi.me).mockResolvedValue({
      id: '1', email: 'x@y.de', first_name: 'X', last_name: 'Y', role_name: 'admin', is_active: true,
    })
    const { result } = renderHook(() => useAuth())

    await act(async () => { await new Promise((r) => setTimeout(r, 50)) })

    act(() => { result.current.logout() })

    expect(result.current.token).toBeNull()
    expect(result.current.user).toBeNull()
    expect(localStorageMock.getItem('token')).toBeNull()
  })

  it('login speichert Token und Benutzer', async () => {
    const mockUser = { id: '42', email: 'admin@test.de', first_name: 'Admin', last_name: 'Test', role_name: 'admin', is_active: true }
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'neuer-token', token_type: 'bearer' })
    // me() wird einmal für den useEffect und einmal im login() direkt aufgerufen
    vi.mocked(authApi.me).mockResolvedValue(mockUser)

    const { result } = renderHook(() => useAuth())

    await act(async () => {
      await result.current.login('admin@test.de', 'passwort123')
    })

    expect(result.current.token).toBe('neuer-token')
    expect(localStorageMock.getItem('token')).toBe('neuer-token')
    expect(result.current.user?.email).toBe('admin@test.de')
  })

  it('login-fehler wirft exception', async () => {
    vi.mocked(authApi.login).mockRejectedValue(new Error('Ungültige E-Mail oder Passwort'))

    const { result } = renderHook(() => useAuth())

    await expect(
      act(async () => { await result.current.login('falsch@test.de', 'wrong') })
    ).rejects.toThrow('Ungültige E-Mail oder Passwort')

    expect(result.current.token).toBeNull()
  })
})
