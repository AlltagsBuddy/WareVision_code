/**
 * Tests für die Bestellseite (Liste, Bestellvorschlag, Formular, Wareneingang, Rechte).
 */
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import PurchaseOrders from './PurchaseOrders'

const suppliers = [{ id: 's1', name: 'Quad Teile GmbH', email: 'b@q.de' }, { id: 's2', name: 'Öl Direkt' }]
const articles = [
  { id: 'a1', article_number: 'ZK-001', name: 'Zündkerze', supplier_id: 's1', supplier_article_number: 'NGK-CR7', purchase_price: '4.50', vat_rate: '19.00' },
]
const sent = {
  id: 'p1', order_number: 'BE-2026-0001', supplier_id: 's1', supplier_name: 'Quad Teile GmbH', status: 'sent',
  order_date: '2026-10-14', expected_date: '2020-01-01', notes: null, internal_notes: null,
  net_amount: '46.45', vat_amount: '8.83', gross_amount: '55.28', sent_to_email: 'b@q.de', created_at: '2026-10-14T08:00:00Z',
  items: [
    { id: 'i1', position: 1, article_id: 'a1', article_number: 'ZK-001', description: 'Zündkerze', supplier_article_number: 'NGK-CR7',
      quantity: 9, received_quantity: 0, unit: 'Stk', unit_price: '4.50', vat_rate: '19.00', line_total_net: '40.50' },
    { id: 'i2', position: 2, article_id: null, article_number: null, description: 'Versand', supplier_article_number: null,
      quantity: 1, received_quantity: 0, unit: 'Stk', unit_price: '5.95', vat_rate: '19.00', line_total_net: '5.95' },
  ],
}
const groups = [
  { supplier_id: 's1', supplier_name: 'Quad Teile GmbH', supplier_email: 'b@q.de', items: [
    { article_id: 'a1', article_number: 'ZK-001', name: 'Zündkerze', supplier_article_number: 'NGK-CR7', stock_quantity: 1,
      reserved_quantity: 0, on_order_quantity: 0, minimum_stock: 3, target_stock: 10, suggested_quantity: 9, unit_price: '4.50', vat_rate: '19.00' },
  ] },
  { supplier_id: null, supplier_name: 'Ohne Lieferant', supplier_email: null, items: [
    { article_id: 'a2', article_number: 'OEL-001', name: 'Motoröl', supplier_article_number: null, stock_quantity: 0,
      reserved_quantity: 0, on_order_quantity: 0, minimum_stock: 4, target_stock: null, suggested_quantity: 4, unit_price: '6.00', vat_rate: '19.00' },
  ] },
]

const api = {
  list: vi.fn(), suggestions: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn(),
  markSent: vi.fn(), sendEmail: vi.fn(), receive: vi.fn(), cancel: vi.fn(), getPdf: vi.fn(),
}
vi.mock('../api/client', () => ({
  purchaseOrdersApi: new Proxy({}, { get: (_t, k: string) => (...a: unknown[]) => (api as any)[k](...a) }),
  suppliersApi: { list: () => Promise.resolve(suppliers) },
  articlesApi: { list: () => Promise.resolve(articles) },
}))
let role = 'admin'
vi.mock('../hooks/useAuth', () => ({ useAuth: () => ({ user: { role_name: role } }) }))

beforeEach(() => {
  vi.clearAllMocks()
  role = 'admin'
  api.list.mockResolvedValue([sent])
  api.suggestions.mockResolvedValue(groups)
})

describe('Bestellungen – Liste', () => {
  it('zeigt Bestellung mit Lieferant, Fortschritt und überfälligem Termin', async () => {
    render(<PurchaseOrders />)
    const row = (await screen.findByText('BE-2026-0001')).closest('tr')!
    expect(within(row).getByText('Quad Teile GmbH')).toBeInTheDocument()
    expect(within(row).getByText('0 / 10')).toBeInTheDocument()
    expect(within(row).getByText(/überfällig/)).toBeInTheDocument()
    expect(within(row).getByText('Bestellt')).toBeInTheDocument()
  })
})

