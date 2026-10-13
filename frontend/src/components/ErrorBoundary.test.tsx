/**
 * Tests für die ErrorBoundary-Komponente.
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ErrorBoundary from './ErrorBoundary'

// Konsolen-Fehler bei erwartetem Boundary-Auslösen unterdrücken
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

function FehlerhafteKomponente({ werfe }: { werfe: boolean }) {
  if (werfe) throw new Error('Testfehler aus Komponente')
  return <div>Kein Fehler</div>
}

describe('ErrorBoundary', () => {
  it('rendert Kinder normal wenn kein Fehler', () => {
    render(
      <ErrorBoundary>
        <div>Inhalt</div>
      </ErrorBoundary>
    )
    expect(screen.getByText('Inhalt')).toBeInTheDocument()
  })

  it('zeigt Fehlermeldung wenn Kind-Komponente wirft', () => {
    render(
      <ErrorBoundary>
        <FehlerhafteKomponente werfe={true} />
      </ErrorBoundary>
    )
    expect(screen.getByText(/unerwarteter Fehler/i)).toBeInTheDocument()
    expect(screen.getByText('Testfehler aus Komponente')).toBeInTheDocument()
  })

  it('zeigt "Zur Startseite"-Button im Fehlerfall', () => {
    render(
      <ErrorBoundary>
        <FehlerhafteKomponente werfe={true} />
      </ErrorBoundary>
    )
    expect(screen.getByRole('button', { name: /startseite/i })).toBeInTheDocument()
  })

  it('zeigt kein Fehlerbanner wenn kein Fehler auftritt', () => {
    render(
      <ErrorBoundary>
        <FehlerhafteKomponente werfe={false} />
      </ErrorBoundary>
    )
    expect(screen.queryByText(/unerwarteter Fehler/i)).not.toBeInTheDocument()
    expect(screen.getByText('Kein Fehler')).toBeInTheDocument()
  })

  it('Startseite-Button setzt Fehlerzustand zurück', () => {
    // window.location.href mocken
    const originalHref = window.location.href
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
    })

    render(
      <ErrorBoundary>
        <FehlerhafteKomponente werfe={true} />
      </ErrorBoundary>
    )

    fireEvent.click(screen.getByRole('button', { name: /startseite/i }))
    expect(window.location.href).toBe('/')

    Object.defineProperty(window, 'location', { value: { href: originalHref }, writable: true })
  })
})
