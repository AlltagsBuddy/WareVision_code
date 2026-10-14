import { useEffect, useId, useRef, useState } from 'react'
import { Html5Qrcode } from 'html5-qrcode'

interface BarcodeScannerProps {
  open: boolean
  onScan: (code: string) => void
  onClose: () => void
}

/** Scanner anhalten, ohne dass ein „läuft nicht“-Fehler der Bibliothek die Seite abstürzen lässt. */
async function safeStop(scanner: Html5Qrcode): Promise<void> {
  try {
    if (scanner.isScanning) await scanner.stop()
  } catch {
    /* bereits gestoppt */
  }
}

export default function BarcodeScanner({ open, onScan, onClose }: BarcodeScannerProps) {
  const id = useId().replace(/:/g, '-')
  const fileId = useId().replace(/:/g, '-')
  const scannerRef = useRef<Html5Qrcode | null>(null)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [restart, setRestart] = useState(0)  // Kamera nach erfolglosem Foto-Scan neu starten

  // Aktuelle Callbacks merken, damit ein neues Rendern der Seite die Kamera nicht neu startet
  const onScanRef = useRef(onScan)
  const onCloseRef = useRef(onClose)
  onScanRef.current = onScan
  onCloseRef.current = onClose

  useEffect(() => {
    if (!open) {
      setCameraError(null)
      setFileError(null)
      return
    }
    let cancelled = false
    let startPromise: Promise<unknown> | null = null
    // useBarCodeDetectorIfSupported: false → ZXing statt nativer BarcodeDetector API
    // Behebt Kamera-Probleme auf Samsung/Android Chrome (schwarzer Bildschirm)
    const scanner = new Html5Qrcode(id, { useBarCodeDetectorIfSupported: false, verbose: false })
    scannerRef.current = scanner
    startPromise = scanner
      .start(
        { facingMode: 'environment' },
        {
          fps: 10,
          // Breites Suchfeld: Strichcodes (EAN) sind breit; mindestens 50 px verlangt die Bibliothek
          qrbox: (w: number, h: number) => ({
            width: Math.max(50, Math.floor(w * 0.9)),
            height: Math.max(50, Math.floor(h * 0.6)),
          }),
        },
        (decodedText) => {
          safeStop(scanner).then(() => {
            if (scannerRef.current === scanner) scannerRef.current = null
            onScanRef.current(decodedText)
            onCloseRef.current()
          })
        },
        () => {}
      )
      .then(() => {
        if (cancelled) safeStop(scanner)  // Dialog wurde während des Starts geschlossen
      })
      .catch((err) => {
        if (cancelled) return
        console.warn('Barcode-Scanner: Kamera nicht verfügbar', err)
        setCameraError('Kamera-Zugriff blockiert (z. B. bei http oder fehlender Berechtigung). Nutze „Foto aufnehmen“ (Kamera-App) oder „Bild auswählen“.')
      })
    return () => {
      cancelled = true
      // Erst stoppen, wenn der Start abgeschlossen ist – sonst wirft die Bibliothek einen Fehler
      Promise.resolve(startPromise).finally(() => safeStop(scanner))
      if (scannerRef.current === scanner) scannerRef.current = null
    }
  }, [open, id, restart])

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    setFileError(null)
    if (!file) return
    await scanImageFile(file)
  }

  // Standbild aus dem laufenden Kamerabild aufnehmen und darin den Barcode suchen
  const takePhoto = async () => {
    setFileError(null)
    const video = document.getElementById(id)?.querySelector('video') as HTMLVideoElement | null
    if (!video || !video.videoWidth) {
      if (navigator.maxTouchPoints > 0) {
        // Handy/Tablet ohne Live-Kamera (z. B. http): Kamera-App des Geräts öffnen
        document.getElementById(`cam-${fileId}`)?.click()
      } else {
        setFileError('Die Kamera ist nicht verfügbar. Bitte Kamera-Zugriff im Browser erlauben oder „Bild auswählen“ nutzen.')
      }
      return
    }
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d')?.drawImage(video, 0, 0)
    const blob: Blob | null = await new Promise((r) => canvas.toBlob(r, 'image/jpeg', 0.95))
    if (!blob) {
      setFileError('Foto konnte nicht aufgenommen werden.')
      return
    }
    await scanImageFile(new File([blob], 'kamera.jpg', { type: 'image/jpeg' }))
  }

  const scanImageFile = async (file: File) => {
    try {
      // Kamera stoppen, falls sie läuft – scanFile benötigt den freien Container
      if (scannerRef.current) {
        await safeStop(scannerRef.current)
        scannerRef.current = null
      }
      // Sichtbarer Container (id) – display:none führt zu fehlenden Dimensionen
      const tryScan = (useBarCodeDetector: boolean) =>
        new Html5Qrcode(id, { useBarCodeDetectorIfSupported: useBarCodeDetector, verbose: false })
          .scanFile(file, true)
      let decodedText: string
      try {
        decodedText = await tryScan(true)  // Native API – oft besser für EAN
      } catch {
        decodedText = await tryScan(false) // Fallback: ZXing
      }
      onScanRef.current(decodedText)
      onCloseRef.current()
    } catch (err) {
      console.error('Barcode aus Bild Fehler:', err)
      setFileError('Kein Barcode/QR-Code im Bild gefunden. Bitte näher heran oder schärfer erneut versuchen.')
      setRestart((r) => r + 1)
    }
  }

  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Barcode / QR-Code scannen</h2>
        <div id={id} style={{ minHeight: 200, borderRadius: 8, overflow: 'hidden' }} />
        {cameraError && (
          <p className="error" style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>{cameraError}</p>
        )}
        <p style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
          Barcode vor die Kamera halten – er wird automatisch erkannt. Oder ein Foto aufnehmen bzw. ein vorhandenes Bild auswählen.
        </p>
        <input
          type="file"
          id={`cam-${fileId}`}
          data-testid="barcode-camera-input"
          accept="image/*"
          capture="environment"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <input
          type="file"
          id={`file-${fileId}`}
          data-testid="barcode-file-input"
          accept="image/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
          <button type="button" className="btn-primary" style={{ flex: '1 1 10rem', width: 'auto' }} onClick={takePhoto}>
            Foto aufnehmen
          </button>
          <button type="button" className="btn-secondary" style={{ flex: '1 1 10rem' }}
            onClick={() => document.getElementById(`file-${fileId}`)?.click()}>
            Bild auswählen
          </button>
        </div>
        {fileError && <p className="error" style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>{fileError}</p>}
        <div className="form-actions" style={{ marginTop: '1rem' }}>
          <button type="button" onClick={onClose} className="btn-secondary">
            Abbrechen
          </button>
        </div>
      </div>
    </div>
  )
}
