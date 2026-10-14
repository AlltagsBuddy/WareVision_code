/**
 * Tests für Fotos am Werkstattauftrag.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import OrderPhotos from './OrderPhotos'

const api = { listPhotos: vi.fn(), uploadPhoto: vi.fn(), getPhotoBlob: vi.fn(), updatePhoto: vi.fn(), deletePhoto: vi.fn() }
vi.mock('../api/client', () => ({
  workshopOrdersApi: new Proxy({}, { get: (_t, k: string) => (...a: unknown[]) => (api as any)[k](...a) }),
}))

const photo = { id: 'p1', filename: 'schaden.jpg', caption: 'Kratzer', created_at: '2026-10-14T10:00:00Z' }

beforeEach(() => {
  vi.clearAllMocks()
  api.getPhotoBlob.mockResolvedValue(new Blob(['x'], { type: 'image/jpeg' }))
  ;(globalThis.URL as any).createObjectURL = vi.fn(() => 'blob:foto')
  ;(globalThis.URL as any).revokeObjectURL = vi.fn()
})

describe('Fotos am Auftrag', () => {
  it('zeigt Hinweis ohne Fotos', async () => {
    api.listPhotos.mockResolvedValue([])
    render(<OrderPhotos orderId="o1" />)
    expect(await screen.findByText(/Noch keine Fotos/)).toBeInTheDocument()
  })

  it('zeigt vorhandene Fotos als Vorschau', async () => {
    api.listPhotos.mockResolvedValue([photo])
    render(<OrderPhotos orderId="o1" />)
    const img = await screen.findByAltText('Kratzer')
    expect(img).toHaveAttribute('src', 'blob:foto')
    expect(api.getPhotoBlob).toHaveBeenCalledWith('o1', 'p1')
    expect(screen.getByRole('heading', { name: 'Fotos (1)' })).toBeInTheDocument()
  })

  it('lädt ausgewählte Bilder hoch und meldet Fehler je Datei', async () => {
    api.listPhotos.mockResolvedValue([])
    api.uploadPhoto
      .mockResolvedValueOnce({ ...photo, id: 'p2', caption: null, filename: 'a.png' })
      .mockRejectedValueOnce(new Error('Nur Fotos im Format JPEG, PNG oder WebP sind erlaubt'))
    render(<OrderPhotos orderId="o1" />)
    await screen.findByText(/Noch keine Fotos/)
    const input = screen.getByTestId('photo-file-input')
    const good = new File(['a'], 'a.png', { type: 'image/png' })
    const bad = new File(['b'], 'b.heic', { type: 'image/heic' })
    fireEvent.change(input, { target: { files: [good, bad] } })
    expect(await screen.findByRole('alert')).toHaveTextContent('b.heic: Nur Fotos im Format JPEG, PNG oder WebP')
    expect(api.uploadPhoto).toHaveBeenCalledTimes(2)
    expect(await screen.findByAltText('a.png')).toBeInTheDocument()
  })

  it('Beschreibung ändern und Foto entfernen', async () => {
    api.listPhotos.mockResolvedValue([photo])
    api.updatePhoto.mockResolvedValue({ ...photo, caption: 'Delle' })
    api.deletePhoto.mockResolvedValue(undefined)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<OrderPhotos orderId="o1" />)
    fireEvent.click(await screen.findByTitle('Kratzer'))
    fireEvent.change(screen.getByLabelText('Beschreibung'), { target: { value: 'Delle' } })
    fireEvent.click(screen.getByRole('button', { name: 'Beschreibung speichern' }))
    await waitFor(() => expect(api.updatePhoto).toHaveBeenCalledWith('o1', 'p1', 'Delle'))
    fireEvent.click(screen.getByRole('button', { name: 'Foto entfernen' }))
    await waitFor(() => expect(api.deletePhoto).toHaveBeenCalledWith('o1', 'p1'))
    expect(await screen.findByText(/Noch keine Fotos/)).toBeInTheDocument()
  })

  it('Notebook ohne https: verständlicher Hinweis statt Dateidialog', async () => {
    api.listPhotos.mockResolvedValue([])
    Object.defineProperty(window, 'isSecureContext', { value: false, configurable: true })
    Object.defineProperty(navigator, 'maxTouchPoints', { value: 0, configurable: true })
    render(<OrderPhotos orderId="o1" />)
    await screen.findByText(/Noch keine Fotos/)
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, 'click')
    fireEvent.click(screen.getByRole('button', { name: 'Foto aufnehmen' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('nur, wenn WareVision über https')
    expect(clickSpy).not.toHaveBeenCalled()
    clickSpy.mockRestore()
  })
})
