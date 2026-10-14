import { useEffect, useRef, useState } from 'react'
import { accountingApi, customersApi, incomingInvoicesApi, invoicesApi } from '../api/client'
import DatevExport from '../components/DatevExport'
import ArchivePanel from '../components/ArchivePanel'

type Preset = 'current_month' | 'last_month' | 'current_quarter' | 'last_quarter' | 'current_year' | 'last_year' | 'custom'
type AccountTab = 'b2c' | 'b2b' | 'incoming'

const PRESET_LABELS: Record<Preset, string> = {
  current_month: 'Laufender Monat',
  last_month: 'Letzter Monat',
  current_quarter: 'Laufendes Quartal',
  last_quarter: 'Letztes Quartal',
  current_year: 'Laufendes Jahr',
  last_year: 'Letztes Jahr',
  custom: 'Benutzerdefiniert',
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Entwurf',
  issued: 'Ausgestellt',
  paid: 'Bezahlt',
  partially_paid: 'Teilbezahlt',
  cancelled: 'Storniert',
  pending: 'Offen',
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'var(--color-text-muted)',
  issued: 'var(--color-warning, #d97706)',
  paid: 'var(--color-success, #16a34a)',
  partially_paid: 'var(--color-warning, #d97706)',
  cancelled: 'var(--color-error, #dc2626)',
  pending: 'var(--color-warning, #d97706)',
}

function getPresetDates(preset: Preset): { from: string; to: string } {
  const today = new Date()
  const y = today.getFullYear()
  const m = today.getMonth()
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  const lastDay = (year: number, month: number) => new Date(year, month + 1, 0)

  switch (preset) {
    case 'current_month':
      return { from: fmt(new Date(y, m, 1)), to: fmt(lastDay(y, m)) }
    case 'last_month': {
      const lm = m === 0 ? 11 : m - 1
      const ly = m === 0 ? y - 1 : y
      return { from: fmt(new Date(ly, lm, 1)), to: fmt(lastDay(ly, lm)) }
    }
    case 'current_quarter': {
      const q = Math.floor(m / 3)
      return { from: fmt(new Date(y, q * 3, 1)), to: fmt(lastDay(y, q * 3 + 2)) }
    }
    case 'last_quarter': {
      const q = Math.floor(m / 3)
      const lq = q === 0 ? 3 : q - 1
      const lqy = q === 0 ? y - 1 : y
      return { from: fmt(new Date(lqy, lq * 3, 1)), to: fmt(lastDay(lqy, lq * 3 + 2)) }
    }
    case 'current_year':
      return { from: fmt(new Date(y, 0, 1)), to: fmt(new Date(y, 11, 31)) }
    case 'last_year':
      return { from: fmt(new Date(y - 1, 0, 1)), to: fmt(new Date(y - 1, 11, 31)) }
    default:
      return { from: fmt(new Date(y, m, 1)), to: fmt(lastDay(y, m)) }
  }
}

const emptyIncomingForm = {
  supplier_name: '', invoice_number: '', invoice_date: new Date().toISOString().slice(0, 10),
  due_date: '', net_amount: '', vat_rate: '19', category: '', notes: '', is_credit_note: false,
}

