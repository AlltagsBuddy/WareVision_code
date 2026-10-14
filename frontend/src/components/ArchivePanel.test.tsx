/**
 * Tests für den Bereich „Belegarchiv (GoBD)“.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ArchivePanel from './ArchivePanel'

const api = { status: vi.fn(), backfill: vi.fn(), verify: vi.fn() }
vi.mock('../api/client', () => ({
  archiveApi: new Proxy({}, { get: (_t, k: string) => (...a: unknown[]) => (api as any)[k](...a) }),
}))

const complete = { archived_documents: 12, backfilled_documents: 0, missing: { invoices: 0, reminders: 0, quotes: 0, purchase_orders: 0 }, missing_total: 0 }
const missing = { archived_documents: 2, backfilled_documents: 0, missing: { invoices: 5, reminders: 1, quotes: 0, purchase_orders: 0 }, missing_total: 6 }

beforeEach(() => vi.clearAllMocks())

describe('Belegarchiv', () => {
  it('zeigt vollständiges Archiv', async () => {
    api.status.mockResolvedValue(complete)
    render(<ArchivePanel />)
    expect(await screen.findByText(/Alle ausgegebenen Belege sind archiviert/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Fehlende Originale erzeugen' })).not.toBeInTheDocument()
  })

  it('zeigt fehlende Originale und zieht sie nach', async () => {
    api.status.mockResolvedValue(missing)
    api.backfill.mockResolvedValue({ created: { invoices: 5, reminders: 1, quotes: 0, purchase_orders: 0 }, hints: [], status: { ...complete, backfilled_documents: 6 } })
    render(<ArchivePanel />)
    expect(await screen.findByText(/6 ausgegebene Belege ohne Original/)).toBeInTheDocument()
    expect(screen.getByText('Rechnungen / Storno / Korrekturen: 5')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Fehlende Originale erzeugen' }))
    expect(await screen.findByText('6 Beleg(e) nachträglich archiviert.')).toBeInTheDocument()
    expect(screen.getByText(/davon 6 nachträglich erzeugt/)).toBeInTheDocument()
  })

  it('meldet veränderte Archivdateien deutlich', async () => {
    api.status.mockResolvedValue(complete)
    api.verify.mockResolvedValue({ checked: 12, problems: ['Archivdatei für RE-2026-0001 (pdf) wurde verändert (Prüfsumme falsch)'] })
    render(<ArchivePanel />)
    fireEvent.click(await screen.findByRole('button', { name: 'Archiv prüfen' }))
    expect(await screen.findByText(/1 von 12 Archivdateien fehlen oder wurden verändert/)).toBeInTheDocument()
    expect(screen.getByText(/RE-2026-0001/)).toBeInTheDocument()
  })

  it('bestätigt unveränderte Dateien', async () => {
    api.status.mockResolvedValue(complete)
    api.verify.mockResolvedValue({ checked: 12, problems: [] })
    render(<ArchivePanel />)
    fireEvent.click(await screen.findByRole('button', { name: 'Archiv prüfen' }))
    await waitFor(() => expect(screen.getByText(/Alle 12 Archivdateien sind vollständig und unverändert/)).toBeInTheDocument())
  })
})
