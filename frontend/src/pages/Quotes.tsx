import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { quotesApi, customersApi, vehiclesApi, articlesApi, laborRatesApi } from '../api/client'
import PreviewModal from '../components/PreviewModal'

type ItemType = 'labor' | 'material' | 'service'

interface ItemForm {
  item_type: ItemType
  article_id: string
  description: string
  quantity: string
  unit: string
  unit_price: string
  vat_rate: string
}

interface QuoteForm {
  quote_type: 'offer' | 'estimate'
  customer_id: string
  vehicle_id: string
  quote_date: string
  valid_until: string
  subject: string
  notes: string
  internal_notes: string
  items: ItemForm[]
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Entwurf',
  sent: 'Versendet',
  accepted: 'Angenommen',
  rejected: 'Abgelehnt',
  converted: 'In Auftrag umgewandelt',
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'var(--color-text-muted, #888)',
  sent: '#60a5fa',
  accepted: '#4ade80',
  rejected: '#f87171',
  converted: '#c4b5fd',
}

const TYPE_LABELS: Record<string, string> = { offer: 'Angebot', estimate: 'Kostenvoranschlag' }
const ITEM_TYPE_LABELS: Record<ItemType, string> = { labor: 'Arbeit', material: 'Material', service: 'Leistung' }
const DEFAULT_VALIDITY_DAYS = 30
// Eingabefelder in der Positionstabelle füllen ihre Spalte aus
const CELL: React.CSSProperties = { width: '100%', minWidth: 0, boxSizing: 'border-box' }

const today = () => new Date().toISOString().slice(0, 10)
const addDays = (iso: string, days: number) => {
  const d = new Date(iso)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

const emptyItem = (item_type: ItemType = 'service'): ItemForm => ({
  item_type,
  article_id: '',
  description: '',
  quantity: '1',
  unit: item_type === 'labor' ? 'Std.' : item_type === 'material' ? 'Stück' : 'Stk',
  unit_price: '0',
  vat_rate: '19',
})

const emptyForm = (): QuoteForm => ({
  quote_type: 'offer',
  customer_id: '',
  vehicle_id: '',
  quote_date: today(),
  valid_until: addDays(today(), DEFAULT_VALIDITY_DAYS),
  subject: '',
  notes: '',
  internal_notes: '',
  items: [emptyItem('labor')],
})

const toNum = (v: string) => {
  const n = parseFloat(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : 0
}
const round2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100
const formatEuro = (v: number | string) =>
  Number(v).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })
const formatDate = (d?: string | null) => {
  if (!d) return '–'
  const [y, m, day] = d.slice(0, 10).split('-')
  return `${day}.${m}.${y}`
}
const customerName = (c: any) =>
  c ? (c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email || '–') : '–'
const vehicleLabel = (v: any) =>
  [v.license_plate, v.model_name_free, v.vin].filter(Boolean).join(' · ') || 'Fahrzeug'

/** Summen wie im Backend: MwSt je Steuersatz kaufmännisch gerundet */
function calcTotals(items: ItemForm[]) {
  const bases = new Map<number, number>()
  for (const it of items) {
    const line = round2(round2(toNum(it.quantity)) * round2(toNum(it.unit_price)))
    const rate = toNum(it.vat_rate)
    bases.set(rate, round2((bases.get(rate) || 0) + line))
  }
  let net = 0
  let vat = 0
  const breakdown: { rate: number; basis: number; tax: number }[] = []
  for (const [rate, basis] of [...bases.entries()].sort((a, b) => b[0] - a[0])) {
    const tax = round2((basis * rate) / 100)
    breakdown.push({ rate, basis, tax })
    net = round2(net + basis)
    vat = round2(vat + tax)
  }
  return { net, vat, gross: round2(net + vat), breakdown }
}

