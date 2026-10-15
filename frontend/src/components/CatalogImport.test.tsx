/**
 * Tests: Lieferanten-Artikeldaten einlesen (Vorschau, Spaltenzuordnung, Import).
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CatalogImport from './CatalogImport'

const api = { sources: vi.fn(), preview: vi.fn(), importFile: vi.fn(), remove: vi.fn() }
vi.mock('../api/client', () => ({
  catalogApi: new Proxy({}, { get: (_t, k: string) => (...a: unknown[]) => (api as any)[k](...a) }),
  suppliersApi: { list: () => Promise.resolve([{ id: 's1', name: 'Teile Gross GmbH' }]) },
}))

const preview = {
  headers: ['Art.-Nr.', 'EAN', 'Bezeichnung'],
  sample: [['NGK-1', '4006381333931', 'Zündkerze']],
  row_count: 1,
  mapping: { supplier_article_number: 0, barcode: 1, name: 2 },
  fields: [
    { key: 'barcode', label: 'Barcode (EAN/GTIN)' },
    { key: 'supplier_article_number', label: 'Artikelnummer beim Lieferanten' },
    { key: 'name', label: 'Bezeichnung' },
  ],
}

describe('CatalogImport', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.sources.mockResolvedValue([{ supplier_name: 'Alt GmbH', source: 'einvoice', count: 3, updated_at: '2026-10-15T10:00:00Z' }])
    api.preview.mockResolvedValue(preview)
    api.importFile.mockResolvedValue({ supplier_name: 'Teile Gross GmbH', created: 1, updated: 0, skipped: 0 })
  })

  it('zeigt vorhandene Daten, liest Datei und importiert mit Zuordnung', async () => {
    render(<CatalogImport onClose={() => {}} />)
    expect(await screen.findByText('Alt GmbH')).toBeInTheDocument()
    expect(screen.getByText('aus E-Rechnungen')).toBeInTheDocument()
    const file = new File(['x'], 'liste.csv', { type: 'text/csv' })
    fireEvent.change(screen.getByLabelText(/Artikeldatei/), { target: { files: [file] } })
    expect(await screen.findByText(/Zeilen erkannt/)).toBeInTheDocument()
    expect((screen.getByLabelText('Barcode (EAN/GTIN)') as HTMLSelectElement).value).toBe('1')
    // ohne Lieferant kein Import
    fireEvent.click(screen.getByRole('button', { name: 'Importieren' }))
    expect(await screen.findByText(/Lieferanten wählen/)).toBeInTheDocument()
    expect(api.importFile).not.toHaveBeenCalled()
    await waitFor(() => expect(screen.getByRole('option', { name: 'Teile Gross GmbH' })).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText('Lieferant'), { target: { value: 's1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Importieren' }))
    await waitFor(() => expect(api.importFile).toHaveBeenCalledWith(file, preview.mapping, { id: 's1' }))
    expect(await screen.findByText(/1 neu, 0 aktualisiert/)).toBeInTheDocument()
  })

  it('meldet Lesefehler', async () => {
    api.preview.mockRejectedValue(new Error('Altes Excel-Format (.xls)'))
    render(<CatalogImport onClose={() => {}} />)
    fireEvent.change(screen.getByLabelText(/Artikeldatei/), { target: { files: [new File(['x'], 'a.xls')] } })
    expect(await screen.findByRole('alert')).toHaveTextContent('.xls')
  })
})
