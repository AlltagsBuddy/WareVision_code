/**
 * Tests für die Angebotsseite (Liste, Formular mit Summen, Statusaktionen).
 */
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Quotes from './Quotes'

const customers = [
  { id: 'c1', customer_type: 'B2C', first_name: 'Julia', last_name: 'Klein' },
  { id: 'c2', customer_type: 'B2B', company_name: 'Händler GmbH' },
]
const articles = [{ id: 'a1', article_number: 'ART-1', name: 'Bremsbeläge', sales_price_b2c: '55.00', sales_price_b2b: '40.00', vat_rate: '19.00' }]
const draft = {
  id: 'q1', quote_number: 'AN-2026-0001', quote_type: 'offer', status: 'draft', customer_id: 'c1', vehicle_id: null,
  quote_date: '2026-10-13', valid_until: '2026-11-12', subject: 'Bremsen', notes: null, internal_notes: null,
  net_amount: '100.00', vat_amount: '19.00', gross_amount: '119.00', items: [
    { id: 'i1', position: 1, item_type: 'labor', description: 'Arbeit', quantity: '1.00', unit: 'Std.', unit_price: '100.00', vat_rate: '19.00', line_total_net: '100.00' },
  ],
}
const expired = { ...draft, id: 'q2', quote_number: 'AN-2026-0002', status: 'sent', valid_until: '2020-01-01' }

const api = {
  list: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  setStatus: vi.fn(),
  convert: vi.fn(),
  duplicate: vi.fn(),
  delete: vi.fn(),
  getPdf: vi.fn(),
  sendEmail: vi.fn(),
}
vi.mock('../api/client', () => ({
  quotesApi: new Proxy({}, { get: (_t, k: string) => (...a: unknown[]) => (api as any)[k](...a) }),
  customersApi: { list: () => Promise.resolve(customers) },
  vehiclesApi: { list: () => Promise.resolve([{ id: 'v1', customer_id: 'c1', license_plate: 'BA-Q 1' }]) },
  articlesApi: { list: () => Promise.resolve(articles) },
  laborRatesApi: { list: () => Promise.resolve([{ id: 'l1', name: 'Mechaniker', rate_per_hour: '89.00', is_default: true }]) },
}))
const navigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({ ...(await orig<typeof import('react-router-dom')>()), useNavigate: () => navigate }))

function renderPage() {
  return render(<MemoryRouter><Quotes /></MemoryRouter>)
}

beforeEach(() => {
  vi.clearAllMocks()
  api.list.mockResolvedValue([draft, expired])
})

describe('Angebote – Liste', () => {
  it('zeigt Angebote mit Kunde, Betrag und Status', async () => {
    renderPage()
    const row = (await screen.findByText('AN-2026-0001')).closest('tr')!
    expect(within(row).getByText('Julia Klein')).toBeInTheDocument()
    expect(within(row).getByText('119,00 €')).toBeInTheDocument()
    expect(within(row).getByText('Entwurf')).toBeInTheDocument()
  })

  it('markiert abgelaufene Angebote', async () => {
    renderPage()
    const row = (await screen.findByText('AN-2026-0002')).closest('tr')!
    expect(within(row).getByText(/abgelaufen/)).toBeInTheDocument()
  })
})

