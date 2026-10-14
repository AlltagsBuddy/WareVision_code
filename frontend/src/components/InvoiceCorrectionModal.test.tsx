/**
 * Tests für den Dialog „Gutschrift / Rechnungskorrektur“.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import InvoiceCorrectionModal from './InvoiceCorrectionModal'

const info = {
  invoice_id: 'inv1', invoice_number: 'RE-2026-0001', gross_amount: '238.56', credited_gross: '0', remaining_gross: '238.56',
  vat_rates: ['19.00', '7.00'],
  items: [
    { item_id: 'i1', article_id: null, description: 'Arbeit', quantity: '2.00', credited_quantity: '0', remaining_quantity: '2.00',
      unit: 'Std.', unit_price: '89.00', vat_rate: '19.00' },
    { item_id: 'i2', article_id: 'a1', description: 'Bremsbeläge', quantity: '3.00', credited_quantity: '1', remaining_quantity: '2.00',
      unit: 'Stk', unit_price: '10.00', vat_rate: '19.00' },
  ],
  corrections: [{ id: 'rk0', invoice_number: 'RK-2026-0001', invoice_date: '2026-10-14', gross_amount: '-11.90', status: 'issued' }],
}

const correctionInfo = vi.fn()
const createCorrection = vi.fn()
vi.mock('../api/client', () => ({
  invoicesApi: {
    correctionInfo: (id: string) => correctionInfo(id),
    createCorrection: (id: string, d: unknown) => createCorrection(id, d),
  },
}))

const onCreated = vi.fn()
const renderModal = (status = 'paid') =>
  render(<InvoiceCorrectionModal invoice={{ id: 'inv1', invoice_number: 'RE-2026-0001', status }} onClose={() => {}} onCreated={onCreated} />)

beforeEach(() => {
  vi.clearAllMocks()
  correctionInfo.mockResolvedValue(info)
})

describe('Rechnungskorrektur-Dialog', () => {
  it('zeigt Positionen mit Restmengen und bisherige Korrekturen', async () => {
    renderModal()
    expect(await screen.findByText('Bremsbeläge')).toBeInTheDocument()
    expect(screen.getByText(/RK-2026-0001/)).toBeInTheDocument()
    // Rückbuchung ins Lager nur bei Lagerartikeln
    expect(screen.getByLabelText('Ins Lager Position 2')).toBeInTheDocument()
    expect(screen.queryByLabelText('Ins Lager Position 1')).not.toBeInTheDocument()
  })

  it('berechnet die Vorschau und sendet Positionen, Rücknahme und Nachlass', async () => {
    createCorrection.mockResolvedValue({ id: 'rk1', invoice_number: 'RK-2026-0002', gross_amount: '-129.90' })
    renderModal()
    await screen.findByText('Bremsbeläge')
    fireEvent.change(screen.getByLabelText('Gutschrift Menge Position 1'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Gutschrift Menge Position 2'), { target: { value: '2' } })
    fireEvent.click(screen.getByLabelText('Ins Lager Position 2'))
    fireEvent.change(screen.getByLabelText('Betrag netto €'), { target: { value: '10' } })
    // 89 + 20 + 10 = 119 netto, 22,61 MwSt, 141,61 brutto
    expect(screen.getByText(/Gutschrift brutto:/).textContent).toContain('141,61')
    expect(screen.getByText(/bereits bezahlt/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/Grund/), { target: { value: 'Rückgabe und Kulanz' } })
    fireEvent.click(screen.getByRole('button', { name: 'Rechnungskorrektur erstellen' }))
    await waitFor(() => expect(createCorrection).toHaveBeenCalledWith('inv1', {
      reason: 'Rückgabe und Kulanz',
      lines: [
        { item_id: 'i1', quantity: 1, return_to_stock: false },
        { item_id: 'i2', quantity: 2, return_to_stock: true },
      ],
      free_lines: [{ description: 'Preisnachlass', net_amount: 10, vat_rate: 19 }],
    }))
    expect(onCreated).toHaveBeenCalled()
  })

  it('verlangt einen Grund', async () => {
    renderModal()
    await screen.findByText('Bremsbeläge')
    fireEvent.change(screen.getByLabelText('Gutschrift Menge Position 1'), { target: { value: '1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Rechnungskorrektur erstellen' }))
    expect(await screen.findByText(/Bitte einen Grund angeben/)).toBeInTheDocument()
    expect(createCorrection).not.toHaveBeenCalled()
  })

  it('lehnt mehr als die Restmenge ab', async () => {
    renderModal()
    await screen.findByText('Bremsbeläge')
    fireEvent.change(screen.getByLabelText('Gutschrift Menge Position 2'), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText(/Grund/), { target: { value: 'Rückgabe' } })
    fireEvent.click(screen.getByRole('button', { name: 'Rechnungskorrektur erstellen' }))
    expect(await screen.findByText(/höchstens 2 gutgeschrieben/)).toBeInTheDocument()
    expect(createCorrection).not.toHaveBeenCalled()
  })

  it('Lagerrücknahme nur mit ganzen Stück', async () => {
    renderModal()
    await screen.findByText('Bremsbeläge')
    fireEvent.change(screen.getByLabelText('Gutschrift Menge Position 2'), { target: { value: '1,5' } })
    fireEvent.click(screen.getByLabelText('Ins Lager Position 2'))
    fireEvent.change(screen.getByLabelText(/Grund/), { target: { value: 'Rückgabe' } })
    fireEvent.click(screen.getByRole('button', { name: 'Rechnungskorrektur erstellen' }))
    expect(await screen.findByText(/nur ganze Stück/)).toBeInTheDocument()
  })

  it('verlangt mindestens eine Menge oder einen Nachlass', async () => {
    renderModal()
    await screen.findByText('Bremsbeläge')
    fireEvent.change(screen.getByLabelText(/Grund/), { target: { value: 'Test' } })
    fireEvent.click(screen.getByRole('button', { name: 'Rechnungskorrektur erstellen' }))
    expect(await screen.findByText(/mindestens eine Menge oder einen Nachlass/)).toBeInTheDocument()
  })

  it('zeigt Fehler der API an', async () => {
    createCorrection.mockRejectedValue(new Error('Die Gutschriften wären höher als der Rechnungsbetrag'))
    renderModal('issued')
    await screen.findByText('Bremsbeläge')
    fireEvent.change(screen.getByLabelText('Betrag netto €'), { target: { value: '5' } })
    fireEvent.change(screen.getByLabelText(/Grund/), { target: { value: 'Kulanz' } })
    fireEvent.click(screen.getByRole('button', { name: 'Rechnungskorrektur erstellen' }))
    expect(await screen.findByText('Die Gutschriften wären höher als der Rechnungsbetrag')).toBeInTheDocument()
    expect(screen.queryByText(/bereits bezahlt/)).not.toBeInTheDocument()
  })
})
