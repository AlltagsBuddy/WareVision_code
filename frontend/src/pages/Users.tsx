import { useEffect, useState } from 'react'
import { usersApi } from '../api/client'
import { useAuth } from '../hooks/useAuth'

const MODULES = [
  { key: 'customers', label: 'Kunden' },
  { key: 'vehicles', label: 'Fahrzeuge' },
  { key: 'articles', label: 'Artikel' },
  { key: 'suppliers', label: 'Lieferanten' },
  { key: 'stock', label: 'Lager' },
  { key: 'stock_counts', label: 'Inventur' },
  { key: 'quotes', label: 'Angebote' },
  { key: 'workshop_orders', label: 'Werkstattauftraege' },
  { key: 'maintenance_plans', label: 'Wartungsplaene' },
  { key: 'appointments', label: 'Terminplaner' },
  { key: 'invoices', label: 'Rechnungen' },
  { key: 'documents', label: 'Dokumente' },
]

const DEFAULT_PERMS = Object.fromEntries(
  MODULES.map((m) => [m.key, { visible: true, write: true }])
)

type PermMap = Record<string, { visible: boolean; write: boolean }>

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
  const [permissions, setPermissions] = useState<PermMap>({ ...DEFAULT_PERMS })
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
    setPermissions({ ...DEFAULT_PERMS })
    setEditing(null)
    setError('')
  }

  const isAdminRole = (roleId: string) => {
    const role = roles.find((r) => r.id === roleId)
    return role?.name === 'admin'
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
          email: form.email.trim(),
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          role_id: form.role_id,
          permissions: isAdminRole(form.role_id) ? null : permissions,
        }
        if (form.password) updateData.password = form.password
        await usersApi.update(editing.id, updateData)
        const updated = await usersApi.list()
        setUsers(updated)
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
          permissions: isAdminRole(form.role_id) ? undefined : permissions,
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
      alert('Sie koennen sich nicht selbst deaktivieren.')
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

  const handleActivate = async (u: any) => {
    if (!confirm(`Benutzer "${u.first_name} ${u.last_name}" freischalten?`)) return
    try {
      await usersApi.update(u.id, { is_active: true })
      setUsers((prev) => prev.map((x) => (x.id === u.id ? { ...x, is_active: true } : x)))
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
    // Berechtigungen aus dem Benutzer laden, Standardwerte fuer fehlende Module
    const perms: PermMap = {}
    MODULES.forEach((m) => {
      perms[m.key] = {
        visible: u.permissions?.[m.key]?.visible !== false,
        write: u.permissions?.[m.key]?.write !== false,
      }
    })
    setPermissions(perms)
    setShowForm(true)
  }

  const togglePerm = (module: string, field: 'visible' | 'write', value: boolean) => {
    setPermissions((prev) => {
      const updated = { ...prev, [module]: { ...prev[module], [field]: value } }
      // Wenn nicht sichtbar, auch kein Schreibrecht
      if (field === 'visible' && !value) {
        updated[module].write = false
      }
      // Wenn Schreibrecht, automatisch sichtbar
      if (field === 'write' && value) {
        updated[module].visible = true
      }
      return updated
    })
  }

  const setAllVisible = (visible: boolean) => {
    setPermissions(Object.fromEntries(
      MODULES.map((m) => [m.key, { visible, write: visible ? permissions[m.key]?.write ?? true : false }])
    ))
  }

  const setAllWrite = (write: boolean) => {
    setPermissions(Object.fromEntries(
      MODULES.map((m) => [m.key, {
        visible: write ? true : permissions[m.key]?.visible ?? true,
        write,
      }])
    ))
  }

  const showingAdminRole = isAdminRole(form.role_id)

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
          <div className="modal" style={{ maxWidth: 600 }} onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? 'Benutzer bearbeiten' : 'Neuer Benutzer'}</h2>
            <form onSubmit={handleSubmit}>

              {/* Stammdaten */}
              <div style={{ fontWeight: 600, fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', marginBottom: '0.5rem' }}>
                Benutzerdaten
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Vorname *</label>
                  <input
                    value={form.first_name}
                    onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                    placeholder="Max"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Nachname *</label>
                  <input
                    value={form.last_name}
                    onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                    placeholder="Mustermann"
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label>E-Mail (Login) *</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                  placeholder="user@warevision.local"
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Rolle *</label>
                  <select
                    value={form.role_id}
                    onChange={(e) => setForm({ ...form, role_id: e.target.value })}
                    required
                  >
                    <option value="">- Bitte waehlen -</option>
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>{r.name}{r.description ? ` - ${r.description}` : ''}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>{editing ? 'Neues Passwort (leer = unveraendert)' : 'Passwort *'}</label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    required={!editing}
                    minLength={editing ? undefined : 6}
                    placeholder={editing ? 'Leer lassen' : 'Mind. 6 Zeichen'}
                  />
                </div>
              </div>

              {/* Berechtigungen - nur fuer Nicht-Admin-Rollen */}
              {!showingAdminRole && (
                <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem', marginTop: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)' }}>
                      Modulberechtigungen
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.78rem' }}>
                      <button type="button" className="btn-secondary btn-sm" onClick={() => { setAllVisible(true); setAllWrite(true) }}>Alle an</button>
                      <button type="button" className="btn-secondary btn-sm" onClick={() => setAllVisible(false)}>Alle aus</button>
                    </div>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginBottom: '0.5rem', marginTop: 0 }}>
                    Loeschen ist generell nur Admins erlaubt.
                  </p>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', padding: '0.25rem 0.5rem', fontWeight: 600, borderBottom: '1px solid var(--color-border)' }}>Modul</th>
                        <th style={{ textAlign: 'center', padding: '0.25rem 0.5rem', fontWeight: 600, borderBottom: '1px solid var(--color-border)', width: 80 }}>
                          Sichtbar
                          <div style={{ fontSize: '0.7rem', fontWeight: 400 }}>
                            <label style={{ cursor: 'pointer' }}>
                              <input type="checkbox" checked={MODULES.every((m) => permissions[m.key]?.visible)} onChange={(e) => setAllVisible(e.target.checked)} style={{ marginRight: 2 }} />
                              alle
                            </label>
                          </div>
                        </th>
                        <th style={{ textAlign: 'center', padding: '0.25rem 0.5rem', fontWeight: 600, borderBottom: '1px solid var(--color-border)', width: 80 }}>
                          Schreiben
                          <div style={{ fontSize: '0.7rem', fontWeight: 400 }}>
                            <label style={{ cursor: 'pointer' }}>
                              <input type="checkbox" checked={MODULES.every((m) => permissions[m.key]?.write)} onChange={(e) => setAllWrite(e.target.checked)} style={{ marginRight: 2 }} />
                              alle
                            </label>
                          </div>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {MODULES.map((m) => (
                        <tr key={m.key} style={{ borderBottom: '1px solid var(--color-border)' }}>
                          <td style={{ padding: '0.3rem 0.5rem' }}>{m.label}</td>
                          <td style={{ textAlign: 'center', padding: '0.3rem 0.5rem' }}>
                            <input
                              type="checkbox"
                              checked={permissions[m.key]?.visible ?? true}
                              onChange={(e) => togglePerm(m.key, 'visible', e.target.checked)}
                              style={{ cursor: 'pointer', width: 16, height: 16 }}
                            />
                          </td>
                          <td style={{ textAlign: 'center', padding: '0.3rem 0.5rem' }}>
                            <input
                              type="checkbox"
                              checked={permissions[m.key]?.write ?? true}
                              disabled={!permissions[m.key]?.visible}
                              onChange={(e) => togglePerm(m.key, 'write', e.target.checked)}
                              style={{ cursor: permissions[m.key]?.visible ? 'pointer' : 'not-allowed', width: 16, height: 16 }}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {showingAdminRole && (
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-border)', paddingTop: '0.75rem', marginTop: '0.5rem' }}>
                  Admins haben automatisch Zugriff auf alle Module.
                </p>
              )}

              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => { setShowForm(false); resetForm() }} className="btn-secondary">Abbrechen</button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Speichern...' : editing ? 'Speichern' : 'Anlegen'}
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
                <th>Module</th>
                <th>Status</th>
                <th>Letzter Login</th>
                <th>Aktionen</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const isAdmin = u.role_name === 'admin'
                const visibleCount = isAdmin
                  ? MODULES.length
                  : MODULES.filter((m) => u.permissions?.[m.key]?.visible !== false).length
                const writeCount = isAdmin
                  ? MODULES.length
                  : MODULES.filter((m) => u.permissions?.[m.key]?.write !== false).length
                return (
                  <tr key={u.id} className={!u.is_active ? 'warning-row' : ''}>
                    <td>
                      <strong>{u.first_name} {u.last_name}</strong>
                      {u.id === currentUser?.id && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginLeft: '0.4rem' }}>(Sie)</span>
                      )}
                    </td>
                    <td>{u.email}</td>
                    <td>{u.role_name}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                      {isAdmin ? (
                        <span>Alle Rechte</span>
                      ) : (
                        <span>{visibleCount} sichtbar, {writeCount} schreiben</span>
                      )}
                    </td>
                    <td>
                      {u.is_active
                        ? 'Aktiv'
                        : <span style={{ color: 'var(--color-warning, orange)', fontWeight: 600 }}>Inaktiv</span>
                      }
                    </td>
                    <td>{u.last_login_at ? new Date(u.last_login_at).toLocaleString('de-DE') : '-'}</td>
                    <td>
                      <button type="button" onClick={() => openEdit(u)} className="btn-secondary btn-sm">
                        Bearbeiten
                      </button>
                      {u.is_active ? (
                        <button
                          type="button"
                          onClick={() => handleDeactivate(u)}
                          className="btn-secondary btn-sm"
                          disabled={u.id === currentUser?.id}
                        >
                          Deaktivieren
                        </button>
                      ) : (
                        <button type="button" onClick={() => handleActivate(u)} className="btn-primary btn-sm">
                          Freischalten
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
