import { useState, useCallback, useEffect } from 'react'
import { pdfPreviewApi } from '../api/client'

interface PreviewModalProps {
  title: string
  url: string
  type: 'pdf' | 'image'
  onClose: () => void
}

/**
 * Zeigt der Browser PDFs direkt in der Seite an? Am PC ja. Chrome auf Android bietet nur den Download an,
 * Safari auf dem iPhone zeigt im Rahmen oft nur die erste Seite. Dort zeigen wir die Seiten als Bilder.
 */
function browserShowsPdfInline(): boolean {
  const nav = navigator as Navigator & { pdfViewerEnabled?: boolean }
  const touch = typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches
  if (touch) return false
  return nav.pdfViewerEnabled !== false
}

export default function PreviewModal({ title, url, type, onClose }: PreviewModalProps) {
  const [zoom, setZoom] = useState(1)
  const [inlinePdf] = useState(() => type !== 'pdf' || browserShowsPdfInline())
  const [pages, setPages] = useState<string[] | null>(null)
  const [pageInfo, setPageInfo] = useState('')
  const [error, setError] = useState('')

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

  // Handy/Tablet: PDF vom Server als Seitenbilder erzeugen lassen
  useEffect(() => {
    if (inlinePdf) return
    let cancelled = false
    setError('')
    fetch(url)
      .then((r) => r.blob())
      .then((blob) => pdfPreviewApi.render(blob))
      .then((res) => {
        if (cancelled) return
        setPages(res.pages)
        setPageInfo(res.truncated ? `Vorschau zeigt die ersten ${res.pages.length} von ${res.page_count} Seiten.` : '')
      })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : 'Vorschau nicht möglich') })
    return () => { cancelled = true }
  }, [inlinePdf, url])

  const fileName = `${title.replace(/[^\wäöüÄÖÜß.-]+/g, '_')}.pdf`

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 720, padding: '1rem' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', gap: '0.5rem', flexWrap: 'wrap' }}>
          <h2 style={{ margin: 0, fontSize: '1rem' }}>{title}</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button type="button" onClick={zoomOut} className="btn-secondary btn-sm" title="Verkleinern">−</button>
            <span style={{ fontSize: '0.9rem', minWidth: 48, textAlign: 'center' }}>{Math.round(zoom * 100)}%</span>
            <button type="button" onClick={zoomIn} className="btn-secondary btn-sm" title="Vergrößern">+</button>
            <button type="button" onClick={onClose} className="btn-secondary btn-sm">Schließen</button>
          </div>
        </div>
        <div
          style={{
            height: '60vh',
            minHeight: 280,
            overflow: 'auto',
            background: '#1e293b',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: inlinePdf ? 'center' : 'flex-start',
            padding: inlinePdf ? '1rem' : '0.5rem',
          }}
        >
          {type === 'pdf' && !inlinePdf ? (
            <div style={{ width: `${zoom * 100}%`, minWidth: '100%' }}>
              {!pages && !error && <p style={{ color: '#cbd5e1', margin: '1rem' }}>Vorschau wird geladen…</p>}
              {error && <p className="error" role="alert" style={{ margin: '1rem' }}>{error}</p>}
              {pages?.map((src, i) => (
                <img
                  key={i}
                  src={src}
                  alt={`${title} – Seite ${i + 1}`}
                  style={{ width: '100%', height: 'auto', display: 'block', background: 'white', marginBottom: '0.5rem', borderRadius: 2 }}
                />
              ))}
            </div>
          ) : (
            <div style={{ transform: `scale(${zoom})`, transformOrigin: 'top center', transition: 'transform 0.15s ease' }}>
              {type === 'pdf' ? (
                <iframe
                  src={url}
                  title={title}
                  style={{ width: 595, height: 842, border: 'none', background: 'white' }}
                />
              ) : (
                <img
                  src={url}
                  alt={title}
                  style={{ maxWidth: '100%', height: 'auto', display: 'block', borderRadius: 4 }}
                />
              )}
            </div>
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
          <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', margin: 0 }}>
            {inlinePdf ? 'Strg + Mausrad zum Zoomen' : pageInfo || 'Mit + und − vergrößern'}
          </p>
          {type === 'pdf' && !inlinePdf && (
            <a href={url} download={fileName} className="btn-secondary btn-sm">PDF speichern / teilen</a>
          )}
        </div>
      </div>
    </div>
  )
}
