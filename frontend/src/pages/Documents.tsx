import { useEffect, useState, useRef } from 'react'
import { documentsApi, customersApi, vehiclesApi } from '../api/client'

const ALLOWED_EXT = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp']

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
  const fileInputRef = useRef<HTMLInputElement>(null)

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
        await documentsApi.upload(file)
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