describe('Bestellvorschlag', () => {
  it('legt aus dem Vorschlag eine Bestellung mit geänderter Menge an', async () => {
    api.create.mockResolvedValue({ ...sent, id: 'new', status: 'draft' })
    render(<PurchaseOrders />)
    fireEvent.click(screen.getByRole('tab', { name: 'Bestellvorschlag' }))
    const input = await screen.findByLabelText('Menge ZK-001')
    expect(input).toHaveValue('9')
    fireEvent.change(input, { target: { value: '12' } })
    fireEvent.click(screen.getAllByRole('button', { name: 'Bestellung anlegen' })[0])
    await waitFor(() => expect(api.create).toHaveBeenCalled())
    const payload = api.create.mock.calls[0][0]
    expect(payload.supplier_id).toBe('s1')
    expect(payload.items[0]).toMatchObject({ article_id: 'a1', quantity: 12, supplier_article_number: 'NGK-CR7', unit_price: 4.5 })
  })

  it('verlangt Lieferant für Artikel ohne Lieferant', async () => {
    render(<PurchaseOrders />)
    fireEvent.click(screen.getByRole('tab', { name: 'Bestellvorschlag' }))
    await screen.findByText('Ohne Lieferant')
    fireEvent.click(screen.getAllByRole('button', { name: 'Bestellung anlegen' })[1])
    expect(await screen.findByText(/zuerst einen Lieferanten wählen/)).toBeInTheDocument()
    expect(api.create).not.toHaveBeenCalled()
  })

  it('zeigt Hinweis, wenn nichts nachbestellt werden muss', async () => {
    api.suggestions.mockResolvedValue([])
    render(<PurchaseOrders />)
    fireEvent.click(screen.getByRole('tab', { name: 'Bestellvorschlag' }))
    expect(await screen.findByText(/kein Artikel muss nachbestellt werden/)).toBeInTheDocument()
  })
})

describe('Bestellungen – Formular', () => {
  it('übernimmt Artikeldaten (EK, Lieferanten-Nr.) und berechnet Summen', async () => {
    api.create.mockResolvedValue({ ...sent, status: 'draft' })
    render(<PurchaseOrders />)
    await screen.findByText('BE-2026-0001')
    fireEvent.click(screen.getByRole('button', { name: '+ Neue Bestellung' }))
    fireEvent.change(await screen.findByLabelText('Lieferant *'), { target: { value: 's1' } })
    fireEvent.change(screen.getByLabelText('Artikel Position 1'), { target: { value: 'a1' } })
    expect(screen.getByLabelText('Lieferanten-Nr. Position 1')).toHaveValue('NGK-CR7')
    expect(screen.getByLabelText('EK Position 1')).toHaveValue('4.5')
    fireEvent.change(screen.getByLabelText('Menge Position 1'), { target: { value: '9' } })
    expect(screen.getByText('Netto: 40,50 €')).toBeInTheDocument()
    expect(screen.getByText('Brutto: 48,20 €')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }))
    await waitFor(() => expect(api.create).toHaveBeenCalled())
    expect(api.create.mock.calls[0][0].items[0]).toMatchObject({ article_id: 'a1', quantity: 9 })
  })

  it('lehnt Kommazahlen als Menge ab', async () => {
    render(<PurchaseOrders />)
    await screen.findByText('BE-2026-0001')
    fireEvent.click(screen.getByRole('button', { name: '+ Neue Bestellung' }))
    fireEvent.change(await screen.findByLabelText('Lieferant *'), { target: { value: 's1' } })
    fireEvent.change(screen.getByLabelText('Bezeichnung Position 1'), { target: { value: 'Schrauben' } })
    fireEvent.change(screen.getByLabelText('Menge Position 1'), { target: { value: '1,5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Speichern' }))
    expect(await screen.findByText(/ganze Zahl größer als 0/)).toBeInTheDocument()
    expect(api.create).not.toHaveBeenCalled()
  })
})

