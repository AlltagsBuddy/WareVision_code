import { useEffect, useId, useRef } from 'react'
import { Html5Qrcode } from 'html5-qrcode'

interface BarcodeScannerProps {
  open: boolean
  onScan: (code: string) => void
  onClose: () => void
}

export default function BarcodeScanner({ open, onScan, onClose }: BarcodeScannerProps) {
  const id = useId().replace(/:/g, '-')
  const scannerRef = useRef<Html5Qrcode | null>(null)

  useEffect(() => {
    if (!open) return

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
        onClose()
      }
    }

    startScanner()
    return () => {
      scannerRef.current?.stop().then(() => {
        scannerRef.current = null
      })
    }
  }, [open, id, onScan, onClose])

  if (!open) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Barcode / QR-Code scannen</h2>
        <div id={id} style={{ minHeight: 200, borderRadius: 8, overflow: 'hidden' }} />
        <p style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
          Barcode oder QR-Code vor die Kamera halten
        </p>
        <div className="form-actions" style={{ marginTop: '1rem' }}>
          <button type="button" onClick={onClose} className="btn-secondary">
            Abbrechen
          </button>
        </div>
      </div>
    </div>
  )
}