export default function Accounting() {
  const [preset, setPreset] = useState<Preset>('current_month')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')

  const [activeTab, setActiveTab] = useState<AccountTab>('b2c')
  const [invoices, setInvoices] = useState<any[]>([])
  const [customers, setCustomers] = useState<any[]>([])
  const [incomingList, setIncomingList] = useState<any[]>([])
  const [listLoading, setListLoading] = useState(false)
  const [listError, setListError] = useState('')
  const [listLoaded, setListLoaded] = useState(false)

  const [previewingId, setPreviewingId] = useState<string | null>(null)
  const previewBlobUrl = useRef<string | null>(null)

  const [exportLoading, setExportLoading] = useState(false)
  const [exportError, setExportError] = useState('')

  // Eingangsrechnungen Form
  const [showIncomingForm, setShowIncomingForm] = useState(false)
  const [incomingForm, setIncomingForm] = useState(emptyIncomingForm)
  const [incomingFormError, setIncomingFormError] = useState('')
  const [incomingFormSaving, setIncomingFormSaving] = useState(false)
  const [editingIncomingId, setEditingIncomingId] = useState<string | null>(null)
  const [uploadingPdfFor, setUploadingPdfFor] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [pendingUploadId, setPendingUploadId] = useState<string | null>(null)
  const eInvoiceInputRef = useRef<HTMLInputElement>(null)
  const [eInvoiceImporting, setEInvoiceImporting] = useState(false)
  const [eInvoiceMessage, setEInvoiceMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    customersApi.list().then(setCustomers).catch(() => {})
  }, [])

  const getDates = () => {
    if (preset === 'custom') return { from: customFrom, to: customTo }
    return getPresetDates(preset)
  }

  const validateDates = () => {
    const { from, to } = getDates()
    if (!from || !to) return 'Bitte Zeitraum vollständig ausfüllen.'
    if (from > to) return 'Startdatum muss vor dem Enddatum liegen.'
    return ''
  }

  const handleLoadAll = async () => {
    const err = validateDates()
    if (err) { setListError(err); return }
    const { from, to } = getDates()
    setListError('')
    setListLoading(true)
    setListLoaded(false)
    try {
      const [inv, inc] = await Promise.all([
        invoicesApi.list({ date_from: from, date_to: to, limit: 500 }),
        incomingInvoicesApi.list({ date_from: from, date_to: to, limit: 500 }),
      ])
      setInvoices(inv)
      setIncomingList(inc)
      setListLoaded(true)
    } catch (e) {
      setListError(e instanceof Error ? e.message : 'Laden fehlgeschlagen')
    } finally {
      setListLoading(false)
    }
  }

  const handlePreview = async (id: string, type: 'outgoing' | 'incoming') => {
    setPreviewingId(id)
    try {
      if (previewBlobUrl.current) URL.revokeObjectURL(previewBlobUrl.current)
      const blob = type === 'outgoing'
        ? await invoicesApi.downloadPdf(id)
        : await incomingInvoicesApi.downloadPdf(id)
      const url = URL.createObjectURL(blob)
      previewBlobUrl.current = url
      window.open(url, '_blank')
    } catch {
      alert('PDF nicht verfügbar')
    } finally {
      setPreviewingId(null)
    }
  }

  const handleExport = async () => {
    const err = validateDates()
    if (err) { setExportError(err); return }
    const { from, to } = getDates()
    setExportError('')
    setExportLoading(true)
    try {
      const blob = await accountingApi.exportZip(from, to)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Buchhaltung_${from.replace(/-/g, '')}_${to.replace(/-/g, '')}.zip`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setExportError(e instanceof Error ? e.message : 'Export fehlgeschlagen')
    } finally {
      setExportLoading(false)
    }
  }

  const handleSaveIncoming = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!incomingForm.supplier_name || !incomingForm.invoice_number || !incomingForm.net_amount) {
      setIncomingFormError('Lieferant, Rechnungsnummer und Nettobetrag sind Pflichtfelder.')
      return
    }
    setIncomingFormError('')
    setIncomingFormSaving(true)
    try {
      const payload = {
        supplier_name: incomingForm.supplier_name,
        invoice_number: incomingForm.invoice_number,
        invoice_date: incomingForm.invoice_date,
        due_date: incomingForm.due_date || undefined,
        net_amount: parseFloat(incomingForm.net_amount),
        vat_rate: parseFloat(incomingForm.vat_rate) || 19,
        category: incomingForm.category || undefined,
        notes: incomingForm.notes || undefined,
        is_credit_note: incomingForm.is_credit_note,
      }
      if (editingIncomingId) {
        const updated = await incomingInvoicesApi.update(editingIncomingId, payload)
        setIncomingList((prev) => prev.map((i) => i.id === editingIncomingId ? updated : i))
      } else {
        const created = await incomingInvoicesApi.create(payload)
        setIncomingList((prev) => [created, ...prev])
      }
      setShowIncomingForm(false)
      setEditingIncomingId(null)
      setIncomingForm(emptyIncomingForm)
    } catch (e) {
      setIncomingFormError(e instanceof Error ? e.message : 'Fehler beim Speichern')
    } finally {
      setIncomingFormSaving(false)
    }
  }

  const handleEditIncoming = (inv: any) => {
    setIncomingForm({
      supplier_name: inv.supplier_name,
      invoice_number: inv.invoice_number,
      invoice_date: inv.invoice_date,
      due_date: inv.due_date || '',
      net_amount: String(inv.net_amount),
      vat_rate: String(inv.vat_rate),
      category: inv.category || '',
      notes: inv.notes || '',
      is_credit_note: !!inv.is_credit_note,
    })
    setEditingIncomingId(inv.id)
    setShowIncomingForm(true)
  }

  const handleDeleteIncoming = async (id: string) => {
    if (!confirm('Eingangsrechnung wirklich löschen?')) return
    try {
      await incomingInvoicesApi.delete(id)
      setIncomingList((prev) => prev.filter((i) => i.id !== id))
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Fehler')
    }
  }

  const handleMarkPaid = async (id: string) => {
    try {
      const updated = await incomingInvoicesApi.update(id, { status: 'paid' })
      setIncomingList((prev) => prev.map((i) => i.id === id ? updated : i))
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Fehler')
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !pendingUploadId) return
    setUploadingPdfFor(pendingUploadId)
    try {
      const updated = await incomingInvoicesApi.uploadPdf(pendingUploadId, file)
      setIncomingList((prev) => prev.map((i) => i.id === pendingUploadId ? updated : i))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Upload fehlgeschlagen')
    } finally {
      setUploadingPdfFor(null)
      setPendingUploadId(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleEInvoiceImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setEInvoiceImporting(true)
    setEInvoiceMessage(null)
    try {
      const created = await incomingInvoicesApi.importEInvoice(file)
      setIncomingList((prev) => [created, ...prev])
      setEInvoiceMessage({
        type: 'success',
        text: `Importiert: ${created.invoice_number} von ${created.supplier_name} (${formatDate(created.invoice_date)}, ${formatEuro(created.gross_amount)})`,
      })
    } catch (err) {
      setEInvoiceMessage({ type: 'error', text: err instanceof Error ? err.message : 'Import fehlgeschlagen' })
    } finally {
      setEInvoiceImporting(false)
      if (eInvoiceInputRef.current) eInvoiceInputRef.current.value = ''
    }
  }

  const handleDownloadOriginal = async (inv: any) => {
    try {
      const blob = await incomingInvoicesApi.downloadOriginal(inv.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = inv.original_filename || `E-Rechnung_${inv.invoice_number}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Download fehlgeschlagen')
    }
  }

  const triggerUpload = (id: string) => {
    setPendingUploadId(id)
    fileInputRef.current?.click()
  }

  const { from: previewFrom, to: previewTo } = getDates()

  const formatDate = (d: string) => {
    if (!d) return '–'
    try { return new Date(d).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) }
    catch { return d }
  }

  const getCustomerName = (customerId: string) => {
    const c = customers.find((x) => x.id === customerId)
    if (!c) return '–'
    return c.company_name || `${c.first_name || ''} ${c.last_name || ''}`.trim() || '–'
  }

  const formatEuro = (val: number | string) =>
    Number(val).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })

  const b2cInvoices = invoices.filter((inv) => {
    const c = customers.find((x) => x.id === inv.customer_id)
    return c?.customer_type === 'B2C'
  })
  const b2bInvoices = invoices.filter((inv) => {
    const c = customers.find((x) => x.id === inv.customer_id)
    return c?.customer_type === 'B2B'
  })

  const isCustomValid = preset !== 'custom' || (customFrom !== '' && customTo !== '')

  const tabCounts = listLoaded
    ? { b2c: b2cInvoices.length, b2b: b2bInvoices.length, incoming: incomingList.length }
    : { b2c: 0, b2b: 0, incoming: 0 }

  return (
    <div className="page">
      <h1>Steuerberater-Export</h1>
      <p className="muted">
        GoBD-konformes Exportpaket – nach Konten getrennt: Privatkunden (B2C), Händler (B2B) und Eingangsrechnungen.
      </p>

      {/* Zeitraum */}
      <div className="card form-card" style={{ maxWidth: 620 }}>
        <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1rem' }}>Zeitraum auswählen</h3>

        <div className="form-group">
          <label>Schnellauswahl</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {(Object.keys(PRESET_LABELS) as Preset[]).filter((p) => p !== 'custom').map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => { setPreset(p); setListLoaded(false) }}
                className={preset === p ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
              >
                {PRESET_LABELS[p]}
              </button>
            ))}
          </div>
        </div>

        <div className="form-row" style={{ display: 'flex', gap: '1rem', marginTop: '0.75rem' }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label htmlFor="date-from">Von</label>
            <input
              id="date-from"
              type="date"
              value={preset === 'custom' ? customFrom : previewFrom}
              onChange={(e) => { setPreset('custom'); setCustomFrom(e.target.value); setListLoaded(false) }}
            />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label htmlFor="date-to">Bis</label>
            <input
              id="date-to"
              type="date"
              value={preset === 'custom' ? customTo : previewTo}
              onChange={(e) => { setPreset('custom'); setCustomTo(e.target.value); setListLoaded(false) }}
            />
          </div>
        </div>

        {listError && <p className="error" style={{ marginTop: '0.5rem' }}>{listError}</p>}

        <div style={{ marginTop: '1rem' }}>
          <button
            type="button"
            onClick={handleLoadAll}
            disabled={listLoading || !isCustomValid}
            className="btn-secondary"
          >
            {listLoading ? 'Wird geladen…' : 'Rechnungen anzeigen'}
          </button>
        </div>
      </div>

      {/* Konto-Tabs + Listen */}
      {listLoaded && (
        <div style={{ marginTop: '1.5rem' }}>
          {/* Tab-Navigation */}
          <div style={{ display: 'flex', gap: 0, borderBottom: '2px solid var(--color-border)', marginBottom: '1rem' }}>
            {([
              { key: 'b2c', label: 'Privatkunden (B2C)', count: tabCounts.b2c },
              { key: 'b2b', label: 'Händler (B2B)', count: tabCounts.b2b },
              { key: 'incoming', label: 'Eingangsrechnungen', count: tabCounts.incoming },
            ] as { key: AccountTab; label: string; count: number }[]).map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                style={{
                  padding: '0.6rem 1.2rem',
                  border: 'none',
                  borderBottom: activeTab === tab.key ? '2px solid var(--color-primary)' : '2px solid transparent',
                  background: 'none',
                  cursor: 'pointer',
                  fontWeight: activeTab === tab.key ? 600 : 400,
                  color: activeTab === tab.key ? 'var(--color-primary)' : 'var(--color-text)',
                  marginBottom: '-2px',
                  fontSize: '0.95rem',
                }}
              >
                {tab.label}
                <span style={{
                  marginLeft: '0.4rem',
                  background: 'var(--color-bg-secondary)',
                  borderRadius: 10,
                  padding: '0.1rem 0.45rem',
                  fontSize: '0.78rem',
                  fontWeight: 400,
                }}>
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          {/* Ausgangsrechnungen B2C */}
          {activeTab === 'b2c' && (
            <OutgoingInvoiceTable
              invoices={b2cInvoices}
              customers={customers}
              title={`Ausgangsrechnungen Privatkunden (B2C) – ${formatDate(previewFrom)} bis ${formatDate(previewTo)}`}
              getCustomerName={getCustomerName}
              formatDate={formatDate}
              formatEuro={formatEuro}
              previewingId={previewingId}
              onPreview={(id) => handlePreview(id, 'outgoing')}
            />
          )}

          {/* Ausgangsrechnungen B2B */}
          {activeTab === 'b2b' && (
            <OutgoingInvoiceTable
              invoices={b2bInvoices}
              customers={customers}
              title={`Ausgangsrechnungen Händler (B2B) – ${formatDate(previewFrom)} bis ${formatDate(previewTo)}`}
              getCustomerName={getCustomerName}
              formatDate={formatDate}
              formatEuro={formatEuro}
              previewingId={previewingId}
              onPreview={(id) => handlePreview(id, 'outgoing')}
            />
          )}

          {/* Eingangsrechnungen */}
          {activeTab === 'incoming' && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0, fontSize: '1rem' }}>
                  Eingangsrechnungen – {formatDate(previewFrom)} bis {formatDate(previewTo)}
                </h3>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={eInvoiceImporting}
                    onClick={() => eInvoiceInputRef.current?.click()}
                    title="ZUGFeRD-PDF oder XRechnung-XML"
                  >
                    {eInvoiceImporting ? 'Importiere…' : '↑ E-Rechnung importieren'}
                  </button>
                  <button
                    type="button"
                    className="btn-primary btn-sm"
                    onClick={() => {
                      setEditingIncomingId(null)
                      setIncomingForm(emptyIncomingForm)
                      setIncomingFormError('')
                      setShowIncomingForm(true)
                    }}
                  >
                    + Neue Eingangsrechnung
                  </button>
                </div>
              </div>
              <input ref={eInvoiceInputRef} type="file" accept=".pdf,.xml,application/pdf,application/xml,text/xml" style={{ display: 'none' }} onChange={handleEInvoiceImport} />
              {eInvoiceMessage && (
                <p className={eInvoiceMessage.type === 'error' ? 'error' : 'success'} style={{ marginBottom: '1rem', color: eInvoiceMessage.type === 'success' ? 'var(--color-success, #16a34a)' : undefined }}>
                  {eInvoiceMessage.text}
                </p>
              )}

              {showIncomingForm && (
                <form
                  onSubmit={handleSaveIncoming}
                  style={{ background: 'var(--color-bg-secondary)', padding: '1rem', borderRadius: 8, marginBottom: '1rem' }}
                >
                  <h4 style={{ margin: '0 0 0.75rem' }}>
                    {editingIncomingId ? 'Eingangsrechnung bearbeiten' : 'Neue Eingangsrechnung'}
                  </h4>
                  <div className="form-row" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <div className="form-group" style={{ flex: '1 1 200px' }}>
                      <label>Lieferant *</label>
                      <input value={incomingForm.supplier_name} onChange={(e) => setIncomingForm({ ...incomingForm, supplier_name: e.target.value })} placeholder="Firma / Name" required />
                    </div>
                    <div className="form-group" style={{ flex: '1 1 150px' }}>
                      <label>Rechnungsnummer *</label>
                      <input value={incomingForm.invoice_number} onChange={(e) => setIncomingForm({ ...incomingForm, invoice_number: e.target.value })} placeholder="Externe Re-Nr." required />
                    </div>
                    <div className="form-group" style={{ flex: '1 1 140px' }}>
                      <label>Datum *</label>
                      <input type="date" value={incomingForm.invoice_date} onChange={(e) => setIncomingForm({ ...incomingForm, invoice_date: e.target.value })} required />
                    </div>
                    <div className="form-group" style={{ flex: '1 1 140px' }}>
                      <label>Fällig am</label>
                      <input type="date" value={incomingForm.due_date} onChange={(e) => setIncomingForm({ ...incomingForm, due_date: e.target.value })} />
                    </div>
                  </div>
                  <div className="form-row" style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <div className="form-group" style={{ flex: '1 1 140px' }}>
                      <label>Netto (€) *</label>
                      <input type="number" step="0.01" min="0" value={incomingForm.net_amount} onChange={(e) => setIncomingForm({ ...incomingForm, net_amount: e.target.value })} required />
                    </div>
                    <div className="form-group" style={{ flex: '0 1 100px' }}>
                      <label>MwSt %</label>
                      <input type="number" step="0.01" min="0" max="100" value={incomingForm.vat_rate} onChange={(e) => setIncomingForm({ ...incomingForm, vat_rate: e.target.value })} />
                    </div>
                    <div className="form-group" style={{ flex: '1 1 160px' }}>
                      <label>Kategorie</label>
                      <input value={incomingForm.category} onChange={(e) => setIncomingForm({ ...incomingForm, category: e.target.value })} placeholder="z.B. Ersatzteile, Miete" list="category-suggestions" />
                      <datalist id="category-suggestions">
                        {['Ersatzteile', 'Werkzeug', 'Miete', 'Strom', 'Wasser', 'Versicherung', 'Dienstleistung', 'Büromaterial', 'Sonstiges'].map((c) => (
                          <option key={c} value={c} />
                        ))}
                      </datalist>
                    </div>
                    <div className="form-group" style={{ flex: '2 1 200px' }}>
                      <label>Notiz</label>
                      <input value={incomingForm.notes} onChange={(e) => setIncomingForm({ ...incomingForm, notes: e.target.value })} placeholder="Optional" />
                    </div>
                    <div className="form-group" style={{ flex: '1 1 200px', display: 'flex', alignItems: 'flex-end' }}>
                      <label style={{ fontWeight: 400 }}>
                        <input type="checkbox" checked={incomingForm.is_credit_note} onChange={(e) => setIncomingForm({ ...incomingForm, is_credit_note: e.target.checked })} />{' '}
                        Gutschrift des Lieferanten
                      </label>
                    </div>
                  </div>
                  {incomingFormError && <p className="error">{incomingFormError}</p>}
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                    <button type="submit" disabled={incomingFormSaving} className="btn-primary btn-sm">
                      {incomingFormSaving ? 'Speichern…' : editingIncomingId ? 'Speichern' : 'Hinzufügen'}
                    </button>
                    <button type="button" className="btn-secondary btn-sm" onClick={() => { setShowIncomingForm(false); setEditingIncomingId(null) }}>
                      Abbrechen
                    </button>
                  </div>
                </form>
              )}

              <input ref={fileInputRef} type="file" accept=".pdf,.jpg,.jpeg,.png" style={{ display: 'none' }} onChange={handleFileUpload} />

              {incomingList.length === 0 ? (
                <p className="muted">Keine Eingangsrechnungen in diesem Zeitraum.</p>
              ) : (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Re-Nr. (Lieferant)</th>
                      <th>Lieferant</th>
                      <th>Kategorie</th>
                      <th>Datum</th>
                      <th>Fällig</th>
                      <th style={{ textAlign: 'right' }}>Brutto</th>
                      <th>Status</th>
                      <th>PDF</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {incomingList.map((inv) => (
                      <tr key={inv.id}>
                        <td>
                          <code>{inv.invoice_number}</code>
                          {inv.einvoice_format && (
                            <span title="Importierte E-Rechnung" style={{ marginLeft: '0.4rem', fontSize: '0.72rem', padding: '0.05rem 0.35rem', borderRadius: '4px', border: '1px solid currentColor', color: 'var(--color-primary, #22d3ee)' }}>
                              {inv.einvoice_format === 'zugferd' ? 'ZUGFeRD' : 'XRechnung'}
                            </span>
                          )}
                          {inv.is_credit_note && (
                            <span style={{ marginLeft: '0.4rem', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Gutschrift</span>
                          )}
                        </td>
                        <td>{inv.supplier_name}</td>
                        <td style={{ color: 'var(--color-text-muted)', fontSize: '0.88rem' }}>{inv.category || '–'}</td>
                        <td>{formatDate(inv.invoice_date)}</td>
                        <td>{inv.due_date ? formatDate(inv.due_date) : '–'}</td>
                        <td style={{ textAlign: 'right' }}>{formatEuro(inv.gross_amount)}</td>
                        <td>
                          <span style={{ color: STATUS_COLORS[inv.status] ?? 'inherit', fontWeight: 500 }}>
                            {STATUS_LABELS[inv.status] ?? inv.status}
                          </span>
                        </td>
                        <td>
                          {inv.einvoice_format && !inv.pdf_path ? (
                            <button type="button" className="btn-secondary btn-sm" onClick={() => handleDownloadOriginal(inv)}>
                              ↓ XML
                            </button>
                          ) : inv.pdf_path ? (
                            <button
                              type="button"
                              className="btn-secondary btn-sm"
                              disabled={previewingId === inv.id}
                              onClick={() => handlePreview(inv.id, 'incoming')}
                            >
                              {previewingId === inv.id ? '…' : 'Vorschau'}
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="btn-secondary btn-sm"
                              disabled={uploadingPdfFor === inv.id}
                              onClick={() => triggerUpload(inv.id)}
                            >
                              {uploadingPdfFor === inv.id ? 'Lädt…' : '↑ PDF'}
                            </button>
                          )}
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '0.3rem' }}>
                            {inv.status === 'pending' && (
                              <button type="button" className="btn-secondary btn-sm" onClick={() => handleMarkPaid(inv.id)}>
                                Bezahlt
                              </button>
                            )}
                            {inv.einvoice_format ? (
                              <button type="button" className="btn-secondary btn-sm" onClick={() => handleDownloadOriginal(inv)} title="Unverändertes Original herunterladen (GoBD-Archiv)">
                                Original
                              </button>
                            ) : (
                              <>
                                <button type="button" className="btn-secondary btn-sm" onClick={() => handleEditIncoming(inv)}>
                                  ✎
                                </button>
                                <button type="button" className="btn-secondary btn-sm" style={{ color: 'var(--color-error, #dc2626)' }} onClick={() => handleDeleteIncoming(inv.id)}>
                                  ✕
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={5} style={{ fontWeight: 600, paddingTop: '0.75rem' }}>Gesamt</td>
                      <td style={{ textAlign: 'right', fontWeight: 600, paddingTop: '0.75rem' }}>
                        {formatEuro(incomingList.reduce((s, i) => s + Number(i.gross_amount), 0))}
                      </td>
                      <td colSpan={3}></td>
                    </tr>
                  </tfoot>
                </table>
              )}
            </div>
          )}
        </div>
      )}

      {/* ZIP-Export */}
      {listLoaded && (
        <div className="card form-card" style={{ maxWidth: 620, marginTop: '1.5rem' }}>
          <h3 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '1rem' }}>ZIP-Paket für Steuerberater</h3>
          <p className="muted" style={{ marginTop: 0, fontSize: '0.88rem' }}>
            Enthält alle drei Konten als getrennte Ordner und CSVs. Eingangsrechnungen ohne hochgeladenes PDF werden in der CSV erwähnt.
          </p>
          {exportError && <p className="error">{exportError}</p>}
          <button type="button" onClick={handleExport} disabled={exportLoading} className="btn-primary">
            {exportLoading ? 'Wird erstellt…' : 'ZIP-Paket herunterladen'}
          </button>
          <div style={{ marginTop: '1rem', fontSize: '0.82rem', color: 'var(--color-text-muted)' }}>
            <strong>ZIP-Inhalt:</strong>
            <ul style={{ margin: '0.4rem 0 0', paddingLeft: '1.2rem', lineHeight: 1.8 }}>
              <li><code>ausgangsrechnungen_privat/</code> – PDFs B2C (ZUGFeRD)</li>
              <li><code>ausgangsrechnungen_haendler/</code> – PDFs B2B (ZUGFeRD)</li>
              <li><code>eingangsrechnungen/</code> – Hochgeladene PDFs</li>
              <li><code>ausgangsrechnungen_privat.csv</code> / <code>_haendler.csv</code> / <code>eingangsrechnungen.csv</code></li>
              <li><code>ust_zusammenfassung.csv</code> – USt nach Monat, Typ und Steuersatz</li>
              <li><code>LIESMICH.txt</code> – Metadaten und Hinweise</li>
            </ul>
          </div>
        </div>
      )}

      {/* DATEV-Export */}
      <DatevExport getRange={getDates} />

      {/* Belegarchiv */}
      <ArchivePanel />
    </div>
  )
}

