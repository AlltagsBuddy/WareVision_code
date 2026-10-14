/**
 * Foto mit der Kamera aufnehmen (Notebook-Webcam, Tablet, Smartphone).
 * Nutzt die Kamera direkt im Browser; braucht dafür eine sichere Verbindung (https oder localhost)
 * und die Kamera-Freigabe im Browser.
 */
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

export function cameraSupported(): boolean {
  return typeof window !== 'undefined' && window.isSecureContext === true &&
    typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia
}

function cameraErrorText(err: unknown): string {
  const name = (err as { name?: string })?.name || ''
  if (name === 'NotAllowedError' || name === 'SecurityError') {
    return 'Kamera-Zugriff wurde verweigert. Bitte im Browser die Kamera für diese Seite erlauben (Schloss-Symbol neben der Adresse) und erneut versuchen.'
  }
  if (name === 'NotFoundError' || name === 'OverconstrainedError') {
    return 'Keine Kamera gefunden. Ist eine Kamera angeschlossen und eingeschaltet?'
  }
  if (name === 'NotReadableError' || name === 'AbortError') {
    return 'Die Kamera wird gerade von einem anderen Programm benutzt (z. B. Teams oder der Barcode-Scanner). Bitte dort schließen und erneut versuchen.'
  }
  return 'Kamera konnte nicht gestartet werden.'
}

export default function CameraCapture({ onCapture, onClose }: { onCapture: (file: File) => void; onClose: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [error, setError] = useState('')
  const [ready, setReady] = useState(false)
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([])
  const [deviceId, setDeviceId] = useState<string>('')

  const stop = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }

  useEffect(() => {
    let active = true
    setReady(false)
    setError('')
    const video: MediaTrackConstraints = deviceId
      ? { deviceId: { exact: deviceId } }
      : { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } }
    navigator.mediaDevices
      .getUserMedia({ video, audio: false })
      .then(async (stream) => {
        if (!active) {
          stream.getTracks().forEach((t) => t.stop())
          return
        }
        stop()
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play().catch(() => {})
        }
        setReady(true)
        // Erst nach der Freigabe liefert der Browser die Namen der Kameras
        const all = await navigator.mediaDevices.enumerateDevices().catch(() => [])
        if (active) setDevices(all.filter((d) => d.kind === 'videoinput'))
      })
      .catch((err) => active && setError(cameraErrorText(err)))
    return () => {
      active = false
      stop()
    }
  }, [deviceId])

  const takePhoto = () => {
    const v = videoRef.current
    if (!v || !v.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = v.videoWidth
    canvas.height = v.videoHeight
    canvas.getContext('2d')?.drawImage(v, 0, 0)
    canvas.toBlob((blob) => {
      if (!blob) {
        setError('Foto konnte nicht erstellt werden.')
        return
      }
      const stamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')
      stop()
      onCapture(new File([blob], `kamera_${stamp}.jpg`, { type: 'image/jpeg' }))
    }, 'image/jpeg', 0.9)
  }

  const close = () => {
    stop()
    onClose()
  }

  return createPortal(
    <div className="modal-overlay" onClick={close}>
      <div className="modal modal-wide" role="dialog" aria-label="Foto aufnehmen" onClick={(e) => e.stopPropagation()}>
        <h2>Foto aufnehmen</h2>
        {error ? (
          <p className="error" role="alert">{error}</p>
        ) : (
          <video ref={videoRef} playsInline muted
            style={{ width: '100%', maxHeight: '60vh', background: '#000', borderRadius: 6, display: 'block' }} />
        )}
        {!error && !ready && <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Kamera wird gestartet… Bitte ggf. den Kamera-Zugriff im Browser erlauben.</p>}
        {devices.length > 1 && (
          <div className="form-group" style={{ marginTop: '0.75rem' }}>
            <label htmlFor="camera-select">Kamera</label>
            <select id="camera-select" value={deviceId} onChange={(e) => setDeviceId(e.target.value)}>
              <option value="">Standard</option>
              {devices.map((d, i) => (
                <option key={d.deviceId || i} value={d.deviceId}>{d.label || `Kamera ${i + 1}`}</option>
              ))}
            </select>
          </div>
        )}
        <div className="form-actions">
          <button type="button" className="btn-secondary" onClick={close}>Abbrechen</button>
          <button type="button" className="btn-primary" onClick={takePhoto} disabled={!ready || !!error}>Auslösen</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
