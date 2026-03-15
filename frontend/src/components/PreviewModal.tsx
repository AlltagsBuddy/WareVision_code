import { useState, useCallback, useEffect } from 'react'

interface PreviewModalProps {
  title: string
  url: string
  type: 'pdf' | 'image'
  onClose: () => void
}

export default function PreviewModal({ title, url, type, onClose }: PreviewModalProps) {
  const [zoom, setZoom] = useState(1)

  const zoomIn = useCallback(() => setZoom((z) => Math.min(z + 0.25, 3)), [])
  const zoomOut = useCallback(() => setZoom((z) => Math.max(z - 0.25, 0.25)), [])

  useEffect(() => {
    const onWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault()
        if (e.deltaY < 0) zoomIn()
        else zoomOut()
      }
    }
    window.addEventListener('wheel', onWheel, { passive: false })
    return () => window.removeEventListener('wheel', onWheel)
  }, [zoomIn, zoomOut])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 720, padding: '1rem' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h2 style={{ margin: 0, fontSize: '1rem' }}>{title}</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={zoomOut}
              className="btn-secondary btn-sm"
              title="Verkleinern"
            >
              −
            </button>
            <span style={{ fontSize: '0.9rem', minWidth: 48, textAlign: 'center' }}>
              {Math.round(zoom * 100)}%
            </span>
            <button
              type="button"
              onClick={zoomIn}
              className="btn-secondary btn-sm"
              title="Vergrößern"
            >
              +
            </button>
            <button type="button" onClick={onClose} className="btn-secondary btn-sm">
              Schließen
            </button>
          </div>
        </div>
        <div
          style={{
            height: '55vh',
            minHeight: 280,
            overflow: 'auto',
            background: '#1e293b',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'center',
            padding: '1rem',
          }}
        >
          <div
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: 'top center',
              transition: 'transform 0.15s ease',
            }}
          >
            {type === 'pdf' ? (
              <iframe
                src={url}
                title={title}
                style={{
                  width: 595,
                  height: 842,
                  border: 'none',
                  background: 'white',
                }}
              />
            ) : (
              <img
                src={url}
                alt={title}
                style={{
                  maxWidth: '100%',
                  height: 'auto',
                  display: 'block',
                  borderRadius: 4,
                }}
              />
            )}
          </div>
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: '0.5rem', marginBottom: 0 }}>
          Strg + Mausrad zum Zoomen
        </p>
      </div>
    </div>
  )
}