// Ausgelagerte Tabellen-Komponente für Ausgangsrechnungen
function OutgoingInvoiceTable({
  invoices, title, getCustomerName, formatDate, formatEuro, previewingId, onPreview,
}: {
  invoices: any[]
  customers: any[]
  title: string
  getCustomerName: (id: string) => string
  formatDate: (d: string) => string
  formatEuro: (v: number | string) => string
  previewingId: string | null
  onPreview: (id: string) => void
}) {
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem' }}>{title}</h3>
      </div>
      {invoices.length === 0 ? (
        <p className="muted">Keine Rechnungen in diesem Zeitraum.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Rechnungsnr.</th>
              <th>Datum</th>
              <th>Kunde</th>
              <th style={{ textAlign: 'right' }}>Brutto</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id}>
                <td><code>{inv.invoice_number}</code></td>
                <td>{formatDate(inv.invoice_date)}</td>
                <td>{getCustomerName(inv.customer_id)}</td>
                <td style={{ textAlign: 'right' }}>{formatEuro(inv.gross_amount)}</td>
                <td>
                  <span style={{ color: STATUS_COLORS[inv.status] ?? 'inherit', fontWeight: 500 }}>
                    {STATUS_LABELS[inv.status] ?? inv.status}
                  </span>
                </td>
                <td>
                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    disabled={previewingId === inv.id}
                    onClick={() => onPreview(inv.id)}
                  >
                    {previewingId === inv.id ? '…' : 'Vorschau'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3} style={{ fontWeight: 600, paddingTop: '0.75rem' }}>Gesamt</td>
              <td style={{ textAlign: 'right', fontWeight: 600, paddingTop: '0.75rem' }}>
                {formatEuro(invoices.reduce((s, i) => s + Number(i.gross_amount), 0))}
              </td>
              <td colSpan={2}></td>
            </tr>
          </tfoot>
        </table>
      )}
    </div>
  )
}
