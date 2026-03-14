import { useEffect, useState } from 'react'
import { usersApi } from '../api/client'
import { useAuth } from '../hooks/useAuth'

export default function Users() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form, setForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    role_id: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([usersApi.list(), usersApi.roles()])
      .then(([u, r]) => {
        setUsers(u)
        setRoles(r)
      })
      .catch(() => setUsers([]))
      .finally(() => setLoading(false))
  }, [])

  const resetForm = () => {
    setForm({ email: '', first_name: '', last_name: '', password: '', role_id: roles[0]?.id || '' })
    setEditing(null)
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.email.trim() || !form.first_name.trim() || !form.last_name.trim()) {
      setError('E-Mail, Vorname und Nachname erforderlich.')
      return
    }
    if (!editing && !form.password) {
      setError('Passwort erforderlich.')
      return
    }
    if (!editing && form.password.length < 6) {
      setError('Passwort mindestens 6 Zeichen.')
      return
    }
    setSubmitting(true)
    try {
      if (editing) {
        const updateData: Record<string, unknown> = {
          first_name: form.first_name,
          last_name: form.last_name,
        }
        if (form.password) updateData.password = form.password
        await usersApi.update(editing.id, updateData)
        setUsers((prev) => prev.map((u) => (u.id === editing.id ? { ...u, ...updateData } : u)))
      } else {
        if (!form.role_id) {
          setError('Rolle erforderlich.')
          return
        }
        await usersApi.create({
          email: form.email.trim(),
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          password: form.password,
          role_id: form.role_id,
        })
        const updated = await usersApi.list()
        setUsers(updated)
      }
      setShowForm(false)
      resetForm()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeactivate = async (u: any) => {
    if (u.id === currentUser?.id) {
      alert('Sie können sich nicht selbst deaktivieren.')
      return
    }
    if (!confirm(`Benutzer "${u.first_name} ${u.last_name}" wirklich deaktivieren?`)) return
    try {
      await usersApi.deactivate(u.id)
      setUsers((prev) => prev.map((x) => (x.id === u.id ? { ...x, is_active: false } : x)))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const openEdit = (u: any) => {
    setEditing(u)
    setForm({
      email: u.email,
      first_name: u.first_name,
      last_name: u.last_name,
      password: '',
      role_id: u.role_id,
    })
    setShowForm(true)
  }

  if (currentUser?.role_name !== 'admin') {
    return (
      <div className="page">
        <h1>Benutzerverwaltung</h1>
        <p className="error">Zugriff verweigert. Administrator-Rechte erforderlich.</p>
      </div>
    )
  }

  return (
    <div className="page">
      <h1>Benutzerverwaltung</h1>
      <div className="toolbar">
        <button type="button" onClick={() => { resetForm(); setShowForm(true) }} className="btn-primary">
          + Neuer Benutzer
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => { setShowForm(false); resetForm() }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? 'Benutzer bearbeiten' : 'Neuer Benutzer'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>E-Mail *</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                  disabled={!!editing}
                  placeholder="user@warevision.local"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Vorname *</label>
                  <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label>Nachname *</label>
                  <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} required />
                </div>
              </div>
              {!editing && (
                <div className="form-group">
                  <label>Rolle *</label>
                  <select value={form.role_id} onChange={(e) => setForm({ ...form, role_id: e.target.value })} required>
                    <option value="">– Bitte wählen –</option>
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>{r.name} – {r.description || ''}</option>
                    ))}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label>{editing ? 'Neues Passwort (leer = unverändert)' : 'Passwort *'}</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  required={!editing}
                  minLength={editing ? undefined : 6}
                  placeholder={editing ? 'Leer lassen zum Beibehalten' : 'Mind. 6 Zeichen'}
                />
              </div>
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => { setShowForm(false); resetForm() }} className="btn-secondary">Abbrechen</button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Speichern...' : (editing ? 'Speichern' : 'Anlegen')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <p>Laden...</p>
      ) : (
        <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>E-Mail</th>
              <th>Rolle</th>
              <th>Status</th>
              <th>Letzter Login</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className={!u.is_active ? 'warning-row' : ''}>
                <td>{u.first_name} {u.last_name}</td>
                <td>{u.email}</td>
                <td>{u.role_name}</td>
                <td>{u.is_active ? 'Aktiv' : 'Deaktiviert'}</td>
                <td>{u.last_login_at ? new Date(u.last_login_at).toLocaleString('de-DE') : '–'}</td>
                <td>
                  <button type="button" onClick={() => openEdit(u)} className="btn-secondary btn-sm">Bearbeiten</button>
                  {u.is_active && (
                    <button type="button" onClick={() => handleDeactivate(u)} className="btn-secondary btn-sm" disabled={u.id === currentUser?.id}>
                      Deaktivieren
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </div>
  )
}
