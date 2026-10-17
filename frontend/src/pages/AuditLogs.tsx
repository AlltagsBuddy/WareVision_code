import { useEffect, useState } from 'react'
import { auditApi } from '../api/client'
import { useDebounced } from '../hooks/useDebounced'

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
  cancel: 'Storniert',
  archive: 'Archiviert (Original)',
  archive_backfill: 'Archiviert (nachträglich)',
  photo_add: 'Foto hinzugefügt',
  photo_delete: 'Foto entfernt',
  item_delete: 'Position entfernt',
  login: 'Anmeldung',
  login_failed: 'Anmeldung fehlgeschlagen',
  barcode_assign: 'Barcode zugeordnet',
  catalog_import: 'Lieferantendaten importiert',
  catalog_delete: 'Lieferantendaten entfernt',
  user_create: 'Benutzer angelegt',
  user_update: 'Benutzer/Rechte geändert',
  user_deactivate: 'Benutzer deaktiviert',
  '2fa_reset': 'Zwei-Faktor zurückgesetzt',
}

const ENTITY_LABELS: Record<string, string> = {
  invoice: 'Rechnung',
  document: 'Dokument',
  customer: 'Kunde',
  appointment: 'Termin',
  workshop_order: 'Werkstattauftrag',
  article: 'Artikel',
  quote: 'Angebot',
  purchase_order: 'Bestellung',
  setting: 'Einstellung',
  supplier: 'Lieferant',
  vehicle: 'Fahrzeug',
  article_category: 'Artikelkategorie',
  storage_location: 'Lagerort',
  labor_rate: 'Stundensatz',
  maintenance_plan: 'Wartungsplan',
  maintenance_task: 'Wartungsaufgabe',
  manufacturer: 'Hersteller',
  vehicle_model: 'Fahrzeugmodell',
  stock_movement: 'Lagerbewegung',
  stock_reservation: 'Reservierung',
  user: 'Benutzer',
  incoming_invoice: 'Eingangsrechnung',
  stock_count: 'Inventur',
  article_catalog: 'Lieferantendaten',
}

/** Änderung lesbar: „Feld: alt → neu“ */
function changeText(log: any): string {
  const nv = log.new_values || {}
  const ov = log.old_values || {}
  const keys = Array.from(new Set([...Object.keys(nv), ...Object.keys(ov)]))
  if (log.action === 'update' && log.old_values) {
    return keys.map((k) => `${k}: ${ov[k] ?? '–'} → ${nv[k] ?? '–'}`).join(', ')
  }
  return Object.entries(nv).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(', ')
}

export default function AuditLogs() {
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [entityFilter, setEntityFilter] = useState<string>('')
  const [actionFilter, setActionFilter] = useState<string>('')
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounced(search.trim())

  useEffect(() => {
    setLoading(true)
    auditApi
      .list({
        entity_type: entityFilter || undefined,
        action: actionFilter || undefined,
        search: debouncedSearch || undefined,
        limit: 200,
      })
      .then(setLogs)
      .catch(() => setLogs([]))
      .finally(() => setLoading(false))
  }, [entityFilter, actionFilter, debouncedSearch])

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
        Protokollierung von Änderungen für GoBD/DSGVO-Konformität. Nur für Administrator und Chef/Chefin sichtbar. Die Spalte „Benutzer“ zeigt, wer die Änderung gemacht hat.
      </p>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Suchen: Benutzer, Nummer, Wert..."
          aria-label="Audit-Log durchsuchen"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
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
              <th>Benutzer</th>
              <th>Entität</th>
              <th>Aktion</th>
              <th>ID</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={6}>Keine Einträge vorhanden.</td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td>{formatDate(log.created_at)}</td>
                  <td title={log.user_email || ''}>{log.user_name || (log.user_id ? 'Unbekannt' : 'System')}</td>
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
                      <span title={JSON.stringify({ vorher: log.old_values, nachher: log.new_values })}>
                        {changeText(log)}
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
