import { useEffect, useMemo, useState } from 'react'
import { purchaseOrdersApi, suppliersApi, articlesApi } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import PreviewModal from '../components/PreviewModal'
import { hasRight } from '../utils/permissions'

interface ItemForm {
  article_id: string
  description: string
  supplier_article_number: string
  quantity: string
  unit: string
  unit_price: string
  vat_rate: string
}

interface OrderForm {
  supplier_id: string
  order_date: string
  expected_date: string
  notes: string
  internal_notes: string
  items: ItemForm[]
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Entwurf',
  sent: 'Bestellt',
  partial: 'Teilweise geliefert',
  received: 'Geliefert',
  closed: 'Abgeschlossen (Rest storniert)',
  cancelled: 'Storniert',
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'var(--color-text-muted, #888)',
  sent: '#60a5fa',
  partial: '#fbbf24',
  received: '#4ade80',
  closed: '#c4b5fd',
  cancelled: '#f87171',
}

const CELL: React.CSSProperties = { width: '100%', minWidth: 0, boxSizing: 'border-box' }

const today = () => new Date().toISOString().slice(0, 10)
const toNum = (v: string) => {
  const n = parseFloat(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : 0
}
const round2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100
const formatEuro = (v: number | string) => Number(v).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })
const formatDate = (d?: string | null) => {
  if (!d) return '–'
  const [y, m, day] = d.slice(0, 10).split('-')
  return `${day}.${m}.${y}`
}
const isWholePositive = (v: string) => /^\d+$/.test(v.trim()) && parseInt(v, 10) > 0

const emptyItem = (): ItemForm => ({
  article_id: '',
  description: '',
  supplier_article_number: '',
  quantity: '1',
  unit: 'Stk',
  unit_price: '0',
  vat_rate: '19',
})

const emptyForm = (supplier_id = ''): OrderForm => ({
  supplier_id,
  order_date: today(),
  expected_date: '',
  notes: '',
  internal_notes: '',
  items: [emptyItem()],
})

/** Summen wie im Backend: MwSt je Steuersatz kaufmännisch gerundet */
function calcTotals(items: { quantity: string; unit_price: string; vat_rate: string }[]) {
  const bases = new Map<number, number>()
  for (const it of items) {
    const line = round2(toNum(it.quantity) * round2(toNum(it.unit_price)))
    const rate = toNum(it.vat_rate)
    bases.set(rate, round2((bases.get(rate) || 0) + line))
  }
  let net = 0
  let vat = 0
  const breakdown: { rate: number; tax: number }[] = []
  for (const [rate, basis] of [...bases.entries()].sort((a, b) => b[0] - a[0])) {
    const tax = round2((basis * rate) / 100)
    breakdown.push({ rate, tax })
    net = round2(net + basis)
    vat = round2(vat + tax)
  }
  return { net, vat, gross: round2(net + vat), breakdown }
}

const progress = (o: any) => {
  const items = o.items || []
  const ordered = items.reduce((s: number, i: any) => s + i.quantity, 0)
  const received = items.reduce((s: number, i: any) => s + i.received_quantity, 0)
  return `${received} / ${ordered}`
}

