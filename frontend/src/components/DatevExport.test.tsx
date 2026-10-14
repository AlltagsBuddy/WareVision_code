/**
 * Tests für den DATEV-Export-Bereich (Einstellungen, Vorschau, Export).
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import DatevExport from './DatevExport'

const defaults = {
  SKR03: { revenue_19: '8400', revenue_7: '8300', revenue_0: '1590', expense_19: '3400', expense_7: '3300', expense_0: '3200' },
  SKR04: { revenue_19: '4400', revenue_7: '4300', revenue_0: '1370', expense_19: '5400', expense_7: '5300', expense_0: '5200' },
}
const labels = {
  revenue_19: 'Erlöse 19 %', revenue_7: 'Erlöse 7 %', revenue_0: 'Erlöse 0 % / durchlaufende Posten',
  expense_19: 'Wareneingang/Aufwand 19 %', expense_7: 'Wareneingang/Aufwand 7 %', expense_0: 'Wareneingang/Aufwand 0 %',
}
const base = {
  consultant_number: null, client_number: null, chart: 'SKR03', account_length: 4, fiscal_year_start_month: 1,
  debtor_start: 10000, creditor_start: 70000, lock_bookings: false, ...defaults.SKR03,
  account_labels: labels, default_accounts: defaults,
}
const incomplete = { ...base, problems: ['Beraternummer fehlt oder ist ungültig (1001 bis 9999999, vom Steuerberater).'] }
const complete = { ...base, consultant_number: 1234567, client_number: 56789, problems: [] }

const api = { datevSettings: vi.fn(), saveDatevSettings: vi.fn(), datevPreview: vi.fn(), datevExport: vi.fn() }
vi.mock('../api/client', () => ({
  accountingApi: new Proxy({}, { get: (_t, k: string) => (...a: unknown[]) => (api as any)[k](...a) }),
}))

const range = () => ({ from: '2026-10-01', to: '2026-10-31' })

beforeEach(() => {
  vi.clearAllMocks()
  URL.createObjectURL = vi.fn(() => 'blob:x')
  URL.revokeObjectURL = vi.fn()
})

describe('DATEV-Export', () => {
  it('zeigt fehlende Angaben und sperrt den Export', async () => {
    api.datevSettings.mockResolvedValue(incomplete)
    render(<DatevExport getRange={range} />)
    expect(await screen.findByText(/Beraternummer fehlt/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'DATEV-Export herunterladen' })).toBeDisabled()
    expect(screen.getByLabelText('Beraternummer')).toBeInTheDocument()  // Einstellungen automatisch offen
  })

  it('speichert die Einstellungen', async () => {
    api.datevSettings.mockResolvedValue(incomplete)
    api.saveDatevSettings.mockResolvedValue(complete)
    render(<DatevExport getRange={range} />)
    fireEvent.change(await screen.findByLabelText('Beraternummer'), { target: { value: '1234567' } })
    fireEvent.change(screen.getByLabelText('Mandantennummer'), { target: { value: '56789' } })
    fireEvent.click(screen.getByRole('button', { name: 'Einstellungen speichern' }))
    await waitFor(() => expect(api.saveDatevSettings).toHaveBeenCalled())
    expect(api.saveDatevSettings.mock.calls[0][0]).toMatchObject({
      consultant_number: 1234567, client_number: 56789, chart: 'SKR03', account_length: 4, revenue_19: '8400',
    })
    expect(await screen.findByText('DATEV-Einstellungen gespeichert.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'DATEV-Export herunterladen' })).not.toBeDisabled()
  })

  it('Wechsel auf SKR04 übernimmt die Kontenvorschläge', async () => {
    api.datevSettings.mockResolvedValue(incomplete)
    render(<DatevExport getRange={range} />)
    fireEvent.change(await screen.findByLabelText('Kontenrahmen'), { target: { value: 'SKR04' } })
    expect(screen.getByLabelText('Erlöse 19 %')).toHaveValue('4400')
    expect(screen.getByLabelText('Wareneingang/Aufwand 19 %')).toHaveValue('5400')
  })

  it('lehnt Buchstaben in Nummern ab', async () => {
    api.datevSettings.mockResolvedValue(incomplete)
    render(<DatevExport getRange={range} />)
    fireEvent.change(await screen.findByLabelText('Beraternummer'), { target: { value: '12a' } })
    fireEvent.click(screen.getByRole('button', { name: 'Einstellungen speichern' }))
    expect(await screen.findByText(/nur mit Ziffern/)).toBeInTheDocument()
    expect(api.saveDatevSettings).not.toHaveBeenCalled()
  })

  it('zeigt Vorschau mit Hinweisen', async () => {
    api.datevSettings.mockResolvedValue(complete)
    api.datevPreview.mockResolvedValue({
      outgoing_documents: 2, outgoing_bookings: 4, outgoing_debit: '284.11', outgoing_credit: '11.90',
      incoming_documents: 1, incoming_bookings: 1, incoming_credit: '119.00', incoming_debit: '0',
      new_accounts: 2, hints: ['RE-2026-0009: Steuersatz 16 % wird nicht unterstützt'],
    })
    render(<DatevExport getRange={range} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Vorschau' }))
    await waitFor(() => expect(api.datevPreview).toHaveBeenCalledWith('2026-10-01', '2026-10-31', true))
    expect(await screen.findByText(/16 % wird nicht unterstützt/)).toBeInTheDocument()
    expect(screen.getByText(/Neue Debitoren\/Kreditoren: 2/)).toBeInTheDocument()
  })

  it('lädt den Export ohne Eingangsrechnungen herunter', async () => {
    api.datevSettings.mockResolvedValue(complete)
    api.datevExport.mockResolvedValue(new Blob(['x']))
    render(<DatevExport getRange={range} />)
    await screen.findByRole('button', { name: 'DATEV-Export herunterladen' })
    fireEvent.click(screen.getByLabelText(/Eingangsrechnungen mit exportieren/))
    fireEvent.click(screen.getByRole('button', { name: 'DATEV-Export herunterladen' }))
    await waitFor(() => expect(api.datevExport).toHaveBeenCalledWith('2026-10-01', '2026-10-31', false))
  })

  it('zeigt Fehler vom Server', async () => {
    api.datevSettings.mockResolvedValue(complete)
    api.datevExport.mockRejectedValue(new Error('Ein DATEV-Buchungsstapel darf nur ein Wirtschaftsjahr enthalten.'))
    render(<DatevExport getRange={range} />)
    fireEvent.click(await screen.findByRole('button', { name: 'DATEV-Export herunterladen' }))
    expect(await screen.findByText(/nur ein Wirtschaftsjahr/)).toBeInTheDocument()
  })
})
