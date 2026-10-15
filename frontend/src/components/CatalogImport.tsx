/**
 * Lieferanten-Artikeldaten verwalten: Artikeldatei (CSV/Excel) einlesen, Spalten zuordnen, importieren.
 * Die Daten sind nur Vorschläge beim Anlegen eines Artikels per Barcode – Lagerartikel bleiben unverändert.
 */
import { useEffect, useState } from 'react'
import { catalogApi, suppliersApi } from '../api/client'

type Preview = Awaited<ReturnType<typeof catalogApi.preview>>
type Source = Awaited<ReturnType<typeof catalogApi.sources>>[number]

const SOURCE_LABEL: Record<string, string> = { import: 'Artikeldatei', einvoice: 'aus E-Rechnungen' }

export default function CatalogImport({ onClose }: { onClose: () => void }) {
  const [sources, setSources] = useState<Source[]>([])
  const [suppliers, setSuppliers] = useState<any[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<Preview | null>(null)
  const [mapping, setMapping] = useState<Record<string, number | null>>({})
  const [supplierId, setSupplierId] = useState('')
  const [supplierName, setSupplierName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState('')

  const loadSources = () => catalogApi.sources().then(setSources).catch(() => setSources([]))

  useEffect(() => {
    loadSources()
    suppliersApi.list().then(setSuppliers).catch(() => setSuppliers([]))
  }, [])

  const choose = async (f: File | undefined) => {
    setError('')
    setResult('')
    setPreview(null)
    setFile(f || null)
    if (!f) return
    setBusy(true)
    try {
      const p = await catalogApi.preview(f)
      setPreview(p)
      setMapping(p.mapping)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setBusy(false)
    }
  }

  const runImport = async () => {
    if (!file || !preview) return
    setError('')
    if (!supplierId && !supplierName.trim()) {
      setError('Bitte den Lieferanten wählen oder eintragen.')
      return
    }
    setBusy(true)
    try {
      const r = await catalogApi.importFile(file, mapping, supplierId ? { id: supplierId } : { name: supplierName.trim() })
      setResult(`${r.supplier_name}: ${r.created} neu, ${r.updated} aktualisiert`
        + (r.skipped ? `, ${r.skipped} Zeile(n) ohne Bezeichnung oder ohne Barcode/Artikelnummer übersprungen` : '') + '.')
      setFile(null)
      setPreview(null)
      loadSources()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setBusy(false)
    }
  }

  const removeSource = async (name: string) => {
    if (!confirm(`Alle Artikeldaten von „${name}“ entfernen? Eure Lagerartikel bleiben unverändert.`)) return
    try {
      await catalogApi.remove(name)
      loadSources()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const fmt = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString('de-DE') : '–')
  const used = new Set(Object.values(mapping).filter((v) => v !== null))

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-wide" role="dialog" aria-label="Lieferanten-Artikeldaten" onClick={(e) => e.stopPropagation()}>
        <h2>Lieferanten-Artikeldaten</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Artikeldatei eures Großhändlers (Excel oder CSV) einlesen. Beim Anlegen eines Artikels füllt ein Scan des
          Barcodes dann Bezeichnung, Hersteller, Bestellnummer und Preise vor – ihr prüft nur noch und speichert.
          Positionen aus Lieferanten-E-Rechnungen kommen automatisch dazu.
        </p>

        {sources.length > 0 && (
          <div className="table-wrapper" style={{ marginBottom: '1rem' }}>
            <table className="table">
              <thead><tr><th>Lieferant</th><th>Quelle</th><th>Artikel</th><th>Stand</th><th /></tr></thead>
              <tbody>
                {sources.map((s) => (
                  <tr key={`${s.supplier_name}-${s.source}`}>
                    <td>{s.supplier_name}</td>
                    <td>{SOURCE_LABEL[s.source] || s.source}</td>
                    <td>{s.count.toLocaleString('de-DE')}</td>
                    <td>{fmt(s.updated_at)}</td>
                    <td>
                      <button type="button" className="btn-secondary btn-sm" onClick={() => removeSource(s.supplier_name)}>
                        Entfernen
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="form-group">
          <label htmlFor="catalog-file">Artikeldatei (.xlsx oder .csv, höchstens 20 MB)</label>
          <input id="catalog-file" type="file" accept=".xlsx,.xlsm,.csv,.txt,text/csv"
            onChange={(e) => choose(e.target.files?.[0])} disabled={busy} />
        </div>

        {busy && !preview && <p>Datei wird gelesen…</p>}

        {preview && (
          <>
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="catalog-supplier">Lieferant</label>
                <select id="catalog-supplier" value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
                  <option value="">– anderer (unten eintragen) –</option>
                  {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              {!supplierId && (
                <div className="form-group">
                  <label htmlFor="catalog-supplier-name">Name des Lieferanten</label>
                  <input id="catalog-supplier-name" value={supplierName} onChange={(e) => setSupplierName(e.target.value)} />
                </div>
              )}
            </div>

            <p style={{ margin: '0.5rem 0' }}>
              <strong>{preview.row_count.toLocaleString('de-DE')}</strong> Zeilen erkannt. Bitte prüfen, welche Spalte
              zu welchem Feld gehört (Vorschlag ist eingetragen):
            </p>
            <div className="form-row" style={{ flexWrap: 'wrap' }}>
              {preview.fields.map((f) => (
                <div className="form-group" key={f.key} style={{ minWidth: 220, flex: '1 1 220px' }}>
                  <label htmlFor={`map-${f.key}`}>
                    {f.label}{f.key === 'name' ? ' *' : ''}
                  </label>
                  <select
                    id={`map-${f.key}`}
                    value={mapping[f.key] ?? ''}
                    onChange={(e) => setMapping((m) => ({ ...m, [f.key]: e.target.value === '' ? null : Number(e.target.value) }))}
                  >
                    <option value="">– nicht vorhanden –</option>
                    {preview.headers.map((h, i) => (
                      <option key={i} value={i} disabled={used.has(i) && mapping[f.key] !== i}>
                        {h || `Spalte ${i + 1}`}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <div className="table-wrapper">
              <table className="table" style={{ fontSize: '0.8rem' }}>
                <thead><tr>{preview.headers.map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
                <tbody>
                  {preview.sample.map((r, i) => (
                    <tr key={i}>{preview.headers.map((_, j) => <td key={j}>{r[j] ?? ''}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted" style={{ fontSize: '0.85rem' }}>
              Schon vorhandene Einträge desselben Lieferanten (gleiche Artikelnummer) werden aktualisiert, z. B. neue
              Preise. UVP inkl. MwSt wird in einen Netto-Verkaufspreis umgerechnet.
            </p>
          </>
        )}

        {result && <p className="success" role="status">{result}</p>}
        {error && <p className="error" role="alert">{error}</p>}
        <div className="form-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>Schließen</button>
          {preview && (
            <button type="button" className="btn-primary" disabled={busy || mapping.name == null} onClick={runImport}>
              {busy ? 'Importiere…' : 'Importieren'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