export default function PurchaseOrders() {
  const { user } = useAuth()
  // Bestellen (versenden) und stornieren: Sonderrecht „Lager & Einkauf“
  const isAdmin = hasRight(user, 'lager_einkauf')
  const [tab, setTab] = useState<'orders' | 'suggestions'>('orders')
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [suppliers, setSuppliers] = useState<any[]>([])
  const [articles, setArticles] = useState<any[]>([])
  const [articleSearch, setArticleSearch] = useState('')

  // Bestellvorschlag: Menge je Artikel (leer = nicht übernehmen), Lieferantenwahl für „Ohne Lieferant“
  const [suggestions, setSuggestions] = useState<any[]>([])
  const [sugLoading, setSugLoading] = useState(false)
  const [sugQty, setSugQty] = useState<Record<string, string>>({})
  const [sugSupplier, setSugSupplier] = useState('')
  const [sugError, setSugError] = useState('')

  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<OrderForm>(emptyForm())
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const [detail, setDetail] = useState<any | null>(null)
  const [detailError, setDetailError] = useState('')
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState<{ title: string; url: string } | null>(null)
  const [emailModal, setEmailModal] = useState<{ recipient: string } | null>(null)
  const [receipt, setReceipt] = useState<{ qty: Record<string, string>; delivery_note: string; update_price: boolean } | null>(null)

  const supplierMap = useMemo(() => new Map(suppliers.map((s) => [s.id, s])), [suppliers])

  const loadOrders = async () => {
    setLoading(true)
    try {
      setOrders(await purchaseOrdersApi.list({ status_filter: statusFilter || undefined }))
    } finally {
      setLoading(false)
    }
  }

  const loadSuggestions = async () => {
    setSugLoading(true)
    setSugError('')
    try {
      const groups = await purchaseOrdersApi.suggestions()
      setSuggestions(groups)
      const q: Record<string, string> = {}
      groups.forEach((g: any) => g.items.forEach((i: any) => { q[i.article_id] = String(i.suggested_quantity) }))
      setSugQty(q)
    } catch (err) {
      setSugError(err instanceof Error ? err.message : 'Bestellvorschlag konnte nicht geladen werden')
    } finally {
      setSugLoading(false)
    }
  }

  useEffect(() => {
    loadOrders()
  }, [statusFilter])

  useEffect(() => {
    if (tab === 'suggestions') loadSuggestions()
  }, [tab])

  useEffect(() => {
    suppliersApi.list().then(setSuppliers).catch(() => {})
    articlesApi.list({ limit: 200 }).then(setArticles).catch(() => {})
  }, [])

  // Artikelsuche im Formular (Server-Suche, falls mehr als 200 Artikel)
  useEffect(() => {
    if (!showForm || !articleSearch) return
    const t = setTimeout(() => {
      articlesApi
        .list({ search: articleSearch, limit: 50 })
        .then((list) =>
          setArticles((prev) => {
            const m = new Map(prev.map((a) => [a.id, a]))
            list.forEach((a: any) => m.set(a.id, a))
            return [...m.values()]
          })
        )
        .catch(() => {})
    }, 300)
    return () => clearTimeout(t)
  }, [articleSearch, showForm])

  const supplierName = (id: string) => supplierMap.get(id)?.name || '–'

  const displayed = orders.filter((o) => {
    if (!search) return true
    const s = search.toLowerCase()
    return o.order_number.toLowerCase().includes(s) || (o.supplier_name || supplierName(o.supplier_id)).toLowerCase().includes(s)
  })

  const filteredArticles = articles
    .filter((a) => {
      if (!articleSearch) return true
      const s = articleSearch.toLowerCase()
      return `${a.article_number} ${a.name} ${a.supplier_article_number || ''}`.toLowerCase().includes(s)
    })
    .sort((a, b) => {
      // Artikel des gewählten Lieferanten zuerst
      const pa = a.supplier_id === form.supplier_id ? 0 : 1
      const pb = b.supplier_id === form.supplier_id ? 0 : 1
      return pa - pb || a.article_number.localeCompare(b.article_number)
    })
    .slice(0, 200)

  // ---------- Formular ----------
  const openNew = () => {
    setEditingId(null)
    setForm(emptyForm())
    setArticleSearch('')
    setFormError('')
    setShowForm(true)
  }

  const openEdit = (o: any) => {
    setEditingId(o.id)
    setForm({
      supplier_id: o.supplier_id,
      order_date: o.order_date,
      expected_date: o.expected_date || '',
      notes: o.notes || '',
      internal_notes: o.internal_notes || '',
      items: o.items.map((it: any) => ({
        article_id: it.article_id || '',
        description: it.description,
        supplier_article_number: it.supplier_article_number || '',
        quantity: String(it.quantity),
        unit: it.unit || '',
        unit_price: String(Number(it.unit_price)),
        vat_rate: String(Number(it.vat_rate)),
      })),
    })
    setArticleSearch('')
    setFormError('')
    setDetail(null)
    setShowForm(true)
  }

  const setItem = (idx: number, patch: Partial<ItemForm>) =>
    setForm((f) => ({ ...f, items: f.items.map((it, i) => (i === idx ? { ...it, ...patch } : it)) }))

  const removeItem = (idx: number) => setForm((f) => ({ ...f, items: f.items.filter((_, i) => i !== idx) }))

  const pickArticle = (idx: number, articleId: string) => {
    const a = articles.find((x) => x.id === articleId)
    if (!a) {
      setItem(idx, { article_id: '' })
      return
    }
    setItem(idx, {
      article_id: a.id,
      description: a.name,
      supplier_article_number: a.supplier_article_number || '',
      unit_price: String(Number(a.purchase_price)),
      vat_rate: String(Number(a.vat_rate)),
    })
  }

  const buildPayload = (f: OrderForm) => ({
    supplier_id: f.supplier_id,
    order_date: f.order_date,
    expected_date: f.expected_date || null,
    notes: f.notes || null,
    internal_notes: f.internal_notes || null,
    items: f.items
      .filter((it) => it.description.trim())
      .map((it) => ({
        article_id: it.article_id || null,
        description: it.description.trim(),
        supplier_article_number: it.supplier_article_number.trim() || null,
        quantity: parseInt(it.quantity, 10),
        unit: it.unit || null,
        unit_price: toNum(it.unit_price),
        vat_rate: toNum(it.vat_rate),
      })),
  })

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    if (!form.supplier_id) {
      setFormError('Bitte einen Lieferanten auswählen.')
      return
    }
    const items = form.items.filter((it) => it.description.trim())
    if (items.length === 0) {
      setFormError('Mindestens eine Position mit Bezeichnung ist erforderlich.')
      return
    }
    if (items.some((it) => !isWholePositive(it.quantity))) {
      setFormError('Die Menge muss eine ganze Zahl größer als 0 sein.')
      return
    }
    if (form.expected_date && form.expected_date < form.order_date) {
      setFormError('Der Liefertermin darf nicht vor dem Bestelldatum liegen.')
      return
    }
    setSaving(true)
    try {
      const payload = buildPayload(form)
      const saved = editingId ? await purchaseOrdersApi.update(editingId, payload) : await purchaseOrdersApi.create(payload)
      setShowForm(false)
      await loadOrders()
      setDetail(saved)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Fehler beim Speichern')
    } finally {
      setSaving(false)
    }
  }

  // ---------- Bestellvorschlag übernehmen ----------
  const createFromSuggestion = async (group: any) => {
    setSugError('')
    const supplierId = group.supplier_id || sugSupplier
    if (!supplierId) {
      setSugError('Bitte für die Artikel ohne Lieferant zuerst einen Lieferanten wählen.')
      return
    }
    const items = group.items
      .filter((i: any) => isWholePositive(sugQty[i.article_id] || ''))
      .map((i: any) => ({
        article_id: i.article_id,
        description: i.name,
        supplier_article_number: i.supplier_article_number || null,
        quantity: parseInt(sugQty[i.article_id], 10),
        unit: 'Stk',
        unit_price: Number(i.unit_price),
        vat_rate: Number(i.vat_rate),
      }))
    if (items.length === 0) {
      setSugError('Bitte bei mindestens einem Artikel eine Menge eingeben.')
      return
    }
    setBusy(true)
    try {
      const created = await purchaseOrdersApi.create({ supplier_id: supplierId, order_date: today(), items })
      await loadOrders()
      setTab('orders')
      setDetailError('')
      setDetail(created)
    } catch (err) {
      setSugError(err instanceof Error ? err.message : 'Bestellung konnte nicht angelegt werden')
    } finally {
      setBusy(false)
    }
  }

  // ---------- Aktionen im Detail ----------
  const runAction = async (fn: () => Promise<any>) => {
    setBusy(true)
    setDetailError('')
    try {
      const result = await fn()
      if (result && result.id) setDetail(result)
      await loadOrders()
      return result
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'Aktion fehlgeschlagen')
    } finally {
      setBusy(false)
    }
  }

  const openPdf = async (o: any) => {
    try {
      const blob = await purchaseOrdersApi.getPdf(o.id)
      setPreview({ title: `Bestellung ${o.order_number}`, url: URL.createObjectURL(blob) })
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'PDF konnte nicht geladen werden')
    }
  }

  const closePreview = () => {
    if (preview) URL.revokeObjectURL(preview.url)
    setPreview(null)
  }

  const doDelete = async (o: any) => {
    if (!confirm(`Bestellung ${o.order_number} wirklich löschen?`)) return
    setBusy(true)
    try {
      await purchaseOrdersApi.delete(o.id)
      setDetail(null)
      await loadOrders()
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'Löschen fehlgeschlagen')
    } finally {
      setBusy(false)
    }
  }

  const doCancel = async (o: any) => {
    const partly = o.items.some((i: any) => i.received_quantity > 0)
    const msg = partly
      ? `Bestellung ${o.order_number} abschließen? Die noch offene Restmenge wird nicht mehr erwartet.`
      : `Bestellung ${o.order_number} stornieren?`
    if (!confirm(msg)) return
    await runAction(() => purchaseOrdersApi.cancel(o.id))
  }

  const startReceipt = (o: any) => {
    const qty: Record<string, string> = {}
    o.items.forEach((i: any) => { qty[i.id] = String(Math.max(i.quantity - i.received_quantity, 0)) })
    setReceipt({ qty, delivery_note: '', update_price: false })
    setEmailModal(null)
    setDetailError('')
  }

  const doReceive = async () => {
    if (!detail || !receipt) return
    const lines = detail.items
      .filter((i: any) => i.quantity - i.received_quantity > 0)
      .map((i: any) => ({ item_id: i.id, raw: (receipt.qty[i.id] ?? '').trim() }))
    if (lines.some((l: any) => !/^\d+$/.test(l.raw))) {
      setDetailError('Bitte nur ganze Zahlen ab 0 eingeben.')
      return
    }
    const res = await runAction(() =>
      purchaseOrdersApi.receive(detail.id, {
        lines: lines.map((l: any) => ({ item_id: l.item_id, quantity: parseInt(l.raw, 10) })),
        delivery_note: receipt.delivery_note.trim() || null,
        update_purchase_price: receipt.update_price,
      })
    )
    if (res) setReceipt(null)
  }

  const closeDetail = () => {
    setDetail(null)
    setReceipt(null)
    setEmailModal(null)
  }

  const totals = calcTotals(form.items)
  const isOpen = (o: any) => ['sent', 'partial'].includes(o.status)
  const overdue = (o: any) => isOpen(o) && o.expected_date && o.expected_date < today()

  return (
    <div className="page">
      <h1>Bestellungen</h1>
      <div className="toolbar" role="tablist">
        <button type="button" role="tab" aria-selected={tab === 'orders'} className={tab === 'orders' ? 'btn-primary' : 'btn-secondary'} onClick={() => setTab('orders')}>
          Bestellungen
        </button>
        <button type="button" role="tab" aria-selected={tab === 'suggestions'} className={tab === 'suggestions' ? 'btn-primary' : 'btn-secondary'} onClick={() => setTab('suggestions')}>
          Bestellvorschlag
        </button>
      </div>

      {tab === 'orders' && (
        <>
          <div className="toolbar">
            <input type="search" placeholder="Nummer oder Lieferant..." value={search} onChange={(e) => setSearch(e.target.value)} />
            <select className="select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Status filtern">
              <option value="">Alle Status</option>
              {Object.entries(STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
            </select>
            <button type="button" onClick={openNew} className="btn-primary">+ Neue Bestellung</button>
          </div>
          {loading ? (
            <p>Laden...</p>
          ) : displayed.length === 0 ? (
            <p className="muted">Noch keine Bestellungen vorhanden. Tipp: Im Reiter „Bestellvorschlag“ siehst du, was nachbestellt werden sollte.</p>
          ) : (
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Nummer</th>
                    <th>Datum</th>
                    <th>Lieferant</th>
                    <th style={{ textAlign: 'right' }}>Netto</th>
                    <th>Liefertermin</th>
                    <th>Geliefert</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {displayed.map((o) => (
                    <tr key={o.id} onClick={() => { setDetailError(''); setReceipt(null); setEmailModal(null); setDetail(o) }} style={{ cursor: 'pointer' }}>
                      <td><code>{o.order_number}</code></td>
                      <td>{formatDate(o.order_date)}</td>
                      <td>{o.supplier_name || supplierName(o.supplier_id)}</td>
                      <td style={{ textAlign: 'right' }}>{formatEuro(o.net_amount)}</td>
                      <td style={{ color: overdue(o) ? '#f87171' : undefined }}>
                        {formatDate(o.expected_date)}{overdue(o) ? ' (überfällig)' : ''}
                      </td>
                      <td>{progress(o)}</td>
                      <td><span style={{ color: STATUS_COLORS[o.status], fontWeight: 600 }}>{STATUS_LABELS[o.status] || o.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {tab === 'suggestions' && (
        <div>
          <p className="muted" style={{ fontSize: '0.9rem' }}>
            Hier stehen alle Artikel, deren verfügbarer Bestand (Lager − Reservierungen + bereits bestellt) unter dem Mindestbestand liegt.
            Vorgeschlagen wird die Menge bis zum Zielbestand. Mengen kannst du ändern; leer oder 0 = nicht bestellen.
          </p>
          {sugError && <p className="error">{sugError}</p>}
          {sugLoading ? (
            <p>Laden...</p>
          ) : suggestions.length === 0 ? (
            <p className="muted">Alles im grünen Bereich – kein Artikel muss nachbestellt werden.</p>
          ) : (
            suggestions.map((g) => (
              <div key={g.supplier_id || 'none'} className="card" style={{ marginBottom: '1rem', padding: '0.75rem' }}>
                <h2 style={{ fontSize: '1.1rem', marginTop: 0 }}>{g.supplier_name}</h2>
                {!g.supplier_id && (
                  <div className="form-group" style={{ maxWidth: 360 }}>
                    <label htmlFor="sug-supplier">Lieferant für diese Artikel</label>
                    <select id="sug-supplier" value={sugSupplier} onChange={(e) => setSugSupplier(e.target.value)}>
                      <option value="">– bitte wählen –</option>
                      {suppliers.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="table-wrapper">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Artikel</th>
                        <th>Lief.-Nr.</th>
                        <th style={{ textAlign: 'right' }}>Bestand</th>
                        <th style={{ textAlign: 'right' }}>Reserviert</th>
                        <th style={{ textAlign: 'right' }}>Bestellt</th>
                        <th style={{ textAlign: 'right' }}>Mindest / Ziel</th>
                        <th style={{ textAlign: 'right' }}>EK netto</th>
                        <th style={{ width: 90 }}>Menge</th>
                      </tr>
                    </thead>
                    <tbody>
                      {g.items.map((i: any) => (
                        <tr key={i.article_id}>
                          <td><code>{i.article_number}</code> {i.name}</td>
                          <td>{i.supplier_article_number || '–'}</td>
                          <td style={{ textAlign: 'right' }}>{i.stock_quantity}</td>
                          <td style={{ textAlign: 'right' }}>{i.reserved_quantity || '–'}</td>
                          <td style={{ textAlign: 'right' }}>{i.on_order_quantity || '–'}</td>
                          <td style={{ textAlign: 'right' }}>{i.minimum_stock} / {i.target_stock ?? '–'}</td>
                          <td style={{ textAlign: 'right' }}>{formatEuro(i.unit_price)}</td>
                          <td>
                            <input
                              style={CELL}
                              inputMode="numeric"
                              aria-label={`Menge ${i.article_number}`}
                              value={sugQty[i.article_id] ?? ''}
                              onChange={(e) => setSugQty({ ...sugQty, [i.article_id]: e.target.value })}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="form-actions">
                  <button type="button" className="btn-primary" disabled={busy} onClick={() => createFromSuggestion(g)}>
                    Bestellung anlegen
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* ---------- Detailansicht ---------- */}
      {detail && (
        <div className="modal-overlay" onClick={closeDetail}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>
              Bestellung {detail.order_number}{' '}
              <span style={{ color: STATUS_COLORS[detail.status], fontSize: '0.9rem' }}>({STATUS_LABELS[detail.status]})</span>
            </h2>
            <p style={{ margin: '0 0 0.75rem' }}>
              <strong>{detail.supplier_name || supplierName(detail.supplier_id)}</strong>
              <br />
              Datum {formatDate(detail.order_date)}
              {detail.expected_date ? ` · Liefertermin ${formatDate(detail.expected_date)}` : ''}
              {detail.sent_to_email ? ` · gesendet an ${detail.sent_to_email}` : ''}
            </p>
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th>Pos</th>
                    <th>Bezeichnung</th>
                    <th>Lief.-Nr.</th>
                    <th style={{ textAlign: 'right' }}>Bestellt</th>
                    <th style={{ textAlign: 'right' }}>Geliefert</th>
                    <th style={{ textAlign: 'right' }}>EK netto</th>
                    <th style={{ textAlign: 'right' }}>Netto</th>
                    {receipt && <th style={{ width: 100 }}>Jetzt geliefert</th>}
                  </tr>
                </thead>
                <tbody>
                  {detail.items.map((it: any) => {
                    const open = it.quantity - it.received_quantity
                    return (
                      <tr key={it.id}>
                        <td>{it.position}</td>
                        <td>
                          {it.description}
                          {it.article_number && <div className="muted" style={{ fontSize: '0.8rem' }}>{it.article_number}</div>}
                          {!it.article_id && <div className="muted" style={{ fontSize: '0.8rem' }}>freie Position, kein Lagerartikel</div>}
                        </td>
                        <td>{it.supplier_article_number || '–'}</td>
                        <td style={{ textAlign: 'right' }}>{it.quantity} {it.unit || ''}</td>
                        <td style={{ textAlign: 'right', color: it.received_quantity >= it.quantity ? '#4ade80' : undefined }}>{it.received_quantity}</td>
                        <td style={{ textAlign: 'right' }}>{formatEuro(it.unit_price)}</td>
                        <td style={{ textAlign: 'right' }}>{formatEuro(it.line_total_net)}</td>
                        {receipt && (
                          <td>
                            {open > 0 ? (
                              <input
                                style={CELL}
                                inputMode="numeric"
                                aria-label={`Geliefert Position ${it.position}`}
                                value={receipt.qty[it.id] ?? ''}
                                onChange={(e) => setReceipt({ ...receipt, qty: { ...receipt.qty, [it.id]: e.target.value } })}
                              />
                            ) : (
                              <span className="muted">komplett</span>
                            )}
                          </td>
                        )}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <div style={{ textAlign: 'right', margin: '0.75rem 0' }}>
              <div>Netto: {formatEuro(detail.net_amount)}</div>
              <div>MwSt: {formatEuro(detail.vat_amount)}</div>
              <div style={{ fontWeight: 700 }}>Brutto: {formatEuro(detail.gross_amount)}</div>
            </div>
            {detail.internal_notes && (
              <p className="muted" style={{ whiteSpace: 'pre-wrap' }}><strong>Intern:</strong> {detail.internal_notes}</p>
            )}

            {receipt && (
              <div className="card" style={{ margin: '0.75rem 0', padding: '0.75rem' }}>
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="delivery-note">Lieferschein-Nr. (optional)</label>
                    <input id="delivery-note" value={receipt.delivery_note} maxLength={100} onChange={(e) => setReceipt({ ...receipt, delivery_note: e.target.value })} />
                  </div>
                  <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                    <label style={{ fontWeight: 400 }}>
                      <input type="checkbox" checked={receipt.update_price} onChange={(e) => setReceipt({ ...receipt, update_price: e.target.checked })} />{' '}
                      Bestellpreis als neuen EK-Preis im Artikel übernehmen
                    </label>
                  </div>
                </div>
                <p className="muted" style={{ fontSize: '0.85rem' }}>
                  Lagerartikel werden sofort ins Lager gebucht. Mehr geliefert als bestellt? Den Rest bitte unter „Lager“ als Zugang buchen.
                </p>
                <div className="form-actions">
                  <button type="button" className="btn-secondary" onClick={() => setReceipt(null)}>Abbrechen</button>
                  <button type="button" className="btn-primary" disabled={busy} onClick={doReceive}>Wareneingang buchen</button>
                </div>
              </div>
            )}

            {emailModal && (
              <div className="card" style={{ margin: '0.75rem 0', padding: '0.75rem' }}>
                <div className="form-group">
                  <label htmlFor="po-email">Empfänger (leer = E-Mail des Lieferanten)</label>
                  <input id="po-email" type="email" value={emailModal.recipient} onChange={(e) => setEmailModal({ recipient: e.target.value })} />
                </div>
                <div className="form-actions">
                  <button type="button" className="btn-secondary" onClick={() => setEmailModal(null)}>Abbrechen</button>
                  <button
                    type="button"
                    className="btn-primary"
                    disabled={busy}
                    onClick={async () => {
                      const res = await runAction(() => purchaseOrdersApi.sendEmail(detail.id, emailModal.recipient || undefined))
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
              <button type="button" className="btn-secondary" onClick={closeDetail}>Schließen</button>
              <button type="button" className="btn-secondary" onClick={() => openPdf(detail)}>PDF</button>
              {detail.status === 'draft' && (
                <>
                  <button type="button" className="btn-secondary" onClick={() => openEdit(detail)}>Bearbeiten</button>
                  <button type="button" className="btn-secondary" disabled={busy} onClick={() => doDelete(detail)}>Löschen</button>
                </>
              )}
              {isAdmin && detail.status === 'draft' && (
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => runAction(() => purchaseOrdersApi.markSent(detail.id))}>
                  Als bestellt markieren
                </button>
              )}
              {isAdmin && ['draft', 'sent', 'partial'].includes(detail.status) && (
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => { setReceipt(null); setEmailModal({ recipient: '' }) }}>
                  Per E-Mail senden
                </button>
              )}
              {isAdmin && isOpen(detail) && (
                <button type="button" className="btn-secondary" disabled={busy} onClick={() => doCancel(detail)}>
                  {detail.status === 'partial' ? 'Rest stornieren' : 'Stornieren'}
                </button>
              )}
              {isOpen(detail) && !receipt && (
                <button type="button" className="btn-primary" disabled={busy} onClick={() => startReceipt(detail)}>
                  Wareneingang
                </button>
              )}
            </div>
            {!isAdmin && detail.status === 'draft' && (
              <p className="muted" style={{ fontSize: '0.85rem' }}>Bestellen (E-Mail senden) braucht das Recht „Lager & Einkauf“.</p>
            )}
          </div>
        </div>
      )}

      {/* ---------- Formular ---------- */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 1100 }}>
            <h2>{editingId ? 'Bestellung bearbeiten' : 'Neue Bestellung'}</h2>
            <form onSubmit={handleSave}>
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="po-supplier">Lieferant *</label>
                  <select id="po-supplier" value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })} required>
                    <option value="">– bitte wählen –</option>
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="po-date">Bestelldatum *</label>
                  <input id="po-date" type="date" value={form.order_date} onChange={(e) => setForm({ ...form, order_date: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label htmlFor="po-expected">Gewünschter Liefertermin</label>
                  <input id="po-expected" type="date" value={form.expected_date} min={form.order_date} onChange={(e) => setForm({ ...form, expected_date: e.target.value })} />
                </div>
              </div>

              <div className="form-group" style={{ maxWidth: 360 }}>
                <label htmlFor="po-article-search">Artikel suchen</label>
                <input id="po-article-search" type="search" placeholder="Nummer, Name, Lief.-Nr." value={articleSearch} onChange={(e) => setArticleSearch(e.target.value)} />
              </div>

              <label style={{ fontWeight: 600 }}>Positionen (Einkaufspreise netto)</label>
              <div className="table-wrapper">
                <table className="table" style={{ tableLayout: 'fixed', width: '100%', minWidth: 760 }}>
                  <thead>
                    <tr>
                      <th>Artikel / Bezeichnung</th>
                      <th style={{ width: 120 }}>Lief.-Nr.</th>
                      <th style={{ width: 70 }}>Menge</th>
                      <th style={{ width: 70 }}>Einheit</th>
                      <th style={{ width: 90 }}>EK €</th>
                      <th style={{ width: 70 }}>MwSt %</th>
                      <th style={{ width: 95, textAlign: 'right' }}>Netto</th>
                      <th style={{ width: 45 }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {form.items.map((it, idx) => (
                      <tr key={idx}>
                        <td>
                          <select aria-label={`Artikel Position ${idx + 1}`} value={it.article_id} onChange={(e) => pickArticle(idx, e.target.value)} style={{ ...CELL, marginBottom: 4 }}>
                            <option value="">– freie Position (kein Lagerartikel) –</option>
                            {it.article_id && !filteredArticles.some((a) => a.id === it.article_id) && (
                              <option value={it.article_id}>{it.description}</option>
                            )}
                            {filteredArticles.map((a) => (
                              <option key={a.id} value={a.id}>{a.article_number} · {a.name}</option>
                            ))}
                          </select>
                          <input aria-label={`Bezeichnung Position ${idx + 1}`} value={it.description} placeholder="Bezeichnung" onChange={(e) => setItem(idx, { description: e.target.value })} style={CELL} />
                        </td>
                        <td><input aria-label={`Lieferanten-Nr. Position ${idx + 1}`} style={CELL} value={it.supplier_article_number} onChange={(e) => setItem(idx, { supplier_article_number: e.target.value })} /></td>
                        <td><input aria-label={`Menge Position ${idx + 1}`} style={CELL} inputMode="numeric" value={it.quantity} onChange={(e) => setItem(idx, { quantity: e.target.value })} /></td>
                        <td><input style={CELL} value={it.unit} onChange={(e) => setItem(idx, { unit: e.target.value })} /></td>
                        <td><input aria-label={`EK Position ${idx + 1}`} style={CELL} inputMode="decimal" value={it.unit_price} onChange={(e) => setItem(idx, { unit_price: e.target.value })} /></td>
                        <td>
                          <select style={CELL} value={it.vat_rate} onChange={(e) => setItem(idx, { vat_rate: e.target.value })}>
                            <option value="19">19</option>
                            <option value="7">7</option>
                            <option value="0">0</option>
                          </select>
                        </td>
                        <td style={{ textAlign: 'right' }}>{formatEuro(round2(toNum(it.quantity) * round2(toNum(it.unit_price))))}</td>
                        <td>
                          <button type="button" className="btn-secondary btn-sm" title="Entfernen" onClick={() => removeItem(idx)}>✕</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div style={{ margin: '0.5rem 0 1rem' }}>
                <button type="button" className="btn-secondary btn-sm" onClick={() => setForm((f) => ({ ...f, items: [...f.items, emptyItem()] }))}>+ Position</button>
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
                  <label htmlFor="po-notes">Hinweis an den Lieferanten (erscheint auf dem PDF)</label>
                  <textarea id="po-notes" rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                </div>
                <div className="form-group">
                  <label htmlFor="po-internal">Interne Notiz (nicht auf dem PDF)</label>
                  <textarea id="po-internal" rows={2} value={form.internal_notes} onChange={(e) => setForm({ ...form, internal_notes: e.target.value })} />
                </div>
              </div>
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
