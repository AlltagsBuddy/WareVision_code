import { useEffect, useState, useRef } from 'react'
import { documentsApi, customersApi, vehiclesApi } from '../api/client'

const ALLOWED_EXT = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp']
const IMAGE_EXT = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

const isImageDoc = (filename: string) => {
  const ext = '.' + (filename.split('.').pop()?.toLowerCase() || '')
  return IMAGE_EXT.includes(ext)
}

export default function Documents() {
  const [documents, setDocuments] = useState<any[]>([])
  const [customers, setCustomers] = useState<any[]>([])
  const [vehicles, setVehicles] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [customerFilter, setCustomerFilter] = useState<string>('')
  const [vehicleFilter, setVehicleFilter] = useState<string>('')
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')
  const [assignModal, setAssignModal] = useState<{ doc: any } | null>(null)
  const [assignForm, setAssignForm] = useState({ customer_id: '', vehicle_id: '' })
  const [textModal, setTextModal] = useState<{ doc: any } | null>(null)
  const [extractingId, setExtractingId] = useState<string | null>(null)
  const [cameraModal, setCameraModal] = useState(false)
  const [cameraError, setCameraError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  useEffect(() => () => stopCamera(), [])

  useEffect(() => {
    Promise.all([
      documentsApi.list({
        customer_id: customerFilter || undefined,
        vehicle_id: vehicleFilter || undefined,
      }),
      customersApi.list(),
      vehiclesApi.list(),
    ])
      .then(([docs, custs, vehs]) => {
        setDocuments(docs)
        setCustomers(custs)
        setVehicles(vehs)
      })
      .finally(() => setLoading(false))
  }, [customerFilter, vehicleFilter])

  const getCustomerName = (customerId: string | null) => {
    if (!customerId) return '–'
    const c = customers.find((x) => x.id === customerId)
    if (!c) return '–'
    return c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || '–'
  }

  const getVehicleLabel = (vehicleId: string | null) => {
    if (!vehicleId) return '–'
    const v = vehicles.find((x) => x.id === vehicleId)
    if (!v) return '–'
    return v.license_plate || v.vin || 'Fahrzeug'
  }

  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    } catch {
      return '–'
    }
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    setUploadError('')
    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        const ext = '.' + file.name.split('.').pop()?.toLowerCase()
        if (!ALLOWED_EXT.includes(ext)) {
          setUploadError(`Dateityp nicht erlaubt: ${file.name}`)
          continue
        }
        await documentsApi.upload(file, customerFilter || undefined, vehicleFilter || undefined)
      }
      const updated = await documentsApi.list({
        customer_id: customerFilter || undefined,
        vehicle_id: vehicleFilter || undefined,
      })
      setDocuments(updated)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload fehlgeschlagen')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const startCamera = async () => {
    setCameraError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      streamRef.current = stream
      if (videoRef.current) videoRef.current.srcObject = stream
    } catch (err) {
      setCameraError('Kamera-Zugriff fehlgeschlagen. Bitte Berechtigung prüfen.')
    }
  }

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
  }

  const capturePhoto = async () => {
    if (!videoRef.current) return
    const canvas = document.createElement('canvas')
    canvas.width = videoRef.current.videoWidth
    canvas.height = videoRef.current.videoHeight
    canvas.getContext('2d')?.drawImage(videoRef.current, 0, 0)
    canvas.toBlob(
      async (blob) => {
        if (!blob) return
        setUploading(true)
        setCameraError('')
        try {
          const file = new File([blob], `Foto_${new Date().toISOString().slice(0, 10)}_${Date.now()}.jpg`, {
            type: 'image/jpeg',
          })
          await documentsApi.upload(file, customerFilter || undefined, vehicleFilter || undefined)
          const updated = await documentsApi.list({
            customer_id: customerFilter || undefined,
            vehicle_id: vehicleFilter || undefined,
          })
          setDocuments(updated)
          setCameraModal(false)
          stopCamera()
        } catch (err) {
          setCameraError(err instanceof Error ? err.message : 'Upload fehlgeschlagen')
        } finally {
          setUploading(false)
        }
      },
      'image/jpeg',
      0.9
    )
  }

  const openPreview = async (doc: any) => {
    if (!isImageDoc(doc.filename)) return
    try {
      const blob = await documentsApi.getBlob(doc.id)
      const url = URL.createObjectURL(blob)
      setPreviewModal({ doc, url })
    } catch {
      setUploadError('Vorschau konnte nicht geladen werden')
    }
  }

  const closePreview = () => {
    if (previewModal) {
      URL.revokeObjectURL(previewModal.url)
      setPreviewModal(null)
    }
  }

  const handleDownload = async (doc: any) => {
    try {
      await documentsApi.download(doc.id, doc.filename)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Download fehlgeschlagen')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Dokument wirklich löschen?')) return
    try {
      await documentsApi.delete(id)
      setDocuments((prev) => prev.filter((d) => d.id !== id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Löschen fehlgeschlagen')
    }
  }

  const handleExtractText = async (doc: any) => {
    setExtractingId(doc.id)
    try {
      const updated = await documentsApi.extractText(doc.id)
      setDocuments((prev) => prev.map((d) => (d.id === doc.id ? updated : d)))
      setTextModal({ doc: updated })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Textextraktion fehlgeschlagen')
    } finally {
      setExtractingId(null)
    }
  }

  const openAssignModal = (doc: any) => {
    setAssignModal({ doc })
    setAssignForm({ customer_id: doc.customer_id || '', vehicle_id: doc.vehicle_id || '' })
  }

  const handleAssign = async () => {
    if (!assignModal) return
    try {
      await documentsApi.update(assignModal.doc.id, {
        customer_id: assignForm.customer_id || undefined,
        vehicle_id: assignForm.vehicle_id || undefined,
      })
      setDocuments((prev) =>
        prev.map((d) =>
          d.id === assignModal.doc.id
            ? { ...d, customer_id: assignForm.customer_id || null, vehicle_id: assignForm.vehicle_id || null }
            : d
        )
      )
      setAssignModal(null)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  return (
    <div className="page">
      <h1>Dokumente</h1>
      <div className="toolbar">
        <select
          value={customerFilter}
          onChange={(e) => setCustomerFilter(e.target.value)}
          className="select"
        >
          <option value="">Alle Kunden</option>
          {customers.map((c) => (
            <option key={c.id} value={c.id}>
              {c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email}
            </option>
          ))}
        </select>
        <select
          value={vehicleFilter}
          onChange={(e) => setVehicleFilter(e.target.value)}
          className="select"
        >
          <option value="">Alle Fahrzeuge</option>
          {vehicles.map((v) => (
            <option key={v.id} value={v.id}>
              {v.license_plate || v.vin || v.id?.slice(0, 8)}
            </option>
          ))}
        </select>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.gif,.webp"
          multiple
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="btn-primary"
        >
          {uploading ? 'Wird hochgeladen...' : '+ Hochladen'}
        </button>
      </div>
      {uploadError && <p className="error">{uploadError}</p>}

      {textModal && (
        <div className="modal-overlay" onClick={() => setTextModal(null)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>Extrahierter Text: {textModal.doc.filename}</h2>
            <div
              style={{
                maxHeight: 400,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                fontFamily: 'monospace',
                fontSize: '0.9rem',
                padding: '1rem',
                background: 'var(--color-bg)',
                borderRadius: 6,
                border: '1px solid var(--color-border)',
              }}
            >
              {textModal.doc.extracted_text || '(Kein Text extrahiert)'}
            </div>
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={() => setTextModal(null)} className="btn-secondary">
                Schließen
              </button>
              {!textModal.doc.extracted_text && (
                <button type="button" onClick={() => handleExtractText(textModal.doc)} className="btn-primary">
                  Text extrahieren
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {cameraModal && (
        <div className="modal-overlay" onClick={() => { setCameraModal(false); stopCamera() }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Foto aufnehmen</h2>
            <div style={{ position: 'relative', background: '#000', borderRadius: 8, overflow: 'hidden', minHeight: 300 }}>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                style={{ width: '100%', display: 'block' }}
              />
            </div>
            {cameraError && <p className="error" style={{ marginTop: '0.5rem' }}>{cameraError}</p>}
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={() => { setCameraModal(false); stopCamera() }} className="btn-secondary">
                Abbrechen
              </button>
              <button type="button" onClick={capturePhoto} disabled={uploading} className="btn-primary">
                {uploading ? 'Wird hochgeladen...' : 'Aufnehmen & Hochladen'}
              </button>
            </div>
          </div>
        </div>
      )}

      {previewModal && (
        <div className="modal-overlay" onClick={closePreview}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>Bildvorschau: {previewModal.doc.filename}</h2>
            <div style={{ textAlign: 'center', maxHeight: '70vh', overflow: 'auto' }}>
              <img
                src={previewModal.url}
                alt={previewModal.doc.filename}
                style={{ maxWidth: '100%', height: 'auto', borderRadius: 8 }}
              />
            </div>
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={closePreview} className="btn-secondary">
                Schließen
              </button>
              <button type="button" onClick={() => { handleDownload(previewModal.doc); closePreview() }} className="btn-primary">
                Download
              </button>
            </div>
          </div>
        </div>
      )}

      {assignModal && (
        <div className="modal-overlay" onClick={() => setAssignModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Zuordnung: {assignModal.doc.filename}</h2>
            <div className="form-group">
              <label>Kunde</label>
              <select
                value={assignForm.customer_id}
                onChange={(e) => {
                  const newCustomerId = e.target.value
                  const selVehicle = vehicles.find((v) => v.id === assignForm.vehicle_id)
                  const vehicleId = selVehicle && (!newCustomerId || selVehicle.customer_id === newCustomerId)
                    ? assignForm.vehicle_id
                    : ''
                  setAssignForm({ ...assignForm, customer_id: newCustomerId, vehicle_id: vehicleId })
                }}
              >
                <option value="">– Keiner –</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Fahrzeug</label>
              <select
                value={assignForm.vehicle_id}
                onChange={(e) => setAssignForm({ ...assignForm, vehicle_id: e.target.value })}
              >
                <option value="">– Keines –</option>
                {vehicles
                  .filter((v) => !assignForm.customer_id || v.customer_id === assignForm.customer_id)
                  .map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.license_plate || v.vin || 'Fahrzeug'} ({getCustomerName(v.customer_id)})
                    </option>
                  ))}
              </select>
            </div>
            <div className="form-actions">
              <button type="button" onClick={() => setAssignModal(null)} className="btn-secondary">
                Abbrechen
              </button>
              <button type="button" onClick={handleAssign} className="btn-primary">
                Speichern
              </button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <p>Laden...</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Dateiname</th>
              <th>Größe</th>
              <th>Kunde</th>
              <th>Fahrzeug</th>
              <th>Hochgeladen</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {documents.length === 0 ? (
              <tr>
                <td colSpan={6}>Keine Dokumente. Klicken Sie auf „Hochladen“, um Dateien hinzuzufügen.</td>
              </tr>
            ) : (
              documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.filename}</td>
                  <td>{formatSize(doc.file_size)}</td>
                  <td>{getCustomerName(doc.customer_id)}</td>
                  <td>{getVehicleLabel(doc.vehicle_id)}</td>
                  <td>{formatDate(doc.created_at)}</td>
                  <td>
                    {isImageDoc(doc.filename) && (
                      <button
                        type="button"
                        onClick={() => openPreview(doc)}
                        className="btn-secondary btn-sm"
                      >
                        Vorschau
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDownload(doc)}
                      className="btn-secondary btn-sm"
                    >
                      Download
                    </button>
                    <button
                      type="button"
                      onClick={() => (doc.extracted_text ? setTextModal({ doc }) : handleExtractText(doc))}
                      disabled={extractingId === doc.id}
                      className="btn-secondary btn-sm"
                    >
                      {extractingId === doc.id ? '…' : doc.extracted_text ? 'Text anzeigen' : 'Text extrahieren'}
                    </button>
                    <button
                      type="button"
                      onClick={() => openAssignModal(doc)}
                      className="btn-secondary btn-sm"
                    >
                      Zuordnen
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(doc.id)}
                      className="btn-secondary btn-sm"
                    >
                      Löschen
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