describe('Angebote – Formular', () => {
  it('berechnet Summen je Steuersatz und speichert', async () => {
    api.create.mockResolvedValue({ ...draft, id: 'new' })
    renderPage()
    await screen.findByText('AN-2026-0001')
    fireEvent.click(screen.getByRole('button', { name: '+ Neues Angebot' }))
    const modal = await screen.findByRole('heading', { name: 'Neues Angebot' })
    const form = modal.closest('.modal') as HTMLElement
    const selects = within(form).getAllByRole('combobox')
    // Kunde wählen (zweites Select)
    fireEvent.change(selects[1], { target: { value: 'c1' } })
    // erste Position (Arbeit): 2 Std. à 89 €
    const rows = within(form).getAllByRole('row').slice(1)
    const inputs = within(rows[0]).getAllByRole('textbox')
    fireEvent.change(inputs[0], { target: { value: 'Arbeitszeit' } })
    fireEvent.change(inputs[1], { target: { value: '2' } })
    fireEvent.change(inputs[3], { target: { value: '89' } })
    // Fachbuch mit 7 %
    fireEvent.click(within(form).getByRole('button', { name: '+ Freie Position' }))
    const row2 = within(form).getAllByRole('row')[2]
    const in2 = within(row2).getAllByRole('textbox')
    fireEvent.change(in2[0], { target: { value: 'Fachbuch' } })
    fireEvent.change(in2[3], { target: { value: '24,99' } })
    fireEvent.change(within(row2).getAllByRole('combobox')[1], { target: { value: '7' } })

    // 19 %: 178,00 → 33,82 ; 7 %: 24,99 → 1,75 ; Brutto 238,56
    expect(within(form).getByText('MwSt 19 %: 33,82 €')).toBeInTheDocument()
    expect(within(form).getByText('MwSt 7 %: 1,75 €')).toBeInTheDocument()
    expect(within(form).getByText('Brutto: 238,56 €')).toBeInTheDocument()

    fireEvent.click(within(form).getByRole('button', { name: 'Speichern' }))
    await waitFor(() => expect(api.create).toHaveBeenCalled())
    const payload = api.create.mock.calls[0][0]
    expect(payload.customer_id).toBe('c1')
    expect(payload.items).toHaveLength(2)
    expect(payload.items[1]).toMatchObject({ description: 'Fachbuch', unit_price: 24.99, vat_rate: 7 })
  })

  it('verlangt einen Kunden', async () => {
    renderPage()
    await screen.findByText('AN-2026-0001')
    fireEvent.click(screen.getByRole('button', { name: '+ Neues Angebot' }))
    const save = await screen.findByRole('button', { name: 'Speichern' })
    // 1. Pflichtfeld-Prüfung des Browsers verhindert das Absenden
    fireEvent.click(save)
    expect(api.create).not.toHaveBeenCalled()
    // 2. Zusätzliche Prüfung in WareVision (falls die Browser-Prüfung umgangen wird)
    fireEvent.submit(save.closest('form')!)
    expect(await screen.findByText('Bitte einen Kunden auswählen.')).toBeInTheDocument()
    expect(api.create).not.toHaveBeenCalled()
  })

  it('übernimmt bei Händlern den Händlerpreis des Artikels', async () => {
    renderPage()
    await screen.findByText('AN-2026-0001')
    fireEvent.click(screen.getByRole('button', { name: '+ Neues Angebot' }))
    const form = (await screen.findByRole('heading', { name: 'Neues Angebot' })).closest('.modal') as HTMLElement
    fireEvent.change(within(form).getAllByRole('combobox')[1], { target: { value: 'c2' } })
    fireEvent.click(within(form).getByRole('button', { name: '+ Material' }))
    const row = within(form).getAllByRole('row')[2]
    fireEvent.change(within(row).getAllByRole('combobox')[1], { target: { value: 'a1' } })
    expect(within(row).getByDisplayValue('40')).toBeInTheDocument()
    expect(within(row).getByDisplayValue('Bremsbeläge')).toBeInTheDocument()
  })
})

describe('Angebote – Aktionen', () => {
  it('Entwurf: bearbeiten, löschen und annehmen möglich', async () => {
    api.setStatus.mockResolvedValue({ ...draft, status: 'accepted' })
    renderPage()
    fireEvent.click(await screen.findByText('AN-2026-0001'))
    expect(screen.getByRole('button', { name: 'Bearbeiten' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Löschen' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Angenommen' }))
    await waitFor(() => expect(api.setStatus).toHaveBeenCalledWith('q1', 'accepted'))
    expect(await screen.findByText('(Angenommen)')).toBeInTheDocument()
  })

  it('Umwandlung fragt nach dem Fahrzeug', async () => {
    api.convert.mockResolvedValue({ ...draft, status: 'converted', workshop_order_id: 'wo1' })
    renderPage()
    fireEvent.click(await screen.findByText('AN-2026-0001'))
    fireEvent.click(screen.getByRole('button', { name: 'In Werkstattauftrag umwandeln' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Werkstattauftrag anlegen' }))
    await waitFor(() => expect(api.convert).toHaveBeenCalledWith('q1', { vehicle_id: 'v1' }))
    expect(await screen.findByRole('button', { name: 'Zum Werkstattauftrag' })).toBeInTheDocument()
  })

  it('zeigt Fehlermeldungen der API an', async () => {
    api.setStatus.mockRejectedValue(new Error('Statuswechsel nicht möglich'))
    renderPage()
    fireEvent.click(await screen.findByText('AN-2026-0001'))
    fireEvent.click(screen.getByRole('button', { name: 'Abgelehnt' }))
    expect(await screen.findByText('Statuswechsel nicht möglich')).toBeInTheDocument()
  })
})
