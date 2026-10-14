/**
 * Tests für die Kamera-Aufnahme (Webcam/Handy).
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import CameraCapture, { cameraSupported } from './CameraCapture'

const stopTrack = vi.fn()
const stream = { getTracks: () => [{ stop: stopTrack }] }

beforeEach(() => {
  vi.clearAllMocks()
  Object.defineProperty(window, 'isSecureContext', { value: true, configurable: true })
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: vi.fn().mockResolvedValue(stream),
      enumerateDevices: vi.fn().mockResolvedValue([]),
    },
  })
  Object.defineProperty(HTMLMediaElement.prototype, 'play', { configurable: true, value: vi.fn().mockResolvedValue(undefined) })
})

afterEach(() => {
  Object.defineProperty(window, 'isSecureContext', { value: false, configurable: true })
})

describe('Kamera-Aufnahme', () => {
  it('erkennt, ob die Kamera im Browser nutzbar ist', () => {
    expect(cameraSupported()).toBe(true)
    Object.defineProperty(window, 'isSecureContext', { value: false, configurable: true })
    expect(cameraSupported()).toBe(false)
  })

  it('startet die Kamera und stoppt sie beim Abbrechen', async () => {
    const onClose = vi.fn()
    render(<CameraCapture onCapture={vi.fn()} onClose={onClose} />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Auslösen' })).toBeEnabled())
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith(expect.objectContaining({ audio: false }))
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }))
    expect(onClose).toHaveBeenCalled()
    expect(stopTrack).toHaveBeenCalled()
  })

  it('zeigt verständliche Meldung bei verweigertem Zugriff', async () => {
    ;(navigator.mediaDevices.getUserMedia as any).mockRejectedValueOnce(Object.assign(new Error('x'), { name: 'NotAllowedError' }))
    render(<CameraCapture onCapture={vi.fn()} onClose={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Kamera-Zugriff wurde verweigert')
    expect(screen.getByRole('button', { name: 'Auslösen' })).toBeDisabled()
  })
})
