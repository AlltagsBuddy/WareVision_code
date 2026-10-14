import { useEffect, useRef, useState } from 'react'
import { maintenancePlansApi, manufacturersApi, articlesApi } from '../api/client'
import { buildYearLabel } from '../utils/buildYear'

export default function MaintenancePlans() {
  const [plans, setPlans] = useState<any[]>([])
  const [manufacturers, setManufacturers] = useState<any[]>([])
  const [models, setModels] = useState<Record<string, any[]>>({})
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [manufacturerFilter, setManufacturerFilter] = useState('')
  const [planSearch, setPlanSearch] = useState('')
  const [sortField, setSortField] = useState('name')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [form, setForm] = useState({
    manufacturer_id: '',
    vehicle_model_id: '',
    name: '',
    description: '',
    interval_km: '',
    interval_hours: '',
    interval_months: '',
    build_year_from: '',
    build_year_to: '',
  })
  const [detailPlan, setDetailPlan] = useState<any | null>(null)
  const [tasks, setTasks] = useState<any[]>([])
  const [articles, setArticles] = useState<any[]>([])
  const [showTaskForm, setShowTaskForm] = useState(false)
  const [taskForm, setTaskForm] = useState({ name: '', description: '', article_id: '', quantity: '1', unit: 'Stück' })
  const [taskSubmitting, setTaskSubmitting] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({ name: '', description: '', interval_km: '', interval_hours: '', interval_months: '', build_year_from: '', build_year_to: '' })
  const [editSubmitting, setEditSubmitting] = useState(false)
  const [editError, setEditError] = useState('')
  const [editTaskId, setEditTaskId] = useState<string | null>(null)
  const [editTaskForm, setEditTaskForm] = useState({ name: '', description: '', article_id: '', quantity: '1', unit: 'Stück' })
  const [editTaskSubmitting, setEditTaskSubmitting] = useState(false)
  const [docUploading, setDocUploading] = useState(false)
  const [docError, setDocError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const load = () => {
    setLoading(true)
    maintenancePlansApi
      .list({ manufacturer_id: manufacturerFilter || undefined })
      .then(setPlans)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [manufacturerFilter])

  useEffect(() => {
    manufacturersApi.list().then(setManufacturers)
    articlesApi.list({ limit: 200 }).then(setArticles)
  }, [])

  useEffect(() => {
    if (form.manufacturer_id) {
      manufacturersApi.getModels(form.manufacturer_id).then((m) => {
        setModels((prev) => ({ ...prev, [form.manufacturer_id]: m }))
      })
    } else {
      setForm((f) => ({ ...f, vehicle_model_id: '' }))
    }
  }, [form.manufacturer_id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.manufacturer_id || !form.name.trim()) {
      setError('Bitte Hersteller und Name angeben.')
      return
    }
    setSubmitting(true)
    try {
      await maintenancePlansApi.create({
        manufacturer_id: form.manufacturer_id,
        vehicle_model_id: form.vehicle_model_id || undefined,
        name: form.name.trim(),
        description: form.description || undefined,
        interval_km: form.interval_km ? parseInt(form.interval_km, 10) : undefined,
        interval_hours: form.interval_hours ? parseInt(form.interval_hours, 10) : undefined,
        interval_months: form.interval_months ? parseInt(form.interval_months, 10) : undefined,
        build_year_from: form.build_year_from ? parseInt(form.build_year_from, 10) : undefined,
        build_year_to: form.build_year_to ? parseInt(form.build_year_to, 10) : undefined,
      })
      setShowForm(false)
      setForm({
        manufacturer_id: '',
        vehicle_model_id: '',
        name: '',
        description: '',
        interval_km: '',
        interval_hours: '',
        interval_months: '',
        build_year_from: '',
        build_year_to: '',
      })
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setSubmitting(false)
    }
  }

  const openDetail = async (plan: any) => {
    setDetailPlan(plan)
    setShowTaskForm(false)
    setEditMode(false)
    maintenancePlansApi.getTasks(plan.id).then(setTasks)
  }

  const closeDetail = () => {
    setDetailPlan(null)
    setTasks([])
    setEditMode(false)
  }

  const openEditMode = () => {
    setEditForm({
      name: detailPlan.name,
      description: detailPlan.description || '',
      interval_km: detailPlan.interval_km != null ? String(detailPlan.interval_km) : '',
      interval_hours: detailPlan.interval_hours != null ? String(detailPlan.interval_hours) : '',
      interval_months: detailPlan.interval_months != null ? String(detailPlan.interval_months) : '',
      build_year_from: detailPlan.build_year_from != null ? String(detailPlan.build_year_from) : '',
      build_year_to: detailPlan.build_year_to != null ? String(detailPlan.build_year_to) : '',
    })
    setEditError('')
    setEditMode(true)
  }

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editForm.name.trim()) {
      setEditError('Name darf nicht leer sein.')
      return
    }
    setEditSubmitting(true)
    try {
      const updated = await maintenancePlansApi.update(detailPlan.id, {
        name: editForm.name.trim(),
        description: editForm.description || undefined,
        interval_km: editForm.interval_km ? parseInt(editForm.interval_km, 10) : undefined,
        interval_hours: editForm.interval_hours ? parseInt(editForm.interval_hours, 10) : undefined,
        interval_months: editForm.interval_months ? parseInt(editForm.interval_months, 10) : undefined,
        build_year_from: editForm.build_year_from ? parseInt(editForm.build_year_from, 10) : null,
        build_year_to: editForm.build_year_to ? parseInt(editForm.build_year_to, 10) : null,
      })
      setDetailPlan(updated)
      setEditMode(false)
      load()
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Fehler beim Speichern')
    } finally {
      setEditSubmitting(false)
    }
  }

  const handleAddTask = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detailPlan || !taskForm.name.trim()) return
    setTaskSubmitting(true)
    try {
      await maintenancePlansApi.addTask(detailPlan.id, {
        name: taskForm.name.trim(),
        description: taskForm.description || undefined,
        sort_order: tasks.length,
        article_id: taskForm.article_id || undefined,
        quantity: taskForm.article_id ? (parseFloat(taskForm.quantity) || 1) : undefined,
        unit: taskForm.article_id ? (taskForm.unit || 'Stück') : undefined,
      })
      const updated = await maintenancePlansApi.getTasks(detailPlan.id)
      setTasks(updated)
      setShowTaskForm(false)
      setTaskForm({ name: '', description: '', article_id: '', quantity: '1', unit: 'Stück' })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setTaskSubmitting(false)
    }
  }

  const openEditTask = (t: any) => {
    setEditTaskId(t.id)
    setEditTaskForm({
      name: t.name,
      description: t.description || '',
      article_id: t.article_id || '',
      quantity: t.quantity ? String(Number(t.quantity)) : '1',
      unit: t.unit || 'Stück',
    })
    setShowTaskForm(false)
  }

  const handleUpdateTask = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!detailPlan || !editTaskId) return
    setEditTaskSubmitting(true)
    try {
      await maintenancePlansApi.updateTask(detailPlan.id, editTaskId, {
        name: editTaskForm.name.trim(),
        description: editTaskForm.description || undefined,
        article_id: editTaskForm.article_id || null,
        quantity: parseFloat(editTaskForm.quantity) || 1,
        unit: editTaskForm.article_id ? (editTaskForm.unit || 'Stück') : null,
      })
      const updated = await maintenancePlansApi.getTasks(detailPlan.id)
      setTasks(updated)
      setEditTaskId(null)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setEditTaskSubmitting(false)
    }
  }

  const handleDeleteTask = async (taskId: string) => {
    if (!detailPlan || !confirm('Aufgabe wirklich entfernen?')) return
    try {
      await maintenancePlansApi.deleteTask(detailPlan.id, taskId)
      setTasks((prev) => prev.filter((t) => t.id !== taskId))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleDeletePlan = async () => {
    if (!detailPlan || !confirm('Wartungsplan wirklich löschen?')) return
    try {
      await maintenancePlansApi.delete(detailPlan.id)
      closeDetail()
      load()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleDocumentUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !detailPlan) return
    setDocError('')
    setDocUploading(true)
    try {
      const updated = await maintenancePlansApi.uploadDocument(detailPlan.id, file)
      setDetailPlan(updated)
      load()
    } catch (err) {
      setDocError(err instanceof Error ? err.message : 'Upload fehlgeschlagen')
    } finally {
      setDocUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDocumentDelete = async () => {
    if (!detailPlan || !confirm('Dokument wirklich entfernen?')) return
    setDocError('')
    try {
      await maintenancePlansApi.deleteDocument(detailPlan.id)
      setDetailPlan({ ...detailPlan, document_id: null, document_filename: null })
      load()
    } catch (err) {
      setDocError(err instanceof Error ? err.message : 'Fehler beim Entfernen')
    }
  }

  const handleDocumentDownload = () => {
    if (!detailPlan?.document_id) return
    const token = localStorage.getItem('token')
    const url = maintenancePlansApi.getDocumentUrl(detailPlan.id)
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = detailPlan.document_filename || 'dokument'
        a.click()
        URL.revokeObjectURL(a.href)
      })
      .catch(() => alert('Download fehlgeschlagen'))
  }

  const getManufacturerName = (id: string) => manufacturers.find((m) => m.id === id)?.name || id
  const getModelName = (manufacturerId: string, modelId: string) => {
    const list = models[manufacturerId] || []
    return list.find((m) => m.id === modelId)?.name || modelId
  }

  const vehicleModels = form.manufacturer_id ? (models[form.manufacturer_id] || []) : []

  const handleSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortField(field); setSortDir('asc') }
  }
  const sortIcon = (field: string) => sortField === field ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ↕'

  const pq = planSearch.toLowerCase()
  const displayedPlans = [...plans]
    .filter((p) => {
      if (!pq) return true
      const manuName = getManufacturerName(p.manufacturer_id).toLowerCase()
      const modelList = p.manufacturer_id ? (models[p.manufacturer_id] || []) : []
      const modelEntry = modelList.find((m: any) => m.id === p.vehicle_model_id)
      const modelName = modelEntry ? (modelEntry.name || '').toLowerCase() : ''
      return (
        (p.name || '').toLowerCase().includes(pq) ||
        manuName.includes(pq) ||
        modelName.includes(pq)
      )
    })
    .sort((a, b) => {
      let va = '', vb = ''
      if (sortField === 'manufacturer') { va = getManufacturerName(a.manufacturer_id); vb = getManufacturerName(b.manufacturer_id) }
      else if (sortField === 'created_at') { va = a.created_at || ''; vb = b.created_at || '' }
      else { va = a.name || ''; vb = b.name || '' }
      return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va)
    })

  return (
    <div className="page">
      <h1>Wartungspläne</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Name, Hersteller, Modell..."
          value={planSearch}
          onChange={(e) => setPlanSearch(e.target.value)}
        />
        <select
          value={manufacturerFilter}
          onChange={(e) => setManufacturerFilter(e.target.value)}
          className="select"
        >
          <option value="">Alle Hersteller</option>
          {manufacturers.map((m) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
        <button type="button" onClick={() => setShowForm(true)} className="btn-primary">
          + Neuer Wartungsplan
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Neuer Wartungsplan</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Hersteller *</label>
                <select
                  value={form.manufacturer_id}
                  onChange={(e) => setForm({ ...form, manufacturer_id: e.target.value, vehicle_model_id: '' })}
                  required
                >
                  <option value="">– Bitte wählen –</option>
                  {manufacturers.map((m) => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Modell (optional)</label>
                <select
                  value={form.vehicle_model_id}
                  onChange={(e) => setForm({ ...form, vehicle_model_id: e.target.value })}
                  disabled={!form.manufacturer_id}
                >
                  <option value="">– Alle Modelle –</option>
                  {vehicleModels.map((m) => (
                    <option key={m.id} value={m.id}>{m.name} {m.variant ? `(${m.variant})` : ''}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Name *</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="z.B. Kleine Inspektion"
                  required
                />
              </div>
              <div className="form-group">
                <label>Beschreibung</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  rows={2}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Intervall (km)</label>
                  <input
                    type="number"
                    value={form.interval_km}
                    onChange={(e) => setForm({ ...form, interval_km: e.target.value })}
                    placeholder="z.B. 10000"
                  />
                </div>
                <div className="form-group">
                  <label>Intervall (Stunden)</label>
                  <input
                    type="number"
                    value={form.interval_hours}
                    onChange={(e) => setForm({ ...form, interval_hours: e.target.value })}
                    placeholder="z.B. 100"
                  />
                </div>
                <div className="form-group">
                  <label>Intervall (Monate)</label>
                  <input
                    type="number"
                    value={form.interval_months}
                    onChange={(e) => setForm({ ...form, interval_months: e.target.value })}
                    placeholder="z.B. 12"
                  />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="mp-year-from">Baujahr von</label>
                  <input id="mp-year-from" type="number" min={1900} max={2100} value={form.build_year_from}
                    onChange={(e) => setForm({ ...form, build_year_from: e.target.value })} placeholder="leer = alle" />
                </div>
                <div className="form-group">
                  <label htmlFor="mp-year-to">Baujahr bis</label>
                  <input id="mp-year-to" type="number" min={1900} max={2100} value={form.build_year_to}
                    onChange={(e) => setForm({ ...form, build_year_to: e.target.value })} placeholder="z.B. 2012 für ältere Fahrzeuge" />
                </div>
              </div>
              <p style={{ marginTop: 0, fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>Ohne Baujahr gilt der Plan für alle Baujahre. Passt ein Plan mit Baujahr, wird er bevorzugt.</p>
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Abbrechen</button>
                <button type="submit" disabled={submitting} className="btn-primary">{submitting ? 'Speichern...' : 'Anlegen'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <p>Laden...</p>
      ) : plans.length === 0 ? (
        <p>Keine Wartungspläne vorhanden.</p>
      ) : (
        <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr>
              <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>Name{sortIcon('name')}</th>
              <th onClick={() => handleSort('manufacturer')} style={{ cursor: 'pointer' }}>Hersteller{sortIcon('manufacturer')}</th>
              <th>Modell</th>
              <th>Baujahre</th>
              <th>Intervall</th>
              <th onClick={() => handleSort('created_at')} style={{ cursor: 'pointer' }}>Erstellt{sortIcon('created_at')}</th>
            </tr>
          </thead>
          <tbody>
            {displayedPlans.map((p) => (
              <tr key={p.id} onClick={() => openDetail(p)} style={{ cursor: 'pointer' }}>
                <td><strong>{p.name}</strong></td>
                <td>{getManufacturerName(p.manufacturer_id)}</td>
                <td>{p.vehicle_model_id ? getModelName(p.manufacturer_id, p.vehicle_model_id) : '–'}</td>
                <td>{buildYearLabel(p)}</td>
                <td>
                  {[p.interval_km && `${p.interval_km} km`, p.interval_hours && `${p.interval_hours} h`, p.interval_months && `${p.interval_months} Mon.`]
                    .filter(Boolean)
                    .join(' / ') || '–'}
                </td>
                <td>{p.created_at ? new Date(p.created_at).toLocaleDateString('de-DE') : '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}

      {detailPlan && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            {editMode ? (
              <>
                <h2>Wartungsplan bearbeiten</h2>
                <form onSubmit={handleEditSubmit}>
                  <div className="form-group">
                    <label>Name *</label>
                    <input
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Beschreibung</label>
                    <textarea
                      value={editForm.description}
                      onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                      rows={2}
                    />
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label>Intervall (km)</label>
                      <input
                        type="number"
                        value={editForm.interval_km}
                        onChange={(e) => setEditForm({ ...editForm, interval_km: e.target.value })}
                        placeholder="z.B. 10000"
                      />
                    </div>
                    <div className="form-group">
                      <label>Intervall (Stunden)</label>
                      <input
                        type="number"
                        value={editForm.interval_hours}
                        onChange={(e) => setEditForm({ ...editForm, interval_hours: e.target.value })}
                        placeholder="z.B. 100"
                      />
                    </div>
                    <div className="form-group">
                      <label>Intervall (Monate)</label>
                      <input
                        type="number"
                        value={editForm.interval_months}
                        onChange={(e) => setEditForm({ ...editForm, interval_months: e.target.value })}
                        placeholder="z.B. 12"
                      />
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="form-group">
                      <label htmlFor="mp-edit-year-from">Baujahr von</label>
                      <input id="mp-edit-year-from" type="number" min={1900} max={2100} value={editForm.build_year_from}
                        onChange={(e) => setEditForm({ ...editForm, build_year_from: e.target.value })} placeholder="leer = alle" />
                    </div>
                    <div className="form-group">
                      <label htmlFor="mp-edit-year-to">Baujahr bis</label>
                      <input id="mp-edit-year-to" type="number" min={1900} max={2100} value={editForm.build_year_to}
                        onChange={(e) => setEditForm({ ...editForm, build_year_to: e.target.value })} placeholder="leer = alle" />
                    </div>
                  </div>
                  {editError && <p className="error">{editError}</p>}
                  <div className="form-actions">
                    <button type="button" onClick={() => setEditMode(false)} className="btn-secondary">Abbrechen</button>
                    <button type="submit" disabled={editSubmitting} className="btn-primary">{editSubmitting ? 'Speichern...' : 'Speichern'}</button>
                  </div>
                </form>
              </>
            ) : (
              <>
                <h2>{detailPlan.name}</h2>
                <p>
                  <strong>Hersteller:</strong> {getManufacturerName(detailPlan.manufacturer_id)} &nbsp;
                  <strong>Modell:</strong> {detailPlan.vehicle_model_id ? getModelName(detailPlan.manufacturer_id, detailPlan.vehicle_model_id) : '–'} &nbsp;
                  <strong>Baujahre:</strong> {buildYearLabel(detailPlan)}
                </p>
                {detailPlan.description && <p>{detailPlan.description}</p>}

                <h3>Hersteller-Dokument</h3>
                {detailPlan.document_id ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.9rem' }}>{detailPlan.document_filename || 'Dokument'}</span>
                    <button type="button" onClick={handleDocumentDownload} className="btn-secondary btn-sm">
                      Herunterladen
                    </button>
                    <button type="button" onClick={() => fileInputRef.current?.click()} className="btn-secondary btn-sm">
                      Ersetzen
                    </button>
                    <button type="button" onClick={handleDocumentDelete} className="btn-secondary btn-sm" style={{ color: 'var(--color-error)' }}>
                      Entfernen
                    </button>
                  </div>
                ) : (
                  <div style={{ marginBottom: '0.75rem' }}>
                    <button type="button" onClick={() => fileInputRef.current?.click()} className="btn-secondary btn-sm" disabled={docUploading}>
                      {docUploading ? 'Wird hochgeladen…' : '+ Dokument hochladen (PDF)'}
                    </button>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,image/jpeg,image/png"
                  style={{ display: 'none' }}
                  onChange={handleDocumentUpload}
                />
                {docError && <p className="error" style={{ marginBottom: '0.75rem' }}>{docError}</p>}

                <h3>Aufgaben</h3>
                {tasks.length === 0 ? (
                  <p>Keine Aufgaben definiert.</p>
                ) : (
                  <ul style={{ listStyle: 'none', padding: 0 }}>
                    {tasks.map((t, i) => (
                      <li key={t.id} style={{ marginBottom: '0.5rem', borderBottom: '1px solid var(--color-border)' }}>
                        {editTaskId === t.id ? (
                          <form onSubmit={handleUpdateTask} style={{ padding: '0.75rem', background: 'var(--color-surface-2)', borderRadius: 6 }}>
                            <div className="form-group">
                              <label>Name *</label>
                              <input
                                value={editTaskForm.name}
                                onChange={(e) => setEditTaskForm({ ...editTaskForm, name: e.target.value })}
                                required
                              />
                            </div>
                            <div className="form-group">
                              <label>Beschreibung</label>
                              <input
                                value={editTaskForm.description}
                                onChange={(e) => setEditTaskForm({ ...editTaskForm, description: e.target.value })}
                              />
                            </div>
                            <div className="form-group">
                              <label>Benötigter Artikel (optional)</label>
                              <select
                                value={editTaskForm.article_id}
                                onChange={(e) => setEditTaskForm({ ...editTaskForm, article_id: e.target.value })}
                              >
                                <option value="">– Kein Artikel –</option>
                                {articles.map((a) => (
                                  <option key={a.id} value={a.id}>{a.article_number} – {a.name}</option>
                                ))}
                              </select>
                            </div>
                            {editTaskForm.article_id && (
                              <div className="form-row">
                                <div className="form-group">
                                  <label>Menge</label>
                                  <input
                                    type="number"
                                    step="0.01"
                                    min="0.01"
                                    value={editTaskForm.quantity}
                                    onChange={(e) => setEditTaskForm({ ...editTaskForm, quantity: e.target.value })}
                                  />
                                </div>
                                <div className="form-group">
                                  <label>Einheit</label>
                                  <input
                                    value={editTaskForm.unit}
                                    onChange={(e) => setEditTaskForm({ ...editTaskForm, unit: e.target.value })}
                                    placeholder="Stück, Liter, ..."
                                  />
                                </div>
                              </div>
                            )}
                            <div className="form-actions">
                              <button type="button" onClick={() => setEditTaskId(null)} className="btn-secondary">Abbrechen</button>
                              <button type="submit" disabled={editTaskSubmitting} className="btn-primary">
                                {editTaskSubmitting ? 'Speichern...' : 'Speichern'}
                              </button>
                            </div>
                          </form>
                        ) : (
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', padding: '0.4rem 0' }}>
                            <span style={{ minWidth: 20, paddingTop: 2 }}>{i + 1}.</span>
                            <div style={{ flex: 1 }}>
                              <strong>{t.name}</strong>
                              {t.description && <span style={{ color: 'var(--color-text-muted)' }}> – {t.description}</span>}
                              {t.article_id ? (
                                <div style={{ fontSize: '0.82rem', color: 'var(--color-primary)', marginTop: 2 }}>
                                  Artikel: {t.article_number} {t.article_name} &nbsp;·&nbsp; {Number(t.quantity)} {t.unit || 'Stück'}
                                </div>
                              ) : (
                                <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
                                  Kein Artikel verknüpft
                                </div>
                              )}
                            </div>
                            <button type="button" onClick={() => openEditTask(t)} className="btn-secondary btn-sm">Bearbeiten</button>
                            <button type="button" onClick={() => handleDeleteTask(t.id)} className="btn-secondary btn-sm">Entfernen</button>
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                )}

                {!showTaskForm ? (
                  <button type="button" onClick={() => setShowTaskForm(true)} className="btn-primary" style={{ marginTop: '0.5rem' }}>
                    + Aufgabe hinzufügen
                  </button>
                ) : (
                  <form onSubmit={handleAddTask} style={{ marginTop: '1rem', padding: '1rem', border: '1px solid var(--color-border)', borderRadius: 8 }}>
                    <h4>Neue Aufgabe</h4>
                    <div className="form-group">
                      <label>Name *</label>
                      <input
                        value={taskForm.name}
                        onChange={(e) => setTaskForm({ ...taskForm, name: e.target.value })}
                        placeholder="z.B. Öl wechseln"
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Beschreibung</label>
                      <input
                        value={taskForm.description}
                        onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })}
                        placeholder="Optional"
                      />
                    </div>
                    <div className="form-group">
                      <label>Benötigter Artikel (optional – wird automatisch in Werkstattauftrag übernommen)</label>
                      <select
                        value={taskForm.article_id}
                        onChange={(e) => setTaskForm({ ...taskForm, article_id: e.target.value })}
                      >
                        <option value="">– Kein Artikel –</option>
                        {articles.map((a) => (
                          <option key={a.id} value={a.id}>{a.article_number} – {a.name}</option>
                        ))}
                      </select>
                    </div>
                    {taskForm.article_id && (
                      <div className="form-row">
                        <div className="form-group">
                          <label>Menge</label>
                          <input
                            type="number"
                            step="0.01"
                            min="0.01"
                            value={taskForm.quantity}
                            onChange={(e) => setTaskForm({ ...taskForm, quantity: e.target.value })}
                          />
                        </div>
                        <div className="form-group">
                          <label>Einheit</label>
                          <input
                            value={taskForm.unit}
                            onChange={(e) => setTaskForm({ ...taskForm, unit: e.target.value })}
                            placeholder="Stück, Liter, ..."
                          />
                        </div>
                      </div>
                    )}
                    <div className="form-actions">
                      <button type="button" onClick={() => setShowTaskForm(false)} className="btn-secondary">Abbrechen</button>
                      <button type="submit" disabled={taskSubmitting} className="btn-primary">{taskSubmitting ? 'Speichern...' : 'Hinzufügen'}</button>
                    </div>
                  </form>
                )}

                <div className="form-actions" style={{ marginTop: '1.5rem' }}>
                  <button type="button" onClick={handleDeletePlan} className="btn-secondary" style={{ color: 'var(--color-error)' }}>Plan löschen</button>
                  <button type="button" onClick={openEditMode} className="btn-secondary">Bearbeiten</button>
                  <button type="button" onClick={closeDetail} className="btn-secondary">Schließen</button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

