import { useEffect, useState } from 'react'
import { useSearchParams, useLocation } from 'react-router-dom'
import { invoicesApi, customersApi, workshopOrdersApi } from '../api/client'

const STATUS_LABELS: Record<string, string> = {
  draft: 'Entwurf',
  issued: 'Ausgestellt',
  partially_paid: 'Teilweise bezahlt',
  paid: 'Bezahlt',
  cancelled: 'Storniert',
}

export default function Invoices() {
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const workshopOrderIdFromState = (location.state as { workshopOrderId?: string })?.workshopOrderId
  const [invoices, setInvoices] = useState<any[]>([])
  const [customers, setCustomers] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [overdueFilter, setOverdueFilter] = useState(searchParams.get('overdue') === '1')
  const [form, setForm] = useState({
    customer_id: '',
    workshop_order_id: '',
    invoice_date: new Date().toISOString().slice(0, 10),
    due_date: '',
    notes: '',
    items: [{ description: '', quantity: 1, unit: 'Stk', unit_price: 0, vat_rate: 19 }] as { description: string; quantity: number; unit: string; unit_price: number; vat_rate: number }[],
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [previewModal, setPreviewModal] = useState<{ invoiceNumber: string; url: string } | null>(null)

  useEffect(() => {
    Promise.all([
      invoicesApi.list({ status_filter: statusFilter || undefined, overdue: overdueFilter }),
      customersApi.list(),
      workshopOrdersApi.list(),
    ])
      .then(([invs, custs, ords]) => {
        setInvoices(invs)
        setCustomers(custs)
        setOrders(ords.filter((o: any) => o.status !== 'invoiced'))
      })
      .finally(() => setLoading(false))
  }, [statusFilter, overdueFilter])

  useEffect(() => {
    if (form.workshop_order_id) {
      const ord = orders.find((o: any) => o.id === form.workshop_order_id)
      if (ord) setForm((f) => ({ ...f, customer_id: ord.customer_id }))
    }
  }, [form.workshop_order_id, orders])

  useEffect(() => {
    if (!workshopOrderIdFromState || orders.length === 0) return
    const ord = orders.find((o: any) => o.id === workshopOrderIdFromState)
    if (ord) {
      setForm((f) => ({ ...f, workshop_order_id: ord.id, customer_id: ord.customer_id }))
      setShowForm(true)
    }
    window.history.replaceState({}, '', location.pathname)
  }, [workshopOrderIdFromState, orders, location.pathname])

  const getCustomerName = (customerId: string) => {
    const c = customers.find((x) => x.id === customerId)
    if (!c) return '–'
    return c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || '–'
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.customer_id) {
      setError('Bitte Kunde auswählen.')
      return
    }
    if (form.workshop_order_id) {
      if (!form.invoice_date) {
        setError('Rechnungsdatum erforderlich.')
        return
      }
      const ord = orders.find((o: any) => o.id === form.workshop_order_id)
      const customerId = ord?.customer_id || form.customer_id
      setSubmitting(true)
      try {
        await invoicesApi.create({
          customer_id: customerId,
          workshop_order_id: form.workshop_order_id,
          invoice_date: form.invoice_date,
          due_date: form.due_date || undefined,
          notes: form.notes || undefined,
        })
        setShowForm(false)
        setForm({ customer_id: '', workshop_order_id: '', invoice_date: new Date().toISOString().slice(0, 10), due_date: '', notes: '', items: [{ description: '', quantity: 1, unit: 'Stk', unit_price: 0, vat_rate: 19 }] })
        const updated = await invoicesApi.list({ status_filter: statusFilter || undefined, overdue: overdueFilter })
        setInvoices(updated)
        const ords = await workshopOrdersApi.list()
        setOrders(ords.filter((o: any) => o.status !== 'invoiced'))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Anlegen')
      } finally {
        setSubmitting(false)
      }
    } else {
      const validItems = form.items.filter((i) => i.description.trim())
      if (validItems.length === 0) {
        setError('Mindestens eine Position mit Beschreibung erforderlich.')
        return
      }
      setSubmitting(true)
      try {
        await invoicesApi.create({
          customer_id: form.customer_id,
          invoice_date: form.invoice_date,
          due_date: form.due_date || undefined,
          notes: form.notes || undefined,
          items: validItems.map((i) => ({
            description: i.description,
            quantity: i.quantity,
            unit: i.unit || undefined,
            unit_price: i.unit_price,
            vat_rate: i.vat_rate,
          })),
        })
        setShowForm(false)
        setForm({ customer_id: '', workshop_order_id: '', invoice_date: new Date().toISOString().slice(0, 10), due_date: '', notes: '', items: [{ description: '', quantity: 1, unit: 'Stk', unit_price: 0, vat_rate: 19 }] })
        const updated = await invoicesApi.list({ status_filter: statusFilter || undefined, overdue: overdueFilter })
        setInvoices(updated)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Anlegen')
      } finally {
        setSubmitting(false)
      }
    }
  }

  const handleIssue = async (id: string) => {
    try {
      await invoicesApi.issue(id)
      setInvoices((prev) => prev.map((i) => (i.id === id ? { ...i, status: 'issued' } : i)))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleMarkPaid = async (id: string) => {
    try {
      await invoicesApi.markPaid(id)
      setInvoices((prev) => prev.map((i) => (i.id === id ? { ...i, status: 'paid' } : i)))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleMarkReminder = async (id: string, level: 1 | 2 | 3) => {
    try {
      const updated = await invoicesApi.markReminder(id, level)
      setInvoices((prev) => prev.map((i) => (i.id === id ? { ...i, reminder_level: updated.reminder_level, reminder_date: updated.reminder_date } : i)))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleDownloadPdf = async (id: string, invoiceNumber: string) => {
    try {
      const blob = await invoicesApi.downloadPdf(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Rechnung_${invoiceNumber}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'PDF konnte nicht geladen werden')
    }
  }

  const handleDownloadZugferd = async (id: string, invoiceNumber: string) => {
    try {
      const blob = await invoicesApi.downloadZugferd(id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Rechnung_${invoiceNumber}_ZUGFeRD.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'ZUGFeRD konnte nicht geladen werden')
    }
  }

  const handlePreviewPdf = async (id: string, invoiceNumber: string) => {
    try {
      const blob = await invoicesApi.downloadPdf(id)
      const url = URL.createObjectURL(blob)
      setPreviewModal({ invoiceNumber, url })
    } catch (err) {
      alert(err instanceof Error ? err.message : 'PDF konnte nicht geladen werden')
    }
  }

  const closePreview = () => {
    if (previewModal) {
      URL.revokeObjectURL(previewModal.url)
      setPreviewModal(null)
    }
  }

  const addItem = () => {
    setForm((f) => ({ ...f, items: [...f.items, { description: '', quantity: 1, unit: 'Stk', unit_price: 0, vat_rate: 19 }] }))
  }

  const removeItem = (idx: number) => {
    setForm((f) => ({ ...f, items: f.items.filter((_, i) => i !== idx) }))
  }

  const updateItem = (idx: number, field: string, value: string | number) => {
    setForm((f) => ({
      ...f,
      items: f.items.map((it, i) => (i === idx ? { ...it, [field]: value } : it)),
    }))
  }

  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    } catch {
      return '–'
    }
  }

  const isOverdue = (inv: any) => {
    if (!inv.due_date || inv.status === 'paid' || inv.status === 'cancelled') return false
    return new Date(inv.due_date) < new Date(new Date().toISOString().slice(0, 10))
  }

  return (
    <div className="page">
      <h1>Rechnungen</h1>
      <div className="toolbar">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="select">
          <option value="">Alle Status</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input type="checkbox" checked={overdueFilter} onChange={(e) => setOverdueFilter(e.target.checked)} />
          Überfällig
        </label>
        <button type="button" onClick={() => setShowForm(true)} className="btn-primary">
          + Neue Rechnung
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>Neue Rechnung</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Quelle</label>
                <select
                  value={form.workshop_order_id}
                  onChange={(e) => setForm({ ...form, workshop_order_id: e.target.value })}
                >
                  <option value="">Manuell (Positionen eingeben)</option>
                  {orders.map((o: any) => (
                    <option key={o.id} value={o.id}>
                      {o.order_number} – {getCustomerName(o.customer_id)}
                    </option>
                  ))}
                </select>
              </div>
              {!form.workshop_order_id && (
                <div className="form-group">
                  <label htmlFor="inv-customer">Kunde *</label>
                  <select
                    id="inv-customer"
                    value={form.customer_id}
                    onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
                    required={!form.workshop_order_id}
                  >
                    <option value="">– Bitte wählen –</option>
                    {customers.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || c.email || c.id}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="inv-date">Rechnungsdatum *</label>
                  <input
                    id="inv-date"
                    type="date"
                    value={form.invoice_date}
                    onChange={(e) => setForm({ ...form, invoice_date: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="inv-due">Fällig am</label>
                  <input
                    id="inv-due"
                    type="date"
                    value={form.due_date}
                    onChange={(e) => setForm({ ...form, due_date: e.target.value })}
                  />
                </div>
              </div>
              {!form.workshop_order_id && (
                <>
                  <div className="form-group">
                    <label>Positionen</label>
                    {form.items.map((it, idx) => (
                      <div key={idx} className="invoice-item-row">
                        <input
                          placeholder="Beschreibung"
                          value={it.description}
                          onChange={(e) => updateItem(idx, 'description', e.target.value)}
                          className="invoice-item-desc"
                        />
                        <input
                          type="number"
                          placeholder="Menge"
                          value={it.quantity}
                          onChange={(e) => updateItem(idx, 'quantity', parseFloat(e.target.value) || 0)}
                          className="invoice-item-qty"
                        />
                        <input
                          placeholder="Einheit"
                          value={it.unit}
                          onChange={(e) => updateItem(idx, 'unit', e.target.value)}
                          className="invoice-item-unit"
                        />
                        <input
                          type="number"
                          step="0.01"
                          placeholder="Preis"
                          value={it.unit_price}
                          onChange={(e) => updateItem(idx, 'unit_price', parseFloat(e.target.value) || 0)}
                          className="invoice-item-price"
                        />
                        <input
                          type="number"
                          step="0.01"
                          placeholder="MwSt %"
                          value={it.vat_rate}
                          onChange={(e) => updateItem(idx, 'vat_rate', parseFloat(e.target.value) || 0)}
                          className="invoice-item-vat"
                        />
                        <button type="button" onClick={() => removeItem(idx)} className="btn-icon">
                          ×
                        </button>
                      </div>
                    ))}
                    <button type="button" onClick={addItem} className="btn-secondary btn-sm">
                      + Position
                    </button>
                  </div>
                </>
              )}
              <div className="form-group">
                <label htmlFor="inv-notes">Anmerkungen</label>
                <textarea
                  id="inv-notes"
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  rows={2}
                />
              </div>
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
                  Abbrechen
                </button>
                <button type="submit" disabled={submitting} className="btn-primary">
                  {submitting ? 'Wird erstellt...' : 'Rechnung anlegen'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {previewModal && (
        <div className="modal-overlay" onClick={closePreview}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 900 }}>
            <h2>Rechnungsvorschau: {previewModal.invoiceNumber}</h2>
            <div style={{ height: '70vh', minHeight: 400, borderRadius: 8, overflow: 'hidden', background: '#1e293b' }}>
              <iframe
                src={previewModal.url}
                title={`Rechnung ${previewModal.invoiceNumber}`}
                style={{ width: '100%', height: '100%', border: 'none' }}
              />
            </div>
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={closePreview} className="btn-secondary">
                Schließen
              </button>
              <button
                type="button"
                onClick={() => {
                  const a = document.createElement('a')
                  a.href = previewModal.url
                  a.download = `Rechnung_${previewModal.invoiceNumber}.pdf`
                  a.click()
                }}
                className="btn-primary"
              >
                PDF herunterladen
              </button>
            </div>
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
              <th>Rechnungsnr.</th>
              <th>Status</th>
              <th>Mahnung</th>
              <th>Kunde</th>
              <th>Datum</th>
              <th>Fällig</th>
              <th>Brutto</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {invoices.length === 0 ? (
              <tr>
                <td colSpan={8}>Keine Rechnungen vorhanden.</td>
              </tr>
            ) : (
              invoices.map((inv) => (
                <tr key={inv.id} className={isOverdue(inv) ? 'warning-row' : ''}>
                  <td><strong>{inv.invoice_number}</strong></td>
                  <td>
                    {STATUS_LABELS[inv.status] || inv.status}
                    {isOverdue(inv) && <span className="warning" style={{ marginLeft: 4 }}>überfällig</span>}
                  </td>
                  <td>
                    {inv.reminder_level > 0 ? (
                      <span title={inv.reminder_date ? `am ${formatDate(inv.reminder_date)}` : ''}>
                        {inv.reminder_level}. Mahnung
                      </span>
                    ) : (
                      isOverdue(inv) && (inv.status === 'issued' || inv.status === 'partially_paid') ? (
                        <button type="button" onClick={() => handleMarkReminder(inv.id, 1)} className="btn-secondary btn-sm">
                          1. Mahnung
                        </button>
                      ) : '–'
                    )}
                    {inv.reminder_level === 1 && isOverdue(inv) && (
                      <button type="button" onClick={() => handleMarkReminder(inv.id, 2)} className="btn-secondary btn-sm" style={{ marginLeft: 4 }}>
                        2. Mahnung
                      </button>
                    )}
                    {inv.reminder_level === 2 && isOverdue(inv) && (
                      <button type="button" onClick={() => handleMarkReminder(inv.id, 3)} className="btn-secondary btn-sm" style={{ marginLeft: 4 }}>
                        3. Mahnung
                      </button>
                    )}
                  </td>
                  <td>{getCustomerName(inv.customer_id)}</td>
                  <td>{formatDate(inv.invoice_date)}</td>
                  <td>{inv.due_date ? formatDate(inv.due_date) : '–'}</td>
                  <td>{Number(inv.gross_amount).toFixed(2)} €</td>
                  <td>
                    {inv.status === 'draft' && (
                      <>
                        <button
                          type="button"
                          onClick={() => handlePreviewPdf(inv.id, inv.invoice_number)}
                          className="btn-secondary btn-sm"
                        >
                          Vorschau
                        </button>
                        <button
                          type="button"
                          onClick={() => handleIssue(inv.id)}
                          className="btn-secondary btn-sm"
                        >
                          Ausstellen
                        </button>
                      </>
                    )}
                    {(inv.status === 'issued' || inv.status === 'partially_paid') && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleMarkPaid(inv.id)}
                          className="btn-secondary btn-sm"
                        >
                          Als bezahlt
                        </button>
                        <button
                          type="button"
                          onClick={() => handlePreviewPdf(inv.id, inv.invoice_number)}
                          className="btn-secondary btn-sm"
                        >
                          Vorschau
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDownloadPdf(inv.id, inv.invoice_number)}
                          className="btn-secondary btn-sm"
                        >
                          PDF
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDownloadZugferd(inv.id, inv.invoice_number)}
                          className="btn-secondary btn-sm"
                        >
                          ZUGFeRD
                        </button>
                      </>
                    )}
                    {(inv.status === 'paid') && (
                      <>
                        <button
                          type="button"
                          onClick={() => handlePreviewPdf(inv.id, inv.invoice_number)}
                          className="btn-secondary btn-sm"
                        >
                          Vorschau
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDownloadPdf(inv.id, inv.invoice_number)}
                          className="btn-secondary btn-sm"
                        >
                          PDF
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDownloadZugferd(inv.id, inv.invoice_number)}
                          className="btn-secondary btn-sm"
                        >
                          ZUGFeRD
                        </button>
                      </>
                    )}
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
