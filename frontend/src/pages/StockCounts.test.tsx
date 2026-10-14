/**
 * Tests für die Inventur-Seite (Blindzählung, Erfassung, Abschluss).
 */
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import StockCounts from './StockCounts'

const item = (id: string, nr: string, extra: Record<string, unknown> = {}) => ({
  id, article_id: `a-${id}`, article_number: nr, article_name: `Artikel ${nr}`, location: 'Regal A', barcode: `40000${id}`,
  unit_cost: '5.00', book_qty_at_start: 10, expected_qty: null, counted_qty: null, difference: null, note: null, counted_at: null,
  ...extra,
})
const openCount = {
  id: 'sc1', count_number: 'INV-2026-01', count_date: '2026-12-31', status: 'open', scope_label: 'Gesamtes Lager',
  notes: null, value_expected: null, value_counted: null, completed_at: null, created_at: '2026-12-31T08:00:00Z',
  total_items: 2, counted_items: 0, items: [item('1', 'ART-1'), item('2', 'ART-2')],
}

const api = { list: vi.fn(), get: vi.fn(), create: vi.fn(), updateItem: vi.fn(), complete: vi.fn(), cancel: vi.fn(), getPdf: vi.fn(), getCsv: vi.fn() }
vi.mock('../api/client', () => ({
  stockCountsApi: new Proxy({}, { get: (_t, k: string) => (...a: unknown[]) => (api as any)[k](...a) }),
  storageLocationsApi: { list: () => Promise.resolve([{ id: 'l1', name: 'Regal A' }]) },
  articleCategoriesApi: { list: () => Promise.resolve([]) },
}))
let role = 'admin'
vi.mock('../hooks/useAuth', () => ({ useAuth: () => ({ user: { role_name: role } }) }))
vi.mock('../components/BarcodeScanner', () => ({ default: () => null }))

beforeEach(() => {
  vi.clearAllMocks()
  role = 'admin'
  api.list.mockResolvedValue([{ ...openCount, items: undefined }])
  api.get.mockResolvedValue(openCount)
})

async function openDetail() {
  render(<StockCounts />)
  fireEvent.click(await screen.findByText('INV-2026-01'))
  await screen.findByText('0 von 2 Artikeln gezählt')
}

describe('Inventur', () => {
  it('Übersicht zeigt Fortschritt und Status', async () => {
    render(<StockCounts />)
    const row = (await screen.findByText('INV-2026-01')).closest('tr')!
    expect(within(row).getByText('0 / 2')).toBeInTheDocument()
    expect(within(row).getByText('Zählung läuft')).toBeInTheDocument()
  })

  it('Blindzählung: Soll ist vor der Eingabe verborgen', async () => {
    await openDetail()
    const row = screen.getByText('ART-1').closest('tr')!
    expect(within(row).queryByText('10')).not.toBeInTheDocument()
    expect(within(row).getByText('·')).toBeInTheDocument()
  })

  it('Ist-Menge mit Enter speichern, danach Soll und Differenz anzeigen', async () => {
    api.updateItem.mockResolvedValue(item('1', 'ART-1', { expected_qty: 10, counted_qty: 8 }))
    await openDetail()
    const input = screen.getByLabelText('Ist-Menge Artikel ART-1')
    input.focus()
    fireEvent.change(input, { target: { value: '8' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(api.updateItem).toHaveBeenCalledWith('sc1', '1', { counted_qty: 8, note: undefined }))
    const row = screen.getByText('ART-1').closest('tr')!
    expect(await within(row).findByText('-2')).toBeInTheDocument()
    expect(screen.getByText('1 von 2 Artikeln gezählt')).toBeInTheDocument()
  })

  it('ungültige Menge wird nicht gespeichert', async () => {
    await openDetail()
    const input = screen.getByLabelText('Ist-Menge Artikel ART-1')
    fireEvent.change(input, { target: { value: '1,5' } })
    fireEvent.blur(input)
    expect(await screen.findByText(/ganze Zahl ab 0/)).toBeInTheDocument()
    expect(api.updateItem).not.toHaveBeenCalled()
  })

  it('Barcode-Suche springt zur Zeile', async () => {
    await openDetail()
    const search = screen.getByPlaceholderText('Suchen oder Barcode scannen + Enter')
    fireEvent.change(search, { target: { value: '400002' } })
    fireEvent.keyDown(search, { key: 'Enter' })
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText('Ist-Menge Artikel ART-2')))
  })

  it('Abschließen erst wenn alles gezählt ist', async () => {
    await openDetail()
    expect(screen.getByRole('button', { name: 'Inventur abschließen' })).toBeDisabled()
  })

  it('Abschluss nach Bestätigung', async () => {
    const counted = { ...openCount, counted_items: 2, items: [
      item('1', 'ART-1', { expected_qty: 10, counted_qty: 10 }), item('2', 'ART-2', { expected_qty: 10, counted_qty: 9 }),
    ] }
    api.get.mockResolvedValue(counted)
    api.complete.mockResolvedValue({ ...counted, status: 'completed', value_expected: '100.00', value_counted: '95.00',
      items: counted.items.map((i) => ({ ...i, difference: i.counted_qty! - i.expected_qty! })) })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<StockCounts />)
    fireEvent.click(await screen.findByText('INV-2026-01'))
    fireEvent.click(await screen.findByRole('button', { name: 'Inventur abschließen' }))
    await waitFor(() => expect(api.complete).toHaveBeenCalledWith('sc1'))
    expect(await screen.findByText('(Abgeschlossen)')).toBeInTheDocument()
    expect(screen.getByText('-5,00 €')).toBeInTheDocument()
    expect(screen.queryByLabelText('Ist-Menge Artikel ART-1')).not.toBeInTheDocument()  // unveränderbar
  })

  it('Werkstatt-Benutzer sieht keine Admin-Aktionen', async () => {
    role = 'werkstatt'
    await openDetail()
    expect(screen.queryByRole('button', { name: 'Inventur abschließen' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Ist-Menge Artikel ART-1')).toBeInTheDocument()  // zählen darf jeder
  })
})
