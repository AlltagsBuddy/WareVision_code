/**
 * Fotos zum Werkstattauftrag: aufnehmen/hochladen, ansehen, beschriften, entfernen.
 */
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { workshopOrdersApi } from '../api/client'

type Photo = { id: string; filename: string; caption?: string | null; created_at: string }

export default function OrderPhotos({ orderId }: { orderId: string }) {
  const [photos, setPhotos] = useState<Photo[]>([])
  const [urls, setUrls] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<Photo | null>(null)
  const [captionDraft, setCaptionDraft] = useState('')
  const urlsRef = useRef<Record<string, string>>({})
  const cameraRef = useRef<HTMLInputElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const loadThumb = async (photo: Photo) => {
    if (urlsRef.current[photo.id]) return
    try {
      const blob = await workshopOrdersApi.getPhotoBlob(orderId, photo.id)
      const url = URL.createObjectURL(blob)
      urlsRef.current = { ...urlsRef.current, [photo.id]: url }
      setUrls(urlsRef.current)
    } catch {
      /* Vorschau fehlt – Eintrag bleibt sichtbar */
    }
  }

  useEffect(() => {
    let active = true
    setLoading(true)
    workshopOrdersApi
      .listPhotos(orderId)
      .then((list) => {
        if (!active) return
        setPhotos(list)
        list.forEach(loadThumb)
      })
      .catch((e) => active && setError(e instanceof Error ? e.message : 'Fotos konnten nicht geladen werden'))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
      Object.values(urlsRef.current).forEach((u) => URL.revokeObjectURL(u))
      urlsRef.current = {}
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId])

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return
    setError('')
    setUploading(true)
    const errors: string[] = []
    for (const file of Array.from(files)) {
      try {
        const photo = await workshopOrdersApi.uploadPhoto(orderId, file)
        setPhotos((prev) => [...prev, photo])
        loadThumb(photo)
      } catch (e) {
        errors.push(`${file.name}: ${e instanceof Error ? e.message : 'Fehler'}`)
      }
    }
    if (errors.length) setError(errors.join(' · '))
    setUploading(false)
    if (cameraRef.current) cameraRef.current.value = ''
    if (fileRef.current) fileRef.current.value = ''
  }

  const openPreview = (photo: Photo) => {
    setPreview(photo)
    setCaptionDraft(photo.caption || '')
  }

  const saveCaption = async () => {
    if (!preview) return
    try {
      const updated = await workshopOrdersApi.updatePhoto(orderId, preview.id, captionDraft)
      setPhotos((prev) => prev.map((p) => (p.id === updated.id ? updated : p)))
      setPreview(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Fehler beim Speichern')
    }
  }

  const removePhoto = async (photo: Photo) => {
    if (!confirm('Foto wirklich entfernen?')) return
    try {
      await workshopOrdersApi.deletePhoto(orderId, photo.id)
      setPhotos((prev) => prev.filter((p) => p.id !== photo.id))
      const url = urlsRef.current[photo.id]
      if (url) URL.revokeObjectURL(url)
      const { [photo.id]: _removed, ...rest } = urlsRef.current
      urlsRef.current = rest
      setUrls(rest)
      setPreview(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Fehler beim Entfernen')
    }
  }

  return (
    <section className="order-photos" aria-label="Fotos zum Auftrag">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
        <h3 style={{ margin: 0 }}>Fotos{photos.length > 0 ? ` (${photos.length})` : ''}</h3>
        <button type="button" className="btn-secondary btn-sm" disabled={uploading} onClick={() => cameraRef.current?.click()}>
          Foto aufnehmen
        </button>
        <button type="button" className="btn-secondary btn-sm" disabled={uploading} onClick={() => fileRef.current?.click()}>
          Bilder auswählen
        </button>
        {uploading && <span style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Wird hochgeladen…</span>}
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden
          data-testid="photo-camera-input" onChange={(e) => handleFiles(e.target.files)} />
        <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden
          data-testid="photo-file-input" onChange={(e) => handleFiles(e.target.files)} />
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {loading ? (
        <p style={{ fontSize: '0.85rem' }}>Fotos laden…</p>
      ) : photos.length === 0 ? (
        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
          Noch keine Fotos. Erlaubt: JPEG, PNG oder WebP, max. 15 MB je Foto.
        </p>
      ) : (
        <div className="order-photo-grid">
          {photos.map((p) => (
            <button key={p.id} type="button" className="order-photo-thumb" onClick={() => openPreview(p)}
              title={p.caption || p.filename}>
              {urls[p.id] ? <img src={urls[p.id]} alt={p.caption || p.filename} /> : <span>{p.filename}</span>}
              {p.caption && <span className="order-photo-caption">{p.caption}</span>}
            </button>
          ))}
        </div>
      )}

      {preview && createPortal(
        <div className="modal-overlay" onClick={() => setPreview(null)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Foto ansehen">
            {urls[preview.id] && (
              <img src={urls[preview.id]} alt={preview.caption || preview.filename}
                style={{ maxWidth: '100%', maxHeight: '65vh', display: 'block', margin: '0 auto', borderRadius: 6 }} />
            )}
            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
              {preview.filename} · {new Date(preview.created_at).toLocaleString('de-DE')}
            </p>
            <div className="form-group">
              <label htmlFor="photo-caption">Beschreibung</label>
              <input id="photo-caption" maxLength={255} value={captionDraft}
                onChange={(e) => setCaptionDraft(e.target.value)} placeholder="z. B. Kratzer links vorne" />
            </div>
            <div className="form-actions">
              <button type="button" className="btn-secondary" onClick={() => removePhoto(preview)}>Foto entfernen</button>
              <button type="button" className="btn-secondary" onClick={() => setPreview(null)}>Schließen</button>
              <button type="button" className="btn-primary" onClick={saveCaption}
                disabled={(preview.caption || '') === captionDraft}>Beschreibung speichern</button>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </section>
  )
}
