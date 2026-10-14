import { useEffect, useState } from 'react'
import { invoicesApi } from '../api/client'

/**
 * Dialog „Gutschrift / Rechnungskorrektur“ zu einer ausgestellten oder bezahlten Rechnung.
 * Einzelne Positionen (Teilmengen) und/oder ein Preisnachlass werden gutgeschrieben.
 * Es entsteht ein eigener Beleg (RK-…) mit negativen Beträgen; die Originalrechnung bleibt unverändert.
 */

interface Props {
  invoice: { id: string; invoice_number: string; status: string }
  onClose: () => void
  onCreated: (correction: any) => void
}

const CELL: React.CSSProperties = { width: '100%', minWidth: 0, boxSizing: 'border-box' }
const toNum = (v: string) => {
  const n = parseFloat(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : NaN
}
const round2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100
const formatEuro = (v: number | string) => Number(v).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })
const fmtQty = (v: string | number) => Number(v).toLocaleString('de-DE', { maximumFractionDigits: 2 })

export default function InvoiceCorrectionModal({ invoice, onClose, onCreated }: Props) {
  const [info, setInfo] = useState<any | null>(null)
  const [loadError, setLoadError] = useState('')
  const [qty, setQty] = useState<Record<string, string>>({})
  const [restock, setRestock] = useState<Record<string, boolean>>({})
  const [discount, setDiscount] = useState({ description: 'Preisnachlass', net_amount: '', vat_rate: '' })
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    invoicesApi
      .correctionInfo(invoice.id)
      .then((data) => {
        setInfo(data)
        setDiscount((d) => ({ ...d, vat_rate: data.vat_rates?.[0] ?? '19.00' }))
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : 'Daten konnten nicht geladen werden'))
  }, [invoice.id])

  // Vorschau der Gutschrift (gleiche Rundung wie im Backend: MwSt je Steuersatz)
  const preview = (() => {
    if (!info) return { net: 0, vat: 0, gross: 0 }
    const bases = new Map<number, number>()
    for (const it of info.items) {
      const q = toNum(qty[it.item_id] ?? '')
      if (!(q > 0)) continue
      const rate = Number(it.vat_rate)
      bases.set(rate, round2((bases.get(rate) || 0) + round2(q * Number(it.unit_price))))
    }
    const d = toNum(discount.net_amount)
    if (d > 0) {
      const rate = Number(discount.vat_rate)
      bases.set(rate, round2((bases.get(rate) || 0) + round2(d)))
    }
    let net = 0
    let vat = 0
    for (const [rate, basis] of bases) {
      net = round2(net + basis)
      vat = round2(vat + round2((basis * rate) / 100))
    }
    return { net, vat, gross: round2(net + vat) }
  })()

  const submit = async () => {
    setError('')
    if (!info) return
    if (reason.trim().length < 3) {
      setError('Bitte einen Grund angeben (erscheint auf dem Beleg).')
      return
    }
    const lines: { item_id: string; quantity: number; return_to_stock: boolean }[] = []
    for (const it of info.items) {
      const raw = (qty[it.item_id] ?? '').trim()
      if (!raw) continue
      const q = toNum(raw)
      if (!(q > 0) || round2(q) !== q) {
        setError(`„${it.description}“: Bitte eine Menge größer als 0 mit höchstens zwei Nachkommastellen eingeben.`)
        return
      }
      if (q > Number(it.remaining_quantity)) {
        setError(`„${it.description}“: Es können höchstens ${fmtQty(it.remaining_quantity)} gutgeschrieben werden.`)
        return
      }
      if (restock[it.item_id] && !Number.isInteger(q)) {
        setError(`„${it.description}“: Ins Lager können nur ganze Stück zurückgebucht werden.`)
        return
      }
      lines.push({ item_id: it.item_id, quantity: q, return_to_stock: !!restock[it.item_id] })
    }
    const free_lines: { description: string; net_amount: number; vat_rate: number }[] = []
    if (discount.net_amount.trim()) {
      const d = toNum(discount.net_amount)
      if (!(d > 0) || round2(d) !== d) {
        setError('Bitte beim Nachlass einen Nettobetrag größer als 0 (auf Cent genau) eingeben.')
        return
      }
      if (!discount.description.trim()) {
        setError('Bitte eine Bezeichnung für den Nachlass eingeben.')
        return
      }
      free_lines.push({ description: discount.description.trim(), net_amount: d, vat_rate: Number(discount.vat_rate) })
    }
    if (lines.length === 0 && free_lines.length === 0) {
      setError('Bitte mindestens eine Menge oder einen Nachlass eingeben.')
      return
    }
    if (preview.gross > Number(info.remaining_gross) + 0.001) {
      setError(`Die Gutschrift ist höher als der noch offene Rechnungsbetrag (${formatEuro(info.remaining_gross)}).`)
      return
    }
    setSaving(true)
    try {
      const created = await invoicesApi.createCorrection(invoice.id, { reason: reason.trim(), lines, free_lines })
      onCreated(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rechnungskorrektur fehlgeschlagen')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 980 }}>
        <h2>Gutschrift / Rechnungskorrektur zu {invoice.invoice_number}</h2>
        <p className="muted" style={{ fontSize: '0.9rem' }}>
          Es wird ein eigener Beleg (RK-…) mit negativen Beträgen erstellt, der auf diese Rechnung verweist. Die Originalrechnung
          bleibt unverändert (GoBD). Für eine vollständige Rückabwicklung ohne Vorkorrekturen kannst du auch „Stornieren“ verwenden.
        </p>
        {loadError && <p className="error">{loadError}</p>}
        {!info && !loadError && <p>Laden...</p>}
        {info && (
          <>
            {info.corrections.length > 0 && (
              <p style={{ fontSize: '0.9rem' }}>
                Bisherige Korrekturen: {info.corrections.map((c: any) => `${c.invoice_number} (${formatEuro(c.gross_amount)})`).join(', ')}
                {' · '}noch gutschreibbar: <strong>{formatEuro(info.remaining_gross)}</strong>
              </p>
            )}
            <div className="table-wrapper">
              <table className="table" style={{ tableLayout: 'fixed', width: '100%', minWidth: 700 }}>
                <thead>
                  <tr>
                    <th>Position</th>
                    <th style={{ width: 90, textAlign: 'right' }}>Berechnet</th>
                    <th style={{ width: 100, textAlign: 'right' }}>Einzelpreis</th>
                    <th style={{ width: 70, textAlign: 'right' }}>MwSt</th>
                    <th style={{ width: 95, textAlign: 'right' }}>Noch möglich</th>
                    <th style={{ width: 90 }}>Gutschrift</th>
                    <th style={{ width: 95 }}>Ins Lager</th>
                  </tr>
                </thead>
                <tbody>
                  {info.items.map((it: any, idx: number) => {
                    const remaining = Number(it.remaining_quantity)
                    return (
                      <tr key={it.item_id}>
                        <td>{it.description}</td>
                        <td style={{ textAlign: 'right' }}>{fmtQty(it.quantity)} {it.unit || ''}</td>
                        <td style={{ textAlign: 'right' }}>{formatEuro(it.unit_price)}</td>
                        <td style={{ textAlign: 'right' }}>{fmtQty(it.vat_rate)} %</td>
                        <td style={{ textAlign: 'right' }}>{fmtQty(remaining)}</td>
                        <td>
                          <input
                            style={CELL}
                            inputMode="decimal"
                            aria-label={`Gutschrift Menge Position ${idx + 1}`}
                            disabled={remaining <= 0}
                            value={qty[it.item_id] ?? ''}
                            onChange={(e) => setQty({ ...qty, [it.item_id]: e.target.value })}
                          />
                        </td>
                        <td>
                          {it.article_id ? (
                            <label style={{ fontWeight: 400 }}>
                              <input
                                type="checkbox"
                                aria-label={`Ins Lager Position ${idx + 1}`}
                                checked={!!restock[it.item_id]}
                                disabled={remaining <= 0}
                                onChange={(e) => setRestock({ ...restock, [it.item_id]: e.target.checked })}
                              />{' '}
                              zurück
                            </label>
                          ) : (
                            <span className="muted">–</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <div className="form-row" style={{ marginTop: '0.75rem' }}>
              <div className="form-group">
                <label htmlFor="rk-discount-desc">Zusätzlicher Nachlass / Kulanz (optional)</label>
                <input id="rk-discount-desc" value={discount.description} maxLength={500} onChange={(e) => setDiscount({ ...discount, description: e.target.value })} />
              </div>
              <div className="form-group" style={{ maxWidth: 150 }}>
                <label htmlFor="rk-discount-net">Betrag netto €</label>
                <input id="rk-discount-net" inputMode="decimal" value={discount.net_amount} onChange={(e) => setDiscount({ ...discount, net_amount: e.target.value })} />
              </div>
              <div className="form-group" style={{ maxWidth: 120 }}>
                <label htmlFor="rk-discount-vat">MwSt</label>
                <select id="rk-discount-vat" value={discount.vat_rate} onChange={(e) => setDiscount({ ...discount, vat_rate: e.target.value })}>
                  {info.vat_rates.map((r: string) => (
                    <option key={r} value={r}>{fmtQty(r)} %</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="rk-reason">Grund (Pflicht, erscheint auf dem Beleg) *</label>
              <input id="rk-reason" value={reason} maxLength={500} placeholder="z. B. Teil zurückgegeben, Kulanz, falsch berechnet" onChange={(e) => setReason(e.target.value)} />
            </div>

            <div style={{ textAlign: 'right', margin: '0.5rem 0' }}>
              <div>Gutschrift netto: {formatEuro(-preview.net)}</div>
              <div>MwSt: {formatEuro(-preview.vat)}</div>
              <div style={{ fontWeight: 700 }}>Gutschrift brutto: {formatEuro(-preview.gross)}</div>
            </div>
            {invoice.status === 'paid' && preview.gross > 0 && (
              <p className="muted" style={{ fontSize: '0.85rem' }}>
                Die Rechnung ist bereits bezahlt: Den Betrag bitte an den Kunden zurücküberweisen und den Beleg danach als „erstattet“ markieren.
              </p>
            )}
          </>
        )}
        {error && <p className="error">{error}</p>}
        <div className="form-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>Abbrechen</button>
          <button type="button" className="btn-primary" disabled={saving || !info} onClick={submit}>
            {saving ? 'Wird erstellt…' : 'Rechnungskorrektur erstellen'}
          </button>
        </div>
      </div>
    </div>
  )
}
