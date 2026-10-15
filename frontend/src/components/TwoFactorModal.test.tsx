/**
 * Tests: eigene Zwei-Faktor-Einstellungen (Status, neue Wiederherstellungscodes).
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import TwoFactorModal from './TwoFactorModal'

const auth = { twoFactorStatus: vi.fn(), renewRecoveryCodes: vi.fn() }
vi.mock('../api/client', () => ({
  authApi: new Proxy({}, { get: (_t, k: string) => (...a: unknown[]) => (auth as any)[k](...a) }),
}))

beforeEach(() => vi.clearAllMocks())

describe('Zwei-Faktor-Einstellungen', () => {
  it('zeigt Status und erstellt neue Codes', async () => {
    auth.twoFactorStatus.mockResolvedValue({ enabled: true, required: true, enabled_at: '2026-10-15T10:00:00Z', recovery_codes_left: 3 })
    auth.renewRecoveryCodes.mockResolvedValue(['AAAAA-BBBBB', 'CCCCC-DDDDD'])
    render(<TwoFactorModal onClose={vi.fn()} />)
    expect(await screen.findByText(/Eingerichtet am/)).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/aktuellen Code/), { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: 'Neue Codes erstellen' }))
    expect(await screen.findByText('AAAAA-BBBBB')).toBeInTheDocument()
    expect(auth.renewRecoveryCodes).toHaveBeenCalledWith('123456')
  })

  it('nicht eingerichtet, aber Pflicht: Hinweis', async () => {
    auth.twoFactorStatus.mockResolvedValue({ enabled: false, required: true, enabled_at: null, recovery_codes_left: 0 })
    render(<TwoFactorModal onClose={vi.fn()} />)
    expect(await screen.findByText(/startet bei der nächsten Anmeldung/)).toBeInTheDocument()
  })

  it('falscher Code: Fehlermeldung', async () => {
    auth.twoFactorStatus.mockResolvedValue({ enabled: true, required: true, enabled_at: null, recovery_codes_left: 10 })
    auth.renewRecoveryCodes.mockRejectedValue(new Error('Code ist falsch oder abgelaufen'))
    render(<TwoFactorModal onClose={vi.fn()} />)
    fireEvent.change(await screen.findByLabelText(/aktuellen Code/), { target: { value: '000000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Neue Codes erstellen' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Code ist falsch')
  })
})
