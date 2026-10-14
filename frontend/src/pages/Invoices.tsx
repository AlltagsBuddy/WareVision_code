import { useEffect, useState } from 'react'
import { useSearchParams, useLocation } from 'react-router-dom'
import { invoicesApi, customersApi, workshopOrdersApi } from '../api/client'
import PreviewModal from '../components/PreviewModal'
import InvoiceCorrectionModal from '../components/InvoiceCorrectionModal'

const STATUS_LABELS: Record<string, string> = {
  draft: 'Entwurf',
  issued: 'Ausgestellt',
  partially_paid: 'Teilweise bezahlt',
  paid: 'Bezahlt',
  cancelled: 'Storniert',
}

const DOC_LABELS: Record<string, string> = { cancellation: 'Stornorechnung', correction: 'Rechnungskorrektur' }

/** Status-Text: Bei Rechnungskorrekturen geht es um eine Erstattung, nicht um eine Zahlung des Kunden */
const statusLabel = (inv: any) => {
  if (inv.document_type === 'correction') {
    if (inv.status === 'issued') return 'Erstattung offen'
    if (inv.status === 'paid') return 'Erstattet/verrechnet'
  }
  return STATUS_LABELS[inv.status] || inv.status
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
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState('invoice_date')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [form, setForm] = useState({
    customer_id: '',
    workshop_order_id: '',
    invoice_date: new Date().toISOString().slice(0, 10),
    service_date: '',
    due_date: '',
    notes: '',
    items: [{ description: '', quantity: 1, unit: 'Stk', unit_price: 0, vat_rate: 19 }] as { description: string; quantity: number; unit: string; unit_price: number; vat_rate: number }[],
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [previewModal, setPreviewModal] = useState<{ invoiceNumber: string; url: string } | null>(null)
  const [sendEmailModal, setSendEmailModal] = useState<{ inv: any; recipientEmail: string } | null>(null)
  const [cancelModal, setCancelModal] = useState<{ inv: any; reason: string } | null>(null)
  const [cancelError, setCancelError] = useState('')
  const [cancelSubmitting, setCancelSubmitting] = useState(false)
  const [confirmModal, setConfirmModal] = useState<{ title: string; message: string; onConfirm: () => Promise<void> } | null>(null)
  const [confirmError, setConfirmError] = useState('')
  const [confirmSubmitting, setConfirmSubmitting] = useState(false)
  const [zugferdImportResult, setZugferdImportResult] = useState<any | null>(null)
  const [zugferdImporting, setZugferdImporting] = useState(false)
  const [zugferdImportError, setZugferdImportError] = useState('')
  const [reminderError, setReminderError] = useState('')
  const [correctionFor, setCorrectionFor] = useState<any | null>(null)
  const [correctionDone, setCorrectionDone] = useState<any | null>(null)

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

  const getCustomerEmail = (customerId: string) => {
    const c = customers.find((x) => x.id === customerId)
    return c?.email || ''
  }

  const handleSendEmail = (inv: any) => {
    setSendEmailModal({ inv, recipientEmail: getCustomerEmail(inv.customer_id) })
  }

  const handleSendEmailSubmit = async () => {
    if (!sendEmailModal) return
    const email = sendEmailModal.recipientEmail.trim()
    if (!email) {
      alert('Bitte E-Mail-Adresse eingeben.')
      return
    }
    try {
      await invoicesApi.sendEmail(sendEmailModal.inv.id, email)
      alert(`Rechnung wurde an ${email} versendet.`)
      setSendEmailModal(null)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'E-Mail-Versand fehlgeschlagen')
    }
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
          service_date: form.service_date || undefined,
          due_date: form.due_date || undefined,
          notes: form.notes || undefined,
        })
        setShowForm(false)
        setForm({ customer_id: '', workshop_order_id: '', invoice_date: new Date().toISOString().slice(0, 10), service_date: '', due_date: '', notes: '', items: [{ description: '', quantity: 1, unit: 'Stk', unit_price: 0, vat_rate: 19 }] })
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
          service_date: form.service_date || undefined,
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
        setForm({ customer_id: '', workshop_order_id: '', invoice_date: new Date().toISOString().slice(0, 10), service_date: '', due_date: '', notes: '', items: [{ description: '', quantity: 1, unit: 'Stk', unit_price: 0, vat_rate: 19 }] })
        const updated = await invoicesApi.list({ status_filter: statusFilter || undefined, overdue: overdueFilter })
        setInvoices(updated)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Anlegen')
      } finally {
        setSubmitting(false)
      }
    }
  }

  const runConfirm = async () => {
    if (!confirmModal) return
    setConfirmError('')
    setConfirmSubmitting(true)
    try {
      await confirmModal.onConfirm()
      setConfirmModal(null)
    } catch (err) {
      setConfirmError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setConfirmSubmitting(false)
    }
  }

  const handleIssue = (inv: any) => {
    setConfirmError('')
    setConfirmModal({
      title: 'Rechnung ausstellen',
      message: `Rechnung ${inv.invoice_number} wirklich ausstellen? Sie kann danach nicht mehr bearbeitet werden.`,
      onConfirm: async () => {
        await invoicesApi.issue(inv.id)
        setInvoices((prev) => prev.map((i) => (i.id === inv.id ? { ...i, status: 'issued' } : i)))
      },
    })
  }

  const handleMarkPaid = (inv: any) => {
    setConfirmError('')
    const isCorrection = inv.document_type === 'correction'
    setConfirmModal({
      title: isCorrection ? 'Als erstattet markieren' : 'Als bezahlt markieren',
      message: isCorrection
        ? `Rechnungskorrektur ${inv.invoice_number} als erstattet bzw. verrechnet markieren?`
        : `Rechnung ${inv.invoice_number} als bezahlt markieren?`,
      onConfirm: async () => {
        await invoicesApi.markPaid(inv.id)
        setInvoices((prev) => prev.map((i) => (i.id === inv.id ? { ...i, status: 'paid' } : i)))
      },
    })
  }

  const handleCancelConfirm = async () => {
    if (!cancelModal) return
    setCancelError('')
    setCancelSubmitting(true)
    try {
      await invoicesApi.cancel(cancelModal.inv.id, cancelModal.reason)
      setCancelModal(null)
      const updated = await invoicesApi.list({ status_filter: statusFilter || undefined, overdue: overdueFilter })
      setInvoices(updated)
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : 'Stornierung fehlgeschlagen')
    } finally {
      setCancelSubmitting(false)
    }
  }

  const handleMarkReminder = async (id: string, level: 1 | 2 | 3) => {
    setReminderError('')
    try {
      const updated = await invoicesApi.markReminder(id, level)
      setInvoices((prev) => prev.map((i) => (i.id === id ? { ...i, reminder_level: updated.reminder_level, reminder_date: updated.reminder_date } : i)))
    } catch (err) {
      setReminderError(err instanceof Error ? err.message : 'Fehler beim Setzen der Mahnstufe')
    }
  }

  const handleDownloadReminderPdf = async (inv: any) => {
    try {
      const blob = await invoicesApi.downloadReminderPdf(inv.id)
      const subjects: Record<number, string> = { 1: 'Zahlungserinnerung', 2: '1_Mahnung', 3: '2_Mahnung' }
      const label = subjects[inv.reminder_level as number] ?? `Mahnung_${inv.reminder_level}`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${label}_${inv.invoice_number}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setReminderError(err instanceof Error ? err.message : 'Mahnbrief konnte nicht geladen werden')
    }
  }

  const handleZugferdImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setZugferdImportError('')
    setZugferdImporting(true)
    try {
      const result = await invoicesApi.importZugferd(file)
      setZugferdImportResult(result)
    } catch (err) {
      setZugferdImportError(err instanceof Error ? err.message : 'Import fehlgeschlagen')
    } finally {
      setZugferdImporting(false)
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
    // Entwürfe können nicht überfällig sein – sie wurden noch nicht ausgestellt
    if (!inv.due_date || inv.status === 'draft' || inv.status === 'paid' || inv.status === 'cancelled') return false
    // Storno- und Korrekturbelege sind keine Forderungen
    if (inv.document_type && inv.document_type !== 'invoice') return false
    return new Date(inv.due_date) < new Date(new Date().toISOString().slice(0, 10))
  }

  // Rechnungskorrekturen je Originalrechnung (nicht stornierte) und Bezugsnummer eines Beleges
  const correctionsOf = (id: string) =>
    invoices.filter((i) => i.document_type === 'correction' && i.corrects_invoice_id === id && i.status !== 'cancelled')
  const refNumber = (inv: any) => {
    const refId = inv.corrects_invoice_id || inv.cancellation_of_id
    return refId ? invoices.find((i) => i.id === refId)?.invoice_number : undefined
  }

  const handleCorrectionCreated = async (created: any) => {
    setCorrectionFor(null)
    setCorrectionDone(created)
    setInvoices(await invoicesApi.list({ status_filter: statusFilter || undefined, overdue: overdueFilter }))
  }

  const handleSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    else { setSortField(field); setSortDir('asc') }
  }
  const sortIcon = (field: string) => sortField === field ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ' ↕'

  const q = search.toLowerCase()
  const displayed = [...invoices]
    .filter((inv) =>
      !q ||
      (inv.invoice_number || '').toLowerCase().includes(q) ||
      getCustomerName(inv.customer_id).toLowerCase().includes(q)
    )
    .sort((a, b) => {
      let va = '', vb = ''
      if (sortField === 'invoice_number') { va = a.invoice_number || ''; vb = b.invoice_number || '' }
      else if (sortField === 'customer') { va = getCustomerName(a.customer_id); vb = getCustomerName(b.customer_id) }
      else if (sortField === 'gross_amount') {
        return sortDir === 'asc'
          ? Number(a.gross_amount) - Number(b.gross_amount)
          : Number(b.gross_amount) - Number(a.gross_amount)
      }
      else if (sortField === 'due_date') { va = a.due_date || ''; vb = b.due_date || '' }
      else { va = a.invoice_date || ''; vb = b.invoice_date || '' }
      return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va)
    })

  return (
    <div className="page">
      <h1>Rechnungen</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Rechnungsnr., Kunde..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
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
        <label className="btn-secondary" style={{ cursor: 'pointer' }}>
          {zugferdImporting ? 'Lese...' : 'ZUGFeRD importieren'}
          <input type="file" accept=".pdf,application/pdf" style={{ display: 'none' }} onChange={handleZugferdImport} disabled={zugferdImporting} />
        </label>
        {zugferdImportError && <span className="error" style={{ fontSize: '0.85rem' }}>{zugferdImportError}</span>}
        {reminderError && <span className="error" style={{ fontSize: '0.85rem' }}>{reminderError}</span>}
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
                  <label htmlFor="inv-service">Leistungsdatum</label>
                  <input
                    id="inv-service"
                    type="date"
                    value={form.service_date}
                    onChange={(e) => setForm({ ...form, service_date: e.target.value })}
                    title="Leer lassen = Rechnungsdatum"
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

      {sendEmailModal && (
        <div className="modal-overlay" onClick={() => setSendEmailModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Rechnung per E-Mail versenden</h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
              Rechnung {sendEmailModal.inv.invoice_number} wird als PDF-Anhang versendet. Der Versand wird im Audit-Log dokumentiert.
            </p>
            <div className="form-group">
              <label>Empfänger-E-Mail *</label>
              <input
                type="email"
                value={sendEmailModal.recipientEmail}
                onChange={(e) => setSendEmailModal({ ...sendEmailModal, recipientEmail: e.target.value })}
                placeholder="kunde@beispiel.de"
              />
            </div>
            <div className="form-actions">
              <button type="button" onClick={() => setSendEmailModal(null)} className="btn-secondary">Abbrechen</button>
              <button type="button" onClick={handleSendEmailSubmit} className="btn-primary">Versenden</button>
            </div>
          </div>
        </div>
      )}

      {previewModal && (
        <PreviewModal
          title={`Rechnung ${previewModal.invoiceNumber}`}
          url={previewModal.url}
          type="pdf"
          onClose={closePreview}
        />
      )}

      {loading ? (
        <p>Laden...</p>
      ) : (
        <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr>
              <th onClick={() => handleSort('invoice_number')} style={{ cursor: 'pointer' }}>Rechnungsnr.{sortIcon('invoice_number')}</th>
              <th>Status</th>
              <th>Mahnung</th>
              <th onClick={() => handleSort('customer')} style={{ cursor: 'pointer' }}>Kunde{sortIcon('customer')}</th>
              <th onClick={() => handleSort('invoice_date')} style={{ cursor: 'pointer' }}>Datum{sortIcon('invoice_date')}</th>
              <th onClick={() => handleSort('due_date')} style={{ cursor: 'pointer' }}>Fällig{sortIcon('due_date')}</th>
              <th onClick={() => handleSort('gross_amount')} style={{ cursor: 'pointer' }}>Brutto{sortIcon('gross_amount')}</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {displayed.length === 0 ? (
              <tr>
                <td colSpan={8}>Keine Rechnungen vorhanden.</td>
              </tr>
            ) : (
              displayed.map((inv) => (
                <tr key={inv.id} className={isOverdue(inv) ? 'warning-row' : ''}>
                  <td>
                    <strong>{inv.invoice_number}</strong>
                    {DOC_LABELS[inv.document_type] && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                        {DOC_LABELS[inv.document_type]}
                        {refNumber(inv) ? ` zu ${refNumber(inv)}` : ''}
                      </div>
                    )}
                    {correctionsOf(inv.id).length > 0 && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                        korrigiert durch {correctionsOf(inv.id).map((c) => c.invoice_number).join(', ')}
                      </div>
                    )}
                  </td>
                  <td>
                    {statusLabel(inv)}
                    {isOverdue(inv) && <span className="warning" style={{ marginLeft: 4 }}>überfällig</span>}
                  </td>
                  <td>
                    {inv.reminder_level > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <span title={inv.reminder_date ? `am ${formatDate(inv.reminder_date)}` : ''}>
                          {inv.reminder_level === 1 ? 'Zahlungserinnerung' : `${inv.reminder_level - 1}. Mahnung`}
                          {inv.reminder_date && <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginLeft: 4 }}>({formatDate(inv.reminder_date)})</span>}
                        </span>
                        <button type="button" onClick={() => handleDownloadReminderPdf(inv)} className="btn-secondary btn-sm">
                          Mahnbrief PDF
                        </button>
                        {inv.reminder_level < 3 && isOverdue(inv) && (
                          <button type="button" onClick={() => handleMarkReminder(inv.id, (inv.reminder_level + 1) as 2 | 3)} className="btn-secondary btn-sm">
                            {inv.reminder_level === 1 ? '1. Mahnung' : '2. Mahnung'}
                          </button>
                        )}
                      </div>
                    ) : (
                      isOverdue(inv) && (inv.status === 'issued' || inv.status === 'partially_paid') ? (
                        <button type="button" onClick={() => handleMarkReminder(inv.id, 1)} className="btn-secondary btn-sm">
                          Erinnerung
                        </button>
                      ) : '–'
                    )}
                  </td>
                  <td>{getCustomerName(inv.customer_id)}</td>
                  <td>{formatDate(inv.invoice_date)}</td>
                  <td>{inv.due_date && (!inv.document_type || inv.document_type === 'invoice') ? formatDate(inv.due_date) : '–'}</td>
                  <td>{Number(inv.gross_amount).toFixed(2)} €</td>
                  <td>
                    {inv.status === 'draft' && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleSendEmail(inv)}
                          className="btn-secondary btn-sm"
                        >
                          E-Mail
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
                          onClick={() => handleIssue(inv)}
                          className="btn-secondary btn-sm"
                        >
                          Ausstellen
                        </button>
                        <button
                          type="button"
                          onClick={() => { setCancelModal({ inv, reason: '' }); setCancelError('') }}
                          className="btn-secondary btn-sm"
                          style={{ color: 'var(--color-error)' }}
                        >
                          Stornieren
                        </button>
                      </>
                    )}
                    {(inv.status === 'issued' || inv.status === 'partially_paid') && (
                      <>
                        {inv.document_type !== 'cancellation' && (
                          <button
                            type="button"
                            onClick={() => handleMarkPaid(inv)}
                            className="btn-secondary btn-sm"
                          >
                            {inv.document_type === 'correction' ? 'Als erstattet' : 'Als bezahlt'}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleSendEmail(inv)}
                          className="btn-secondary btn-sm"
                        >
                          E-Mail
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
                        {inv.document_type === 'invoice' && (
                          <button
                            type="button"
                            onClick={() => setCorrectionFor(inv)}
                            className="btn-secondary btn-sm"
                          >
                            Gutschrift / Korrektur
                          </button>
                        )}
                        {inv.document_type !== 'cancellation' && correctionsOf(inv.id).length === 0 && (
                          <button
                            type="button"
                            onClick={() => { setCancelModal({ inv, reason: '' }); setCancelError('') }}
                            className="btn-secondary btn-sm"
                            style={{ color: 'var(--color-error)' }}
                          >
                            Stornieren
                          </button>
                        )}
                      </>
                    )}
                    {inv.status === 'cancelled' && (
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
                      </>
                    )}
                    {(inv.status === 'paid') && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleSendEmail(inv)}
                          className="btn-secondary btn-sm"
                        >
                          E-Mail
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
                        {inv.document_type === 'invoice' && (
                          <button
                            type="button"
                            onClick={() => setCorrectionFor(inv)}
                            className="btn-secondary btn-sm"
                          >
                            Gutschrift / Korrektur
                          </button>
                        )}
                        {inv.document_type !== 'cancellation' && correctionsOf(inv.id).length === 0 && (
                          <button
                            type="button"
                            onClick={() => { setCancelModal({ inv, reason: '' }); setCancelError('') }}
                            className="btn-secondary btn-sm"
                            style={{ color: 'var(--color-error)' }}
                          >
                            Stornieren
                          </button>
                        )}
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

      {confirmModal && (
        <div className="modal-overlay" onClick={() => setConfirmModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{confirmModal.title}</h2>
            <p>{confirmModal.message}</p>
            {confirmError && <p className="error" style={{ marginTop: '0.75rem' }}>{confirmError}</p>}
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={() => setConfirmModal(null)} className="btn-secondary">
                Abbrechen
              </button>
              <button type="button" onClick={runConfirm} disabled={confirmSubmitting} className="btn-primary">
                {confirmSubmitting ? 'Wird gespeichert...' : 'Bestätigen'}
              </button>
            </div>
          </div>
        </div>
      )}

      {zugferdImportResult && (
        <div className="modal-overlay" onClick={() => setZugferdImportResult(null)}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>ZUGFeRD – Importierte Rechnungsdaten</h2>
            <div style={{ fontSize: '0.9rem' }}>
              <table className="table" style={{ marginBottom: '1rem' }}>
                <tbody>
                  <tr><td><strong>Rechnungsnummer</strong></td><td>{zugferdImportResult.invoice_number || '–'}</td></tr>
                  <tr><td><strong>Rechnungsdatum</strong></td><td>{zugferdImportResult.invoice_date || '–'}</td></tr>
                  <tr><td><strong>Fällig</strong></td><td>{zugferdImportResult.due_date || '–'}</td></tr>
                  <tr><td><strong>Währung</strong></td><td>{zugferdImportResult.currency || '–'}</td></tr>
                  <tr><td><strong>Aussteller</strong></td><td>
                    {zugferdImportResult.seller?.name || '–'}
                    {zugferdImportResult.seller?.vat_id ? ` (USt-IdNr.: ${zugferdImportResult.seller.vat_id})` : ''}
                    {zugferdImportResult.seller?.street ? `, ${zugferdImportResult.seller.street}` : ''}
                    {zugferdImportResult.seller?.postal_code ? `, ${zugferdImportResult.seller.postal_code}` : ''}
                    {zugferdImportResult.seller?.city ? ` ${zugferdImportResult.seller.city}` : ''}
                  </td></tr>
                  <tr><td><strong>Empfänger</strong></td><td>{zugferdImportResult.buyer?.name || '–'}</td></tr>
                  <tr><td><strong>Netto</strong></td><td>{zugferdImportResult.net_amount ? `${zugferdImportResult.net_amount} ${zugferdImportResult.currency}` : '–'}</td></tr>
                  <tr><td><strong>MwSt</strong></td><td>{zugferdImportResult.vat_amount ? `${zugferdImportResult.vat_amount} ${zugferdImportResult.currency}` : '–'}</td></tr>
                  <tr><td><strong>Brutto</strong></td><td><strong>{zugferdImportResult.gross_amount ? `${zugferdImportResult.gross_amount} ${zugferdImportResult.currency}` : '–'}</strong></td></tr>
                </tbody>
              </table>
              {zugferdImportResult.items?.length > 0 && (
                <>
                  <h3 style={{ marginBottom: '0.5rem' }}>Positionen</h3>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Pos</th>
                        <th>Beschreibung</th>
                        <th>Menge</th>
                        <th>Einheit</th>
                        <th>Einzelpreis</th>
                        <th>MwSt %</th>
                        <th>Gesamt netto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {zugferdImportResult.items.map((item: any, idx: number) => (
                        <tr key={idx}>
                          <td>{item.line_id || idx + 1}</td>
                          <td>{item.description || '–'}</td>
                          <td>{item.quantity}</td>
                          <td>{item.unit || '–'}</td>
                          <td>{item.unit_price ? `${item.unit_price} ${zugferdImportResult.currency}` : '–'}</td>
                          <td>{item.vat_rate || '–'}</td>
                          <td>{item.line_total_net ? `${item.line_total_net} ${zugferdImportResult.currency}` : '–'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={() => setZugferdImportResult(null)} className="btn-primary">Schließen</button>
            </div>
          </div>
        </div>
      )}

      {correctionFor && (
        <InvoiceCorrectionModal invoice={correctionFor} onClose={() => setCorrectionFor(null)} onCreated={handleCorrectionCreated} />
      )}

      {correctionDone && (
        <div className="modal-overlay" onClick={() => setCorrectionDone(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Rechnungskorrektur erstellt</h2>
            <p>
              Beleg <strong>{correctionDone.invoice_number}</strong> über{' '}
              {Number(correctionDone.gross_amount).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })} wurde erstellt.
            </p>
            <div className="form-actions">
              <button type="button" className="btn-secondary" onClick={() => setCorrectionDone(null)}>Schließen</button>
              <button type="button" className="btn-secondary" onClick={() => { handleSendEmail(correctionDone); setCorrectionDone(null) }}>Per E-Mail senden</button>
              <button type="button" className="btn-primary" onClick={() => { handlePreviewPdf(correctionDone.id, correctionDone.invoice_number); setCorrectionDone(null) }}>PDF ansehen</button>
            </div>
          </div>
        </div>
      )}

      {cancelModal && (
        <div className="modal-overlay" onClick={() => setCancelModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Rechnung stornieren</h2>
            <p>
              Rechnung <strong>{cancelModal.inv.invoice_number}</strong> wirklich stornieren?
            </p>
            <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', marginTop: '0.5rem' }}>
              Es wird eine Stornorechnung (STO-...) mit negativen Beträgen erstellt. Die Originalrechnung wird als "Storniert" markiert. Dieser Vorgang ist GoBD-konform und kann nicht rückgängig gemacht werden.
            </p>
            <div className="form-group" style={{ marginTop: '1rem' }}>
              <label htmlFor="cancel-reason">Stornierungsgrund (optional)</label>
              <textarea
                id="cancel-reason"
                value={cancelModal.reason}
                onChange={(e) => setCancelModal({ ...cancelModal, reason: e.target.value })}
                placeholder="z.B. Falsche Positionen, Kunde hat widerrufen"
                rows={3}
                style={{ width: '100%' }}
              />
            </div>
            {cancelError && <p className="error" style={{ marginTop: '0.75rem' }}>{cancelError}</p>}
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={() => setCancelModal(null)} className="btn-secondary">
                Abbrechen
              </button>
              <button
                type="button"
                onClick={handleCancelConfirm}
                disabled={cancelSubmitting}
                className="btn-primary"
                style={{ background: 'var(--color-error)' }}
              >
                {cancelSubmitting ? 'Wird storniert...' : 'Jetzt stornieren'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