export default function Quotes() {
  const navigate = useNavigate()
  const [quotes, setQuotes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [customers, setCustomers] = useState<any[]>([])
  const [customerSearch, setCustomerSearch] = useState('')
  const [vehicles, setVehicles] = useState<any[]>([])
  const [articles, setArticles] = useState<any[]>([])
  const [laborRates, setLaborRates] = useState<any[]>([])

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<QuoteForm>(emptyForm())
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [detail, setDetail] = useState<any | null>(null)
  const [detailError, setDetailError] = useState('')
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState<{ title: string; url: string } | null>(null)
  const [convert, setConvert] = useState<{ vehicle_id: string; vehicles: any[] } | null>(null)
  const [emailModal, setEmailModal] = useState<{ recipient: string } | null>(null)

  const customerMap = useMemo(() => {
    const m = new Map<string, any>()
    customers.forEach((c) => m.set(c.id, c))
    return m
  }, [customers])

  const loadQuotes = async () => {
    setLoading(true)
    try {
      setQuotes(await quotesApi.list({ status_filter: statusFilter || undefined, limit: 500 }))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadQuotes()
  }, [statusFilter])

  useEffect(() => {
    customersApi.list({ limit: 100 }).then(setCustomers).catch(() => {})
    articlesApi.list({ limit: 200 }).then(setArticles).catch(() => {})
    laborRatesApi.list().then(setLaborRates).catch(() => {})
  }, [])

  // Kundensuche im Formular (Server-Suche, falls mehr als 100 Kunden)
  useEffect(() => {
    if (!showForm) return
    const t = setTimeout(() => {
      customersApi
        .list({ limit: 100, search: customerSearch || undefined })
        .then((list) => {
          setCustomers((prev) => {
            const m = new Map(prev.map((c) => [c.id, c]))
            list.forEach((c: any) => m.set(c.id, c))
            return [...m.values()]
          })
        })
        .catch(() => {})
    }, 300)
    return () => clearTimeout(t)
  }, [customerSearch, showForm])

  // Fahrzeuge des gewählten Kunden
  useEffect(() => {
    if (!form.customer_id) {
      setVehicles([])
      return
    }
    vehiclesApi.list({ customer_id: form.customer_id }).then(setVehicles).catch(() => setVehicles([]))
  }, [form.customer_id])

  const selectedCustomer = customerMap.get(form.customer_id)
  const isB2B = selectedCustomer?.customer_type === 'B2B'
  const totals = calcTotals(form.items)

  const filteredCustomers = customers
    .filter((c) => !customerSearch || customerName(c).toLowerCase().includes(customerSearch.toLowerCase()))
    .sort((a, b) => customerName(a).localeCompare(customerName(b)))
    .slice(0, 100)

  const displayed = quotes.filter((q) => {
    if (!search) return true
    const s = search.toLowerCase()
    return (
      q.quote_number.toLowerCase().includes(s) ||
      (q.subject || '').toLowerCase().includes(s) ||
      customerName(customerMap.get(q.customer_id)).toLowerCase().includes(s)
    )
  })

  const isExpired = (q: any) =>
    q.valid_until && ['draft', 'sent'].includes(q.status) && q.valid_until < today()

  // ---------- Formular ----------
  const openNew = () => {
    setEditingId(null)
    setForm(emptyForm())
    setCustomerSearch('')
    setFormError('')
    setShowForm(true)
  }

  const openEdit = (q: any) => {
    setEditingId(q.id)
    setForm({
      quote_type: q.quote_type,
      customer_id: q.customer_id,
      vehicle_id: q.vehicle_id || '',
      quote_date: q.quote_date,
      valid_until: q.valid_until || '',
      subject: q.subject || '',
      notes: q.notes || '',
      internal_notes: q.internal_notes || '',
      items: q.items.map((it: any) => ({
        item_type: it.item_type,
        article_id: it.article_id || '',
        description: it.description,
        quantity: String(Number(it.quantity)),
        unit: it.unit || '',
        unit_price: String(Number(it.unit_price)),
        vat_rate: String(Number(it.vat_rate)),
      })),
    })
    setCustomerSearch('')
    setFormError('')
    setDetail(null)
    setShowForm(true)
  }

  const setItem = (idx: number, patch: Partial<ItemForm>) =>
    setForm((f) => ({ ...f, items: f.items.map((it, i) => (i === idx ? { ...it, ...patch } : it)) }))

  const removeItem = (idx: number) =>
    setForm((f) => ({ ...f, items: f.items.filter((_, i) => i !== idx) }))

  const moveItem = (idx: number, dir: -1 | 1) =>
    setForm((f) => {
      const items = [...f.items]
      const j = idx + dir
      if (j < 0 || j >= items.length) return f
      ;[items[idx], items[j]] = [items[j], items[idx]]
      return { ...f, items }
    })

  const addLabor = () => {
    const rate = laborRates.find((r) => r.is_default) || laborRates[0]
    const item = emptyItem('labor')
    if (rate) {
      item.description = rate.name
      item.unit_price = String(Number(rate.rate_per_hour))
    }
    setForm((f) => ({ ...f, items: [...f.items, item] }))
  }

  const pickArticle = (idx: number, articleId: string) => {
    const a = articles.find((x) => x.id === articleId)
    if (!a) {
      setItem(idx, { article_id: '' })
      return
    }
    const price = isB2B ? a.sales_price_b2b : a.sales_price_b2c
    setItem(idx, {
      article_id: a.id,
      description: a.name,
      unit_price: String(Number(price)),
      vat_rate: String(Number(a.vat_rate)),
    })
  }

  const handleTypeChange = (quote_type: 'offer' | 'estimate') =>
    setForm((f) => ({
      ...f,
      quote_type,
      valid_until: quote_type === 'offer' ? f.valid_until || addDays(f.quote_date, DEFAULT_VALIDITY_DAYS) : '',
    }))

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!form.customer_id) {
      setFormError('Bitte einen Kunden auswählen.')
      return
    }
    const items = form.items.filter((it) => it.description.trim())
    if (items.length === 0) {
      setFormError('Mindestens eine Position mit Beschreibung ist erforderlich.')
      return
    }
    if (items.some((it) => toNum(it.quantity) <= 0)) {
      setFormError('Die Menge jeder Position muss größer als 0 sein.')
      return
    }
    const payload = {
      quote_type: form.quote_type,
      customer_id: form.customer_id,
      vehicle_id: form.vehicle_id || null,
      quote_date: form.quote_date,
      valid_until: form.valid_until || null,
      subject: form.subject || null,
      notes: form.notes || null,
      internal_notes: form.internal_notes || null,
      items: items.map((it) => ({
        item_type: it.item_type,
        article_id: it.item_type === 'material' && it.article_id ? it.article_id : null,
        description: it.description.trim(),
        quantity: toNum(it.quantity),
        unit: it.unit || null,
        unit_price: toNum(it.unit_price),
        vat_rate: toNum(it.vat_rate),
      })),
    }
    setSaving(true)
    try {
      const saved = editingId ? await quotesApi.update(editingId, payload) : await quotesApi.create(payload)
      setShowForm(false)
      await loadQuotes()
      setDetail(saved)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Fehler beim Speichern')
    } finally {
      setSaving(false)
    }
  }

  // ---------- Aktionen im Detail ----------
  const runAction = async (fn: () => Promise<any>) => {
    setBusy(true)
    setDetailError('')
    try {
      const result = await fn()
      if (result && result.id) setDetail(result)
      await loadQuotes()
      return result
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'Aktion fehlgeschlagen')
    } finally {
      setBusy(false)
    }
  }

  const openPdf = async (q: any) => {
    try {
      const blob = await quotesApi.getPdf(q.id)
      setPreview({ title: `${TYPE_LABELS[q.quote_type]} ${q.quote_number}`, url: URL.createObjectURL(blob) })
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'PDF konnte nicht geladen werden')
    }
  }

  const closePreview = () => {
    if (preview) URL.revokeObjectURL(preview.url)
    setPreview(null)
  }

  const startConvert = async (q: any) => {
    const list = await vehiclesApi.list({ customer_id: q.customer_id }).catch(() => [])
    setConvert({ vehicle_id: q.vehicle_id || (list[0]?.id ?? ''), vehicles: list })
  }

  const doConvert = async () => {
    if (!detail || !convert) return
    if (!convert.vehicle_id) {
      setDetailError('Bitte ein Fahrzeug auswählen.')
      return
    }
    const res = await runAction(() => quotesApi.convert(detail.id, { vehicle_id: convert.vehicle_id }))
    if (res) setConvert(null)
  }

  const doDelete = async (q: any) => {
    if (!confirm(`${TYPE_LABELS[q.quote_type]} ${q.quote_number} wirklich löschen?`)) return
    setBusy(true)
    try {
      await quotesApi.delete(q.id)
      setDetail(null)
      await loadQuotes()
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'Löschen fehlgeschlagen')
    } finally {
      setBusy(false)
    }
  }

  const detailTotals = detail
    ? calcTotals(
        detail.items.map((it: any) => ({
          ...emptyItem(),
          quantity: String(it.quantity),
          unit_price: String(it.unit_price),
          vat_rate: String(it.vat_rate),
        }))
      )
    : null

  return (
    <div className="page">
      <h1>Angebote &amp; Kostenvoranschläge</h1>
      <div className="toolbar">
        <input type="search" placeholder="Nummer, Kunde, Betreff..." value={search} onChange={(e) => setSearch(e.target.value)} />
        <select className="select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">Alle Status</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <button type="button" onClick={openNew} className="btn-primary">+ Neues Angebot</button>
      </div>

      {loading ? (
        <p>Laden...</p>
      ) : displayed.length === 0 ? (
        <p className="muted">Noch keine Angebote vorhanden.</p>
      ) : (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Nummer</th>
                <th>Art</th>
                <th>Datum</th>
                <th>Kunde</th>
                <th>Betreff</th>
                <th style={{ textAlign: 'right' }}>Brutto</th>
                <th>Gültig bis</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {displayed.map((q) => (
                <tr key={q.id} onClick={() => { setDetailError(''); setConvert(null); setDetail(q) }} style={{ cursor: 'pointer' }}>
                  <td><code>{q.quote_number}</code></td>
                  <td>{TYPE_LABELS[q.quote_type]}</td>
                  <td>{formatDate(q.quote_date)}</td>
                  <td>{customerName(customerMap.get(q.customer_id))}</td>
                  <td>{q.subject || '–'}</td>
                  <td style={{ textAlign: 'right' }}>{formatEuro(q.gross_amount)}</td>
                  <td style={{ color: isExpired(q) ? '#f87171' : undefined }}>
                    {formatDate(q.valid_until)}{isExpired(q) ? ' (abgelaufen)' : ''}
                  </td>
                  <td><span style={{ color: STATUS_COLORS[q.status], fontWeight: 600 }}>{STATUS_LABELS[q.status] || q.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ---------- Detailansicht ---------- */}
      {detail && (
        <div className="modal-overlay" onClick={() => setDetail(null)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>
              {TYPE_LABELS[detail.quote_type]} {detail.quote_number}{' '}
              <span style={{ color: STATUS_COLORS[detail.status], fontSize: '0.9rem' }}>({STATUS_LABELS[detail.status]})</span>
            </h2>
            <p style={{ margin: '0 0 0.75rem' }}>
              <strong>{customerName(customerMap.get(detail.customer_id))}</strong>
              {detail.subject ? ` – ${detail.subject}` : ''}
              <br />
              Datum {formatDate(detail.quote_date)}
              {detail.valid_until ? ` · gültig bis ${formatDate(detail.valid_until)}` : ''}
              {isExpired(detail) && <span style={{ color: '#f87171' }}> · abgelaufen</span>}
            </p>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Pos</th>
                    <th>Art</th>
                    <th>Beschreibung</th>
                    <th style={{ textAlign: 'right' }}>Menge</th>
                    <th style={{ textAlign: 'right' }}>Einzelpreis</th>
                    <th style={{ textAlign: 'right' }}>MwSt</th>
                    <th style={{ textAlign: 'right' }}>Netto</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.items.map((it: any) => (
                    <tr key={it.id}>
                      <td>{it.position}</td>
                      <td>{ITEM_TYPE_LABELS[it.item_type as ItemType] || it.item_type}</td>
                      <td style={{ whiteSpace: 'pre-wrap' }}>{it.description}</td>
                      <td style={{ textAlign: 'right' }}>{Number(it.quantity).toLocaleString('de-DE')} {it.unit || ''}</td>
                      <td style={{ textAlign: 'right' }}>{formatEuro(it.unit_price)}</td>
                      <td style={{ textAlign: 'right' }}>{Number(it.vat_rate).toLocaleString('de-DE')} %</td>
                      <td style={{ textAlign: 'right' }}>{formatEuro(it.line_total_net)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ textAlign: 'right', margin: '0.75rem 0' }}>
              <div>Netto: {formatEuro(detail.net_amount)}</div>
              {detailTotals?.breakdown.map((b) => (
                <div key={b.rate}>MwSt {b.rate.toLocaleString('de-DE')} %: {formatEuro(b.tax)}</div>
              ))}
              <div style={{ fontWeight: 700 }}>Brutto: {formatEuro(detail.gross_amount)}</div>
            </div>
            {detail.internal_notes && (
              <p className="muted" style={{ whiteSpace: 'pre-wrap' }}><strong>Intern:</strong> {detail.internal_notes}</p>
            )}

            {convert && (
              <div className="card" style={{ margin: '0.75rem 0', padding: '0.75rem' }}>
                <div className="form-group">
                  <label>Fahrzeug für den Werkstattauftrag *</label>
                  {convert.vehicles.length === 0 ? (
                    <p className="error">Dieser Kunde hat noch kein Fahrzeug. Bitte zuerst unter „Fahrzeuge“ anlegen.</p>
                  ) : (
                    <select value={convert.vehicle_id} onChange={(e) => setConvert({ ...convert, vehicle_id: e.target.value })}>
                      {convert.vehicles.map((v) => (
                        <option key={v.id} value={v.id}>{vehicleLabel(v)}</option>
                      ))}
                    </select>
                  )}
                </div>
                <div className="form-actions">
                  <button type="button" className="btn-secondary" onClick={() => setConvert(null)}>Abbrechen</button>
                  <button type="button" className="btn-primary" disabled={busy || convert.vehicles.length === 0} onClick={doConvert}>
                    Werkstattauftrag anlegen
                  </button>
                </div>
              </div>
            )}

            {emailModal && (
              <div className="card" style={{ margin: '0.75rem 0', padding: '0.75rem' }}>
                <div className="form-group">
                  <label>Empfänger (leer = E-Mail des Kunden)</label>
                  <input type="email" value={emailModal.recipient} onChange={(e) => setEmailModal({ recipient: e.target.value })} />
                </div>
                <div className="form-actions">
                  <button type="button" className="btn-secondary" onClick={() => setEmailModal(null)}>Abbrechen</button>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={busy}
                    onClick={async () => {
                      const res = await runAction(() => quotesApi.sendEmail(detail.id, emailModal.recipient || undefined))
                      if (res) setEmailModal(null)
                    }}
                  >
                    {busy ? 'Sende…' : 'Senden'}
                  </button>
                </div>
              </div>
            )}

            {detailError && <p className="error">{detailError}</p>}

            <div className="form-actions" style={{ flexWrap: 'wrap', gap: '0.4rem' }}>
              <button type="button" className="btn-secondary" onClick={() => setDetail(null)}>Schließen</button>
              <button type="button" className="btn-secondary" onClick={() => openPdf(detail)}>PDF</button>
              {detail.status === 'draft' && (
                <>
                  <button type="button" className="btn-secondary" onClick={() => openEdit(detail)}>Bearbeiten</button>
                  <button type="button" className="btn-secondary" disabled={busy} onClick={() => doDelete(detail)}>Löschen</button>
                  <button type="button" className="btn-secondary" disabled={busy} onClick={() => runAction(() => quotesApi.setStatus(detail.id, 'sent'))}>
                    Als versendet markieren
                  </button>
                </>
              )}
              {['draft', 'sent', 'accepted'].includes(detail.status) && (
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => setEmailModal({ recipient: '' })}>
                  Per E-Mail senden
                </button>
              )}
              {['draft', 'sent', 'rejected'].includes(detail.status) && (
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => runAction(() => quotesApi.setStatus(detail.id, 'accepted'))}>
                  Angenommen
                </button>
              )}
              {['draft', 'sent', 'accepted'].includes(detail.status) && (
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => runAction(() => quotesApi.setStatus(detail.id, 'rejected'))}>
                  Abgelehnt
                </button>
              )}
              {detail.status !== 'draft' && (
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => runAction(() => quotesApi.duplicate(detail.id))}>
                  Neue Version
                </button>
              )}
              {['draft', 'sent', 'accepted'].includes(detail.status) && (
                <button type="button" className="btn-primary" disabled={busy} onClick={() => startConvert(detail)}>
                  In Werkstattauftrag umwandeln
                </button>
              )}
              {detail.status === 'converted' && (
                <button type="button" className="btn-primary" onClick={() => navigate('/workshop-orders')}>
                  Zum Werkstattauftrag
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ---------- Formular ---------- */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 1100 }}>
            <h2>{editingId ? 'Angebot bearbeiten' : 'Neues Angebot'}</h2>
            <form onSubmit={handleSave}>
              <div className="form-row">
                <div className="form-group">
                  <label>Art *</label>
                  <select value={form.quote_type} onChange={(e) => handleTypeChange(e.target.value as 'offer' | 'estimate')}>
                    <option value="offer">Angebot (mit Gültigkeit)</option>
                    <option value="estimate">Kostenvoranschlag (unverbindlich)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Datum *</label>
                  <input type="date" value={form.quote_date} onChange={(e) => setForm({ ...form, quote_date: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label>Gültig bis</label>
                  <input type="date" value={form.valid_until} min={form.quote_date} onChange={(e) => setForm({ ...form, valid_until: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Kunde suchen</label>
                  <input type="search" placeholder="Name oder Firma..." value={customerSearch} onChange={(e) => setCustomerSearch(e.target.value)} />
                </div>
                <div className="form-group">
                  <label>Kunde *</label>
                  <select value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value, vehicle_id: '' })} required>
                    <option value="">– bitte wählen –</option>
                    {selectedCustomer && !filteredCustomers.some((c) => c.id === selectedCustomer.id) && (
                      <option value={selectedCustomer.id}>{customerName(selectedCustomer)}</option>
                    )}
                    {filteredCustomers.map((c) => (
                      <option key={c.id} value={c.id}>{customerName(c)}{c.customer_type === 'B2B' ? ' (Händler)' : ''}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Fahrzeug</label>
                  <select value={form.vehicle_id} onChange={(e) => setForm({ ...form, vehicle_id: e.target.value })} disabled={!form.customer_id}>
                    <option value="">– ohne Fahrzeug –</option>
                    {vehicles.map((v) => (
                      <option key={v.id} value={v.id}>{vehicleLabel(v)}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Betreff</label>
                <input value={form.subject} maxLength={255} placeholder="z. B. Reparatur Bremsanlage" onChange={(e) => setForm({ ...form, subject: e.target.value })} />
              </div>

              <label style={{ fontWeight: 600 }}>Positionen {isB2B ? '(Händlerpreise)' : ''}</label>
              <div className="table-wrapper">
                <table className="table" style={{ tableLayout: 'fixed', width: '100%', minWidth: 760 }}>
                  <thead>
                    <tr>
                      <th style={{ width: 105 }}>Art</th>
                      <th>Beschreibung</th>
                      <th style={{ width: 70 }}>Menge</th>
                      <th style={{ width: 75 }}>Einheit</th>
                      <th style={{ width: 95 }}>Preis €</th>
                      <th style={{ width: 70 }}>MwSt %</th>
                      <th style={{ width: 95, textAlign: 'right' }}>Netto</th>
                      <th style={{ width: 115 }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {form.items.map((it, idx) => (
                      <tr key={idx}>
                        <td>
                          <select style={CELL} value={it.item_type} onChange={(e) => setItem(idx, { item_type: e.target.value as ItemType, article_id: '' })}>
                            {Object.entries(ITEM_TYPE_LABELS).map(([k, v]) => (
                              <option key={k} value={k}>{v}</option>
                            ))}
                          </select>
                        </td>
                        <td>
                          {it.item_type === 'material' && (
                            <select value={it.article_id} onChange={(e) => pickArticle(idx, e.target.value)} style={{ ...CELL, marginBottom: 4 }}>
                              <option value="">– Artikel wählen (optional) –</option>
                              {articles.map((a) => (
                                <option key={a.id} value={a.id}>{a.article_number} · {a.name}</option>
                              ))}
                            </select>
                          )}
                          <input value={it.description} placeholder="Beschreibung" onChange={(e) => setItem(idx, { description: e.target.value })} style={CELL} />
                        </td>
                        <td><input style={CELL} inputMode="decimal" value={it.quantity} onChange={(e) => setItem(idx, { quantity: e.target.value })} /></td>
                        <td><input style={CELL} value={it.unit} onChange={(e) => setItem(idx, { unit: e.target.value })} /></td>
                        <td><input style={CELL} inputMode="decimal" value={it.unit_price} onChange={(e) => setItem(idx, { unit_price: e.target.value })} /></td>
                        <td>
                          <select style={CELL} value={it.vat_rate} onChange={(e) => setItem(idx, { vat_rate: e.target.value })}>
                            <option value="19">19</option>
                            <option value="7">7</option>
                            <option value="0">0</option>
                          </select>
                        </td>
                        <td style={{ textAlign: 'right' }}>{formatEuro(round2(round2(toNum(it.quantity)) * round2(toNum(it.unit_price))))}</td>
                        <td style={{ whiteSpace: 'nowrap' }}>
                          <button type="button" className="btn-secondary btn-sm" title="Nach oben" onClick={() => moveItem(idx, -1)}>↑</button>
                          <button type="button" className="btn-secondary btn-sm" title="Nach unten" onClick={() => moveItem(idx, 1)}>↓</button>
                          <button type="button" className="btn-secondary btn-sm" title="Entfernen" onClick={() => removeItem(idx)}>✕</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div style={{ display: 'flex', gap: '0.4rem', margin: '0.5rem 0 1rem' }}>
                <button type="button" className="btn-secondary btn-sm" onClick={addLabor}>+ Arbeitszeit</button>
                <button type="button" className="btn-secondary btn-sm" onClick={() => setForm((f) => ({ ...f, items: [...f.items, emptyItem('material')] }))}>+ Material</button>
                <button type="button" className="btn-secondary btn-sm" onClick={() => setForm((f) => ({ ...f, items: [...f.items, emptyItem('service')] }))}>+ Freie Position</button>
              </div>

              <div style={{ textAlign: 'right', marginBottom: '1rem' }}>
                <div>Netto: {formatEuro(totals.net)}</div>
                {totals.breakdown.map((b) => (
                  <div key={b.rate}>MwSt {b.rate.toLocaleString('de-DE')} %: {formatEuro(b.tax)}</div>
                ))}
                <div style={{ fontWeight: 700 }}>Brutto: {formatEuro(totals.gross)}</div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Hinweis für den Kunden (erscheint auf dem PDF)</label>
                  <textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Interne Notiz (nicht auf dem PDF)</label>
                  <textarea rows={2} value={form.internal_notes} onChange={(e) => setForm({ ...form, internal_notes: e.target.value })} />
                </div>
              </div>
              {form.quote_type === 'estimate' && (
                <p className="muted" style={{ fontSize: '0.85rem' }}>
                  Auf dem Kostenvoranschlag steht automatisch der Hinweis zur Unverbindlichkeit und zur Anzeigepflicht bei wesentlicher Überschreitung (§ 649 BGB).
                </p>
              )}
              {formError && <p className="error">{formError}</p>}
              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Abbrechen</button>
                <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Speichern…' : 'Speichern'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {preview && <PreviewModal title={preview.title} url={preview.url} type="pdf" onClose={closePreview} />}
    </div>
  )
}
