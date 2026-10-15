import { useEffect, useMemo, useRef, useState } from 'react'
import { stockCountsApi, storageLocationsApi, articleCategoriesApi } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import BarcodeScanner from '../components/BarcodeScanner'
import PreviewModal from '../components/PreviewModal'
import { hasRight } from '../utils/permissions'

const STATUS_LABELS: Record<string, string> = {
  open: 'Zählung läuft',
  completed: 'Abgeschlossen',
  cancelled: 'Abgebrochen',
}
const STATUS_COLORS: Record<string, string> = {
  open: '#60a5fa',
  completed: '#4ade80',
  cancelled: 'var(--color-text-muted, #888)',
}

const today = () => new Date().toISOString().slice(0, 10)
const formatDate = (d?: string | null) => {
  if (!d) return '–'
  const [y, m, day] = d.slice(0, 10).split('-')
  return `${day}.${m}.${y}`
}
const formatEuro = (v: number | string | null | undefined) =>
  v == null ? '–' : Number(v).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })
const diffColor = (d: number) => (d > 0 ? '#4ade80' : d < 0 ? '#f87171' : undefined)
const fmtDiff = (d: number) => (d > 0 ? `+${d}` : String(d))

export default function StockCounts() {
  const { user } = useAuth()
  // Inventur starten/abschließen/stornieren: Sonderrecht „Lager & Einkauf“
  const isAdmin = hasRight(user, 'lager_einkauf')
  const [counts, setCounts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [showNew, setShowNew] = useState(false)
  const [newForm, setNewForm] = useState({ count_date: today(), storage_location_id: '', category_id: '', notes: '' })
  const [locations, setLocations] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [creating, setCreating] = useState(false)

  const [current, setCurrent] = useState<any | null>(null)
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [noteDrafts, setNoteDrafts] = useState<Record<string, string>>({})
  const [savingId, setSavingId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [onlyOpen, setOnlyOpen] = useState(false)
  const [scannerOpen, setScannerOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState<{ title: string; url: string } | null>(null)
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({})

  const loadCounts = async () => {
    setLoading(true)
    try {
      setCounts(await stockCountsApi.list())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCounts()
    storageLocationsApi.list().then(setLocations).catch(() => {})
    articleCategoriesApi.list().then(setCategories).catch(() => {})
  }, [])

  const openCount = async (id: string) => {
    setError('')
    try {
      const sc = await stockCountsApi.get(id)
      setCurrent(sc)
      setDrafts({})
      setNoteDrafts({})
      setSearch('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Laden')
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      const sc = await stockCountsApi.create({
        count_date: newForm.count_date,
        storage_location_id: newForm.storage_location_id || undefined,
        category_id: newForm.category_id || undefined,
        notes: newForm.notes || undefined,
      })
      setShowNew(false)
      await loadCounts()
      setCurrent(sc)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Inventur konnte nicht angelegt werden')
    } finally {
      setCreating(false)
    }
  }

  const items: any[] = current?.items || []
  const counted = items.filter((i) => i.counted_qty !== null).length
  const progress = items.length ? Math.round((counted / items.length) * 100) : 0
  const isOpen = current?.status === 'open'

  const visible = useMemo(() => {
    const s = search.trim().toLowerCase()
    return items.filter((i) => {
      if (onlyOpen && i.counted_qty !== null) return false
      if (!s) return true
      return (
        i.article_number.toLowerCase().includes(s) ||
        i.article_name.toLowerCase().includes(s) ||
        (i.barcode || '').toLowerCase() === s ||
        (i.location || '').toLowerCase().includes(s)
      )
    })
  }, [items, search, onlyOpen])

  /** Treffer per Barcode/Artikelnummer: Eingabefeld der Zeile fokussieren */
  const jumpTo = (code: string) => {
    const c = code.trim().toLowerCase()
    const hit = items.find((i) => (i.barcode || '').toLowerCase() === c || i.article_number.toLowerCase() === c)
    if (hit) {
      setSearch(hit.article_number)
      setTimeout(() => inputRefs.current[hit.id]?.focus(), 50)
      return true
    }
    return false
  }

  const saveItem = async (item: any) => {
    const raw = drafts[item.id]
    const note = noteDrafts[item.id]
    if (raw === undefined && note === undefined) return
    let counted_qty: number | null = item.counted_qty
    if (raw !== undefined) {
      if (raw.trim() === '') counted_qty = null
      else {
        const n = Number(raw.replace(',', '.'))
        if (!Number.isInteger(n) || n < 0) {
          setError(`${item.article_number}: Bitte eine ganze Zahl ab 0 eingeben.`)
          return
        }
        counted_qty = n
      }
    }
    setSavingId(item.id)
    setError('')
    try {
      const updated = await stockCountsApi.updateItem(current.id, item.id, {
        counted_qty,
        note: note !== undefined ? note : undefined,
      })
      setCurrent((c: any) => ({ ...c, items: c.items.map((i: any) => (i.id === item.id ? updated : i)) }))
      setDrafts((d) => {
        const { [item.id]: _, ...rest } = d
        return rest
      })
      setNoteDrafts((d) => {
        const { [item.id]: _, ...rest } = d
        return rest
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Speichern fehlgeschlagen')
    } finally {
      setSavingId(null)
    }
  }

  const focusNext = (itemId: string) => {
    const idx = visible.findIndex((i) => i.id === itemId)
    const next = visible[idx + 1]
    if (next) setTimeout(() => inputRefs.current[next.id]?.focus(), 30)
  }

  const handleComplete = async () => {
    if (!current) return
    const msg =
      `Inventur ${current.count_number} jetzt abschließen?\n\n` +
      'Alle Differenzen werden als Lagerkorrektur gebucht. Danach kann die Inventur nicht mehr geändert werden.'
    if (!confirm(msg)) return
    setBusy(true)
    setError('')
    try {
      setCurrent(await stockCountsApi.complete(current.id))
      await loadCounts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Abschluss fehlgeschlagen')
    } finally {
      setBusy(false)
    }
  }

  const handleCancel = async () => {
    if (!current || !confirm(`Inventur ${current.count_number} abbrechen? Es wird nichts gebucht.`)) return
    setBusy(true)
    try {
      await stockCountsApi.cancel(current.id)
      await openCount(current.id)
      await loadCounts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Abbrechen fehlgeschlagen')
    } finally {
      setBusy(false)
    }
  }

  const openPdf = async () => {
    if (!current) return
    try {
      const blob = await stockCountsApi.getPdf(current.id)
      const title = current.status === 'completed' ? 'Inventurliste' : 'Zählliste'
      setPreview({ title: `${title} ${current.count_number}`, url: URL.createObjectURL(blob) })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PDF konnte nicht geladen werden')
    }
  }

  const downloadCsv = async () => {
    if (!current) return
    try {
      const blob = await stockCountsApi.getCsv(current.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Inventur_${current.count_number}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'CSV konnte nicht geladen werden')
    }
  }

  // ---------- Detailansicht ----------
  if (current) {
    return (
      <div className="page">
        <button type="button" className="btn-secondary btn-sm" onClick={() => { setCurrent(null); loadCounts() }}>
          ← Alle Inventuren
        </button>
        <h1 style={{ marginTop: '0.75rem' }}>
          Inventur {current.count_number}{' '}
          <span style={{ fontSize: '1rem', color: STATUS_COLORS[current.status] }}>({STATUS_LABELS[current.status]})</span>
        </h1>
        <p className="muted" style={{ marginTop: 0 }}>
          Stichtag {formatDate(current.count_date)} · {current.scope_label}
          {current.notes ? ` · ${current.notes}` : ''}
        </p>

        <div style={{ margin: '0.5rem 0 1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
            <span>{counted} von {items.length} Artikeln gezählt</span>
            <span>{progress} %</span>
          </div>
          <div style={{ height: 10, background: 'rgba(255,255,255,0.1)', borderRadius: 5, overflow: 'hidden' }}>
            <div style={{ width: `${progress}%`, height: '100%', background: progress === 100 ? '#4ade80' : '#22d3ee' }} />
          </div>
        </div>

        {current.status === 'completed' && (
          <div className="card" style={{ marginBottom: '1rem', padding: '0.75rem 1rem' }}>
            Lagerwert laut Buchbestand: <strong>{formatEuro(current.value_expected)}</strong> · Lagerwert laut Inventur:{' '}
            <strong>{formatEuro(current.value_counted)}</strong> · Differenz:{' '}
            <strong style={{ color: diffColor(Number(current.value_counted) - Number(current.value_expected)) }}>
              {formatEuro(Number(current.value_counted) - Number(current.value_expected))}
            </strong>
          </div>
        )}

        <div className="toolbar" style={{ flexWrap: 'wrap' }}>
          <input
            type="search"
            placeholder="Suchen oder Barcode scannen + Enter"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                if (!jumpTo(search) && visible.length === 1) inputRefs.current[visible[0].id]?.focus()
              }
            }}
            autoFocus
          />
          {isOpen && (
            <button type="button" className="btn-secondary" onClick={() => setScannerOpen(true)}>📷 Kamera-Scan</button>
          )}
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', whiteSpace: 'nowrap' }}>
            <input type="checkbox" checked={onlyOpen} onChange={(e) => setOnlyOpen(e.target.checked)} /> nur ungezählte
          </label>
          <button type="button" className="btn-secondary" onClick={openPdf}>
            {current.status === 'completed' ? 'Inventurliste (PDF)' : 'Zählliste drucken'}
          </button>
          {current.status === 'completed' && (
            <button type="button" className="btn-secondary" onClick={downloadCsv}>CSV für Steuerberater</button>
          )}
          {isOpen && isAdmin && (
            <>
              <button type="button" className="btn-secondary" disabled={busy} onClick={handleCancel}>Abbrechen</button>
              <button type="button" className="btn-primary" disabled={busy || counted < items.length} onClick={handleComplete}
                title={counted < items.length ? 'Erst alle Artikel zählen (auch Bestand 0 eintragen)' : ''}>
                Inventur abschließen
              </button>
            </>
          )}
        </div>
        {error && <p className="error">{error}</p>}
        {isOpen && (
          <p className="muted" style={{ fontSize: '0.85rem' }}>
            Ist-Menge eintragen und mit Enter bestätigen (springt zur nächsten Zeile). Der Sollbestand wird erst nach der
            Eingabe angezeigt (Blindzählung). Auch leere Fächer mit 0 erfassen.
          </p>
        )}

        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Artikelnr.</th>
                <th>Bezeichnung</th>
                <th>Lagerort</th>
                <th style={{ width: 110 }}>Ist</th>
                <th style={{ textAlign: 'right' }}>Soll</th>
                <th style={{ textAlign: 'right' }}>Differenz</th>
                <th>Bemerkung</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((i) => {
                const diff = i.counted_qty !== null && i.expected_qty !== null ? i.counted_qty - i.expected_qty : null
                const draft = drafts[i.id]
                return (
                  <tr key={i.id}>
                    <td><code>{i.article_number}</code></td>
                    <td>{i.article_name}</td>
                    <td>{i.location || '–'}</td>
                    <td>
                      {isOpen ? (
                        <input
                          ref={(el) => { inputRefs.current[i.id] = el }}
                          inputMode="numeric"
                          style={{ width: 90, fontSize: '1.05rem', textAlign: 'right' }}
                          value={draft !== undefined ? draft : i.counted_qty ?? ''}
                          onChange={(e) => setDrafts((d) => ({ ...d, [i.id]: e.target.value }))}
                          onBlur={() => saveItem(i)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              e.preventDefault()
                              // Verlassen des Feldes speichert (onBlur), danach nächste Zeile
                              e.currentTarget.blur()
                              focusNext(i.id)
                            }
                          }}
                          aria-label={`Ist-Menge ${i.article_name}`}
                        />
                      ) : (
                        <strong>{i.counted_qty ?? '–'}</strong>
                      )}
                      {savingId === i.id && <span className="muted"> …</span>}
                    </td>
                    <td style={{ textAlign: 'right' }}>{i.counted_qty !== null ? i.expected_qty : '·'}</td>
                    <td style={{ textAlign: 'right', fontWeight: diff ? 700 : undefined, color: diff ? diffColor(diff) : undefined }}>
                      {diff === null ? '' : fmtDiff(diff)}
                    </td>
                    <td>
                      {isOpen ? (
                        <input
                          value={noteDrafts[i.id] !== undefined ? noteDrafts[i.id] : i.note || ''}
                          maxLength={255}
                          placeholder="optional"
                          onChange={(e) => setNoteDrafts((d) => ({ ...d, [i.id]: e.target.value }))}
                          onBlur={() => saveItem(i)}
                        />
                      ) : (
                        i.note || ''
                      )}
                    </td>
                  </tr>
                )
              })}
              {visible.length === 0 && (
                <tr><td colSpan={7} className="muted">Keine passenden Artikel.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <BarcodeScanner
          open={scannerOpen}
          onClose={() => setScannerOpen(false)}
          onScan={(code) => {
            setScannerOpen(false)
            if (!jumpTo(code)) setError(`Kein Artikel mit Barcode/Nummer „${code}“ in dieser Inventur.`)
          }}
        />
        {preview && (
          <PreviewModal title={preview.title} url={preview.url} type="pdf" onClose={() => { URL.revokeObjectURL(preview.url); setPreview(null) }} />
        )}
      </div>
    )
  }

  // ---------- Übersicht ----------
  return (
    <div className="page">
      <h1>Inventur</h1>
      <div className="toolbar">
        {isAdmin && (
          <button type="button" className="btn-primary" onClick={() => { setError(''); setShowNew(true) }}>
            + Neue Inventur
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {loading ? (
        <p>Laden...</p>
      ) : counts.length === 0 ? (
        <p className="muted">Noch keine Inventur durchgeführt.</p>
      ) : (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Nummer</th>
                <th>Stichtag</th>
                <th>Umfang</th>
                <th>Fortschritt</th>
                <th style={{ textAlign: 'right' }}>Lagerwert (EK)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {counts.map((c) => (
                <tr key={c.id} onClick={() => openCount(c.id)} style={{ cursor: 'pointer' }}>
                  <td><code>{c.count_number}</code></td>
                  <td>{formatDate(c.count_date)}</td>
                  <td>{c.scope_label}</td>
                  <td>{c.counted_items} / {c.total_items}</td>
                  <td style={{ textAlign: 'right' }}>{c.status === 'completed' ? formatEuro(c.value_counted) : '–'}</td>
                  <td><span style={{ color: STATUS_COLORS[c.status], fontWeight: 600 }}>{STATUS_LABELS[c.status]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew && (
        <div className="modal-overlay" onClick={() => setShowNew(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Neue Inventur</h2>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Stichtag *</label>
                <input type="date" value={newForm.count_date} onChange={(e) => setNewForm({ ...newForm, count_date: e.target.value })} required />
              </div>
              <div className="form-group">
                <label>Lagerort (optional)</label>
                <select value={newForm.storage_location_id} onChange={(e) => setNewForm({ ...newForm, storage_location_id: e.target.value })}>
                  <option value="">Alle Lagerorte</option>
                  {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Kategorie (optional)</label>
                <select value={newForm.category_id} onChange={(e) => setNewForm({ ...newForm, category_id: e.target.value })}>
                  <option value="">Alle Kategorien</option>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Notiz</label>
                <input value={newForm.notes} maxLength={2000} placeholder="z. B. Jahresinventur 2026" onChange={(e) => setNewForm({ ...newForm, notes: e.target.value })} />
              </div>
              <p className="muted" style={{ fontSize: '0.85rem' }}>
                Alle aktiven Artikel im gewählten Umfang kommen auf die Zählliste. Während der Zählung kann normal weitergearbeitet werden –
                Buchungen werden beim Abschluss korrekt berücksichtigt.
              </p>
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowNew(false)}>Abbrechen</button>
                <button type="submit" className="btn-primary" disabled={creating}>{creating ? 'Lege an…' : 'Inventur starten'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
