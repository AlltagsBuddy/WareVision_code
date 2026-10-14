/**
 * Tests für die Hilfe-Seite (Anleitung, Suche, KI-Assistent).
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Help from './Help'

const articles = [
  {
    id: 'rechnungen',
    title: 'Rechnungen',
    sections: [{ id: 'rechnungen--stornieren', heading: 'Stornieren', text: 'Klicke auf **Stornieren**.' }],
  },
  {
    id: 'inventur',
    title: 'Inventur',
    sections: [{ id: 'inventur--abschliessen', heading: 'Abschließen', text: 'Erst alle Artikel zählen.' }],
  },
]

const ask = vi.fn()
const search = vi.fn()
vi.mock('../api/client', () => ({
  helpApi: {
    articles: () => Promise.resolve(articles),
    status: () => Promise.resolve({ ai_enabled: true, model: 'claude-haiku-5-5' }),
    search: (q: string) => search(q),
    ask: (q: string, h: unknown) => ask(q, h),
  },
}))

beforeEach(() => {
  vi.clearAllMocks()
  // jsdom kennt scrollIntoView nicht
  Element.prototype.scrollIntoView = vi.fn()
})

describe('Hilfe-Seite', () => {
  it('zeigt Inhaltsverzeichnis und erstes Kapitel', async () => {
    render(<Help />)
    expect(await screen.findByRole('heading', { name: 'Rechnungen' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Stornieren' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Inventur' }))
    expect(await screen.findByText('Erst alle Artikel zählen.')).toBeInTheDocument()
  })

  it('sucht in der Anleitung', async () => {
    search.mockResolvedValue([
      { id: 'inventur--abschliessen', article_id: 'inventur', article_title: 'Inventur', heading: 'Abschließen', text: 'Erst alle Artikel zählen.' },
    ])
    render(<Help />)
    await screen.findByRole('heading', { name: 'Rechnungen' })
    fireEvent.change(screen.getByLabelText('Hilfe durchsuchen'), { target: { value: 'Inventur' } })
    await waitFor(() => expect(search).toHaveBeenCalledWith('Inventur'))
  })

  it('stellt eine Frage und zeigt Antwort mit Quelle', async () => {
    ask.mockResolvedValue({
      answer: 'So stornierst du eine Rechnung.',
      mode: 'ai',
      sources: [{ id: 'rechnungen--stornieren', article_id: 'rechnungen', title: 'Rechnungen – Stornieren' }],
      notice: null,
    })
    render(<Help />)
    await screen.findByRole('heading', { name: 'Rechnungen' })
    fireEvent.change(screen.getByLabelText('Frage an den Assistenten'), { target: { value: 'Wie storniere ich?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Fragen' }))
    expect(await screen.findByText('So stornierst du eine Rechnung.')).toBeInTheDocument()
    expect(screen.getByText('Rechnungen – Stornieren')).toBeInTheDocument()
    expect(ask).toHaveBeenCalledWith('Wie storniere ich?', [])
  })

  it('schickt den bisherigen Verlauf mit', async () => {
    ask.mockResolvedValue({ answer: 'Antwort', mode: 'search', sources: [], notice: null })
    render(<Help />)
    await screen.findByRole('heading', { name: 'Rechnungen' })
    const input = screen.getByLabelText('Frage an den Assistenten')
    fireEvent.change(input, { target: { value: 'Erste Frage' } })
    fireEvent.click(screen.getByRole('button', { name: 'Fragen' }))
    await screen.findByText('Antwort')
    fireEvent.change(input, { target: { value: 'Zweite Frage' } })
    fireEvent.click(screen.getByRole('button', { name: 'Fragen' }))
    await waitFor(() => expect(ask).toHaveBeenCalledTimes(2))
    expect(ask.mock.calls[1][1]).toEqual([
      { role: 'user', content: 'Erste Frage' },
      { role: 'assistant', content: 'Antwort' },
    ])
  })

  it('zeigt Hinweis zum Datenschutz', async () => {
    ask.mockResolvedValue({ answer: 'ok', mode: 'search', sources: [], notice: 'Personenbezogene Angaben wurden entfernt.' })
    render(<Help />)
    await screen.findByRole('heading', { name: 'Rechnungen' })
    fireEvent.change(screen.getByLabelText('Frage an den Assistenten'), { target: { value: 'max@test.de?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Fragen' }))
    expect(await screen.findByText('Personenbezogene Angaben wurden entfernt.')).toBeInTheDocument()
  })

  it('Fragen-Button ist bei leerer Eingabe deaktiviert', async () => {
    render(<Help />)
    await screen.findByRole('heading', { name: 'Rechnungen' })
    expect(screen.getByRole('button', { name: 'Fragen' })).toBeDisabled()
  })
})
