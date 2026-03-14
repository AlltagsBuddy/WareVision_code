import { useEffect, useState } from 'react'
import { maintenancePlansApi, manufacturersApi } from '../api/client'

export default function MaintenancePlans() {
  const [plans, setPlans] = useState<any[]>([])
  const [manufacturers, setManufacturers] = useState<any[]>([])
  const [models, setModels] = useState<Record<string, any[]>>({})
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [manufacturerFilter, setManufacturerFilter] = useState('')
  const [form, setForm] = useState({
    manufacturer_id: '',
    vehicle_model_id: '',
    name: '',
    description: '',
    interval_km: '',
    interval_hours: '',
    interval_months: '',
  })
  const [detailPlan, setDetailPlan] = useState<any | null>(null)
  const [tasks, setTasks] = useState<any[]>([])
  const [showTaskForm, setShowTaskForm] = useState(false)
  const [taskForm, setTaskForm] = useState({ name: '', description: '' })
  const [taskSubmitting, setTaskSubmitting] = useState(false)

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
    maintenancePlansApi.getTasks(plan.id).then(setTasks)
  }

  const closeDetail = () => {
    setDetailPlan(null)
    setTasks([])
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
      })
      const updated = await maintenancePlansApi.getTasks(detailPlan.id)
      setTasks(updated)
      setShowTaskForm(false)
      setTaskForm({ name: '', description: '' })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setTaskSubmitting(false)
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

  const getManufacturerName = (id: string) => manufacturers.find((m) => m.id === id)?.name || id
  const getModelName = (manufacturerId: string, modelId: string) => {
    const list = models[manufacturerId] || []
    return list.find((m) => m.id === modelId)?.name || modelId
  }

  const vehicleModels = form.manufacturer_id ? (models[form.manufacturer_id] || []) : []

  return (
    <div className="page">
      <h1>Wartungspläne</h1>
      <div className="toolbar">
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
              <th>Name</th>
              <th>Hersteller</th>
              <th>Modell</th>
              <th>Intervall</th>
            </tr>
          </thead>
          <tbody>
            {plans.map((p) => (
              <tr key={p.id} onClick={() => openDetail(p)} style={{ cursor: 'pointer' }}>
                <td><strong>{p.name}</strong></td>
                <td>{getManufacturerName(p.manufacturer_id)}</td>
                <td>{p.vehicle_model_id ? getModelName(p.manufacturer_id, p.vehicle_model_id) : '–'}</td>
                <td>
                  {[p.interval_km && `${p.interval_km} km`, p.interval_hours && `${p.interval_hours} h`, p.interval_months && `${p.interval_months} Mon.`]
                    .filter(Boolean)
                    .join(' / ') || '–'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}

      {detailPlan && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>{detailPlan.name}</h2>
            <p>
              <strong>Hersteller:</strong> {getManufacturerName(detailPlan.manufacturer_id)} &nbsp;
              <strong>Modell:</strong> {detailPlan.vehicle_model_id ? getModelName(detailPlan.manufacturer_id, detailPlan.vehicle_model_id) : '–'}
            </p>
            {detailPlan.description && <p>{detailPlan.description}</p>}

            <h3>Aufgaben</h3>
            {tasks.length === 0 ? (
              <p>Keine Aufgaben definiert.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {tasks.map((t, i) => (
                  <li key={t.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span>{i + 1}.</span>
                    <span><strong>{t.name}</strong></span>
                    {t.description && <span style={{ color: 'var(--color-text-muted)' }}>– {t.description}</span>}
                    <button type="button" onClick={() => handleDeleteTask(t.id)} className="btn-secondary btn-sm">Entfernen</button>
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
                <div className="form-actions">
                  <button type="button" onClick={() => setShowTaskForm(false)} className="btn-secondary">Abbrechen</button>
                  <button type="submit" disabled={taskSubmitting} className="btn-primary">{taskSubmitting ? 'Speichern...' : 'Hinzufügen'}</button>
                </div>
              </form>
            )}

            <div className="form-actions" style={{ marginTop: '1.5rem' }}>
              <button type="button" onClick={handleDeletePlan} className="btn-secondary" style={{ color: 'var(--color-error)' }}>Plan löschen</button>
              <button type="button" onClick={closeDetail} className="btn-secondary">Schließen</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
