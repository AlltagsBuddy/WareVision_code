import { useEffect, useState } from 'react'
import { auditApi } from '../api/client'

const ACTION_LABELS: Record<string, string> = {
  create: 'Erstellt',
  update: 'Geändert',
  delete: 'Gelöscht',
  dsgvo_anonymize: 'DSGVO: Anonymisiert',
  dsgvo_delete: 'DSGVO: Gelöscht',
  issue: 'Ausgestellt',
  mark_paid: 'Als bezahlt',
  reminder: 'Mahnung',
  email_sent: 'Per E-Mail versendet',
  webhook_termin_marktplatz_import: 'Terminmarktplatz: Import',
  webhook_termin_marktplatz_cancel: 'Terminmarktplatz: Storno',
  webhook_termin_marktplatz_update: 'Terminmarktplatz: Update',
  webhook_termin_marktplatz_error: 'Terminmarktplatz: Fehler',
  termin_marktplatz_cancel_notify: 'Terminmarktplatz: Storno-Benachrichtigung',
  termin_marktplatz_cancel_skip: 'Terminmarktplatz: Storno (ohne Callback)',
}

const ENTITY_LABELS: Record<string, string> = {
  invoice: 'Rechnung',
  document: 'Dokument',
  customer: 'Kunde',
  appointment: 'Termin',
}

export default function AuditLogs() {
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [entityFilter, setEntityFilter] = useState<string>('')
  const [actionFilter, setActionFilter] = useState<string>('')

  useEffect(() => {
    setLoading(true)
    auditApi
      .list({
        entity_type: entityFilter || undefined,
        action: actionFilter || undefined,
        limit: 200,
      })
      .then(setLogs)
      .catch(() => setLogs([]))
      .finally(() => setLoading(false))
  }, [entityFilter, actionFilter])

  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return '–'
    }
  }

  return (
    <div className="page">
      <h1>Audit-Log (Änderungsprotokoll)</h1>
      <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
        Protokollierung von Änderungen für GoBD/DSGVO-Konformität. Nur für Administratoren sichtbar.
      </p>
      <div className="toolbar">
        <select
          value={entityFilter}
          onChange={(e) => setEntityFilter(e.target.value)}
          className="select"
        >
          <option value="">Alle Entitäten</option>
          {Object.entries(ENTITY_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="select"
        >
          <option value="">Alle Aktionen</option>
          {Object.entries(ACTION_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <p>Laden...</p>
      ) : (
        <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr>
              <th>Zeitpunkt</th>
              <th>Entität</th>
              <th>Aktion</th>
              <th>ID</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5}>Keine Einträge vorhanden.</td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td>{formatDate(log.created_at)}</td>
                  <td>{ENTITY_LABELS[log.entity_type] || log.entity_type}</td>
                  <td>{ACTION_LABELS[log.action] || log.action}</td>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                    {log.entity_id ? log.entity_id.slice(0, 8) + '…' : '–'}
                  </td>
                  <td>
                    {log.action === 'email_sent' && log.new_values?.recipient_email && (
                      <span title={JSON.stringify(log.new_values)}>
                        An: {log.new_values.recipient_email}
                        {log.new_values.attachment_filename && ` (${log.new_values.attachment_filename})`}
                      </span>
                    )}
                    {log.action !== 'email_sent' && log.new_values && Object.keys(log.new_values).length > 0 && (
                      <span title={JSON.stringify(log.new_values)}>
                        {Object.entries(log.new_values)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(', ')}
                      </span>
                    )}
                    {log.old_values && Object.keys(log.old_values).length > 0 && !log.new_values && (
                      <span title={JSON.stringify(log.old_values)} style={{ color: 'var(--color-text-muted)' }}>
                        (gelöscht)
                      </span>
                    )}
                    {(!log.new_values || Object.keys(log.new_values).length === 0) &&
                      (!log.old_values || Object.keys(log.old_values).length === 0) &&
                      '–'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        </div>
      )}
    </div>
  )
}