describe('Bestellungen – Wareneingang und Rechte', () => {
  it('bucht eine Teillieferung mit Lieferschein', async () => {
    api.receive.mockResolvedValue({ ...sent, status: 'partial', items: [{ ...sent.items[0], received_quantity: 4 }, sent.items[1]] })
    render(<PurchaseOrders />)
    fireEvent.click(await screen.findByText('BE-2026-0001'))
    fireEvent.click(screen.getByRole('button', { name: 'Wareneingang' }))
    const qty = screen.getByLabelText('Geliefert Position 1')
    expect(qty).toHaveValue('9')  // Vorbelegung = offene Menge
    fireEvent.change(qty, { target: { value: '4' } })
    fireEvent.change(screen.getByLabelText('Geliefert Position 2'), { target: { value: '0' } })
    fireEvent.change(screen.getByLabelText('Lieferschein-Nr. (optional)'), { target: { value: 'LS-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Wareneingang buchen' }))
    await waitFor(() => expect(api.receive).toHaveBeenCalledWith('p1', {
      lines: [{ item_id: 'i1', quantity: 4 }, { item_id: 'i2', quantity: 0 }],
      delivery_note: 'LS-1',
      update_purchase_price: false,
    }))
    expect(await screen.findByText('(Teilweise geliefert)')).toBeInTheDocument()
  })

  it('ungültige Wareneingangsmenge wird nicht gebucht', async () => {
    render(<PurchaseOrders />)
    fireEvent.click(await screen.findByText('BE-2026-0001'))
    fireEvent.click(screen.getByRole('button', { name: 'Wareneingang' }))
    fireEvent.change(screen.getByLabelText('Geliefert Position 1'), { target: { value: '-1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Wareneingang buchen' }))
    expect(await screen.findByText(/ganze Zahlen ab 0/)).toBeInTheDocument()
    expect(api.receive).not.toHaveBeenCalled()
  })

  it('Werkstatt-Benutzer: Wareneingang ja, Bestellen/Stornieren nein', async () => {
    role = 'werkstatt'
    api.list.mockResolvedValue([{ ...sent, status: 'draft' }, { ...sent, id: 'p2', order_number: 'BE-2026-0002' }])
    render(<PurchaseOrders />)
    fireEvent.click(await screen.findByText('BE-2026-0001'))
    expect(screen.queryByRole('button', { name: 'Als bestellt markieren' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Per E-Mail senden' })).not.toBeInTheDocument()
    expect(screen.getByText(/nur ein Administrator/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Schließen' }))
    fireEvent.click(await screen.findByText('BE-2026-0002'))
    expect(screen.getByRole('button', { name: 'Wareneingang' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Stornieren' })).not.toBeInTheDocument()
  })

  it('Admin: Entwurf als bestellt markieren', async () => {
    api.list.mockResolvedValue([{ ...sent, status: 'draft' }])
    api.markSent.mockResolvedValue(sent)
    render(<PurchaseOrders />)
    fireEvent.click(await screen.findByText('BE-2026-0001'))
    fireEvent.click(screen.getByRole('button', { name: 'Als bestellt markieren' }))
    await waitFor(() => expect(api.markSent).toHaveBeenCalledWith('p1'))
    expect(await screen.findByText('(Bestellt)')).toBeInTheDocument()
  })

  it('zeigt API-Fehler an', async () => {
    api.cancel.mockRejectedValue(new Error('Administrator-Rechte erforderlich'))
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<PurchaseOrders />)
    fireEvent.click(await screen.findByText('BE-2026-0001'))
    fireEvent.click(screen.getByRole('button', { name: 'Stornieren' }))
    expect(await screen.findByText('Administrator-Rechte erforderlich')).toBeInTheDocument()
  })
})
