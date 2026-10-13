/**
 * Tests für den API-Client (client.ts).
 * fetch wird gemockt – kein echter HTTP-Request.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { api } from './client'

// fetch global mocken
const mockFetch = vi.fn()
global.fetch = mockFetch

// localStorage mocken
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

// window.location.href mocken
Object.defineProperty(window, 'location', {
  value: { href: '', hostname: 'localhost' },
  writable: true,
})

// beforeEach auf oberster Ebene damit alle describe-Blöcke profitieren
beforeEach(() => {
  vi.clearAllMocks()
  localStorageMock.clear()
})

describe('api() – HTTP-Client', () => {

  it('sendet GET-Request und parst JSON', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => ({ id: '123', name: 'Test' }),
    })

    const result = await api<{ id: string; name: string }>('/customers/123')
    expect(result).toEqual({ id: '123', name: 'Test' })
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/customers/123',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) })
    )
  })

  it('fügt Authorization-Header hinzu wenn Token vorhanden', async () => {
    localStorageMock.setItem('token', 'mein-jwt-token')
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => ({}),
    })

    await api('/test')
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/test',
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: 'Bearer mein-jwt-token' }),
      })
    )
  })

  it('wirft Fehler bei HTTP 400 mit detail-Meldung', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      headers: { get: () => 'application/json' },
      json: async () => ({ detail: 'Ungültige Eingabe' }),
    })

    await expect(api('/test')).rejects.toThrow('Ungültige Eingabe')
  })

  it('gibt undefined zurück bei HTTP 204', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
      headers: { get: () => '' },
    })

    const result = await api('/test')
    expect(result).toBeUndefined()
  })

  it('löscht Token und leitet weiter bei HTTP 401', async () => {
    localStorageMock.setItem('token', 'abgelaufenes-token')
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      headers: { get: () => 'application/json' },
      json: async () => ({}),
    })

    await expect(api('/test')).rejects.toThrow()
    expect(localStorageMock.getItem('token')).toBeNull()
  })
})

describe('API-Basis-URL', () => {
  it('hängt API_BASE vor alle Pfade', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: { get: () => 'application/json' },
      json: async () => ([]),
    })

    await api('/invoices/')
    const calledUrl = (mockFetch.mock.calls[0] as any[])[0]
    expect(calledUrl).toBe('/api/v1/invoices/')
  })
})
