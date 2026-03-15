import { useEffect, useId, useRef, useState } from 'react'
import { Html5Qrcode } from 'html5-qrcode'

interface BarcodeScannerProps {
  open: boolean
  onScan: (code: string) => void
  onClose: () => void
}

export default function BarcodeScanner({ open, onScan, onClose }: BarcodeScannerProps) {
  const id = useId().replace(/:/g, '-')
  const fileId = useId().replace(/:/g, '-')
  const scannerRef = useRef<Html5Qrcode | null>(null)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      setCameraError(null)
      setFileError(null)
      return
    }

    const startScanner = async () => {
      try {
        const scanner = new Html5Qrcode(id)
        scannerRef.current = scanner
        await scanner.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 250, height: 150 } },
          (decodedText) => {
            scanner.stop().then(() => {
              scannerRef.current = null
              onScan(decodedText)
              onClose()
            })
          },
          () => {}
        )
      } catch (err) {
        console.error('Barcode-Scanner Fehler:', err)
        setCameraError('Kamera-Zugriff blockiert (z.B. bei http oder fehlender Berechtigung). Nutze „Foto auswählen“.')
      }
    }

    startScanner()
    return () => {
      scannerRef.current?.stop().then(() => {
        scannerRef.current = null
      })
    }
  }, [open, id, onScan, onClose])

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    setFileError(null)
    if (!file) return
    try {
      const scanner = new Html5Qrcode(fileId)
      const decodedText = await scanner.scanFile(file, false)
      onScan(decodedText)
      onClose()
    } catch (err) {
      console.error('Barcode aus Bild Fehler:', err)
      setFileError('Kein Barcode/QR-Code im Bild gefunden.')
    }
  }

  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Barcode / QR-Code scannen</h2>
        <div id={id} style={{ minHeight: 200, borderRadius: 8, overflow: 'hidden' }} />
        <div id={fileId} style={{ display: 'none' }} />
        {cameraError && (
          <p className="error" style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>{cameraError}</p>
        )}
        <p style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
          Barcode vor die Kamera halten – oder Foto auswählen
        </p>
        <input
          type="file"
          id={`file-${fileId}`}
          accept="image/*"
          capture="environment"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <label htmlFor={`file-${fileId}`} className="btn-primary" style={{ display: 'inline-block', marginTop: '0.5rem', cursor: 'pointer' }}>
          Foto auswählen / aufnehmen
        </label>
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
