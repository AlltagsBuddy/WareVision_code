import { useEffect, useState, useCallback, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { articlesApi, articleCategoriesApi, suppliersApi, manufacturersApi, storageLocationsApi, catalogApi, type CatalogItem, type LabelSuggestion } from '../api/client'
import BarcodeScanner from '../components/BarcodeScanner'
import CameraCapture, { cameraSupported } from '../components/CameraCapture'
import CatalogImport from '../components/CatalogImport'
import { useAuth } from '../hooks/useAuth'
import { hasRight } from '../utils/permissions'

export default function Articles() {
  const { user } = useAuth()
  const [articles, setArticles] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [suppliers, setSuppliers] = useState<any[]>([])
  const [manufacturers, setManufacturers] = useState<any[]>([])
  const [allModels, setAllModels] = useState<any[]>([])  // alle Fahrzeugmodelle flach
  const [storageLocations, setStorageLocations] = useState<any[]>([])
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const modelFilter = searchParams.get('modell') || ''
  const setModelFilter = (id: string) => {
    const next = new URLSearchParams(searchParams)
    if (id) next.set('modell', id)
    else next.delete('modell')
    setSearchParams(next, { replace: true })
  }
  const [barcodeInput, setBarcodeInput] = useState('')
  const [barcodeFilter, setBarcodeFilter] = useState('')
  const [scanModalOpen, setScanModalOpen] = useState(false)
  // Wohin der gescannte Code geht: Suche in der Liste oder Barcode-Feld im Formular
  const [scanTarget, setScanTarget] = useState<'filter' | 'form'>('filter')
  // Zuordnen eines unbekannten Barcodes zu einem vorhandenen Artikel
  const [assignSearch, setAssignSearch] = useState('')
  const [assignHits, setAssignHits] = useState<any[]>([])
  const [assignMsg, setAssignMsg] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const PAGE_SIZE = 50
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<any | null>(null)
  const [form, setForm] = useState({
    article_number: '',
    name: '',
    description: '',
    category_id: '',
    supplier_id: '',
    storage_location_id: '',
    purchase_price: 0,
    sales_price_b2c: 0,
    sales_price_b2b: 0,
    vat_rate: 19,
    minimum_stock: 0,
    target_stock: '' as string,
    supplier_article_number: '',
    part_manufacturer: '',
    oem_number: '',
    barcode: '',
    compatible_model_ids: [] as string[],
  })
  // Vorschläge aus Lieferanten-Artikeldaten bzw. Etikett-Foto (nur beim Anlegen)
  const [catalogHits, setCatalogHits] = useState<CatalogItem[]>([])
  const [prefillNote, setPrefillNote] = useState('')
  const [catalogQuery, setCatalogQuery] = useState('')
  const [catalogSearchHits, setCatalogSearchHits] = useState<CatalogItem[]>([])
  const [showCatalogImport, setShowCatalogImport] = useState(false)
  const [aiEnabled, setAiEnabled] = useState(false)
  const [labelCameraOpen, setLabelCameraOpen] = useState(false)
  const [labelBusy, setLabelBusy] = useState(false)
  const [labelError, setLabelError] = useState('')
  const labelFileRef = useRef<HTMLInputElement>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // Lagerorte-Verwaltung
  const [showLocModal, setShowLocModal] = useState(false)
  const [locForm, setLocForm] = useState({ name: '', description: '' })
  const [locEditing, setLocEditing] = useState<any | null>(null)
  const [locSubmitting, setLocSubmitting] = useState(false)
  const [locError, setLocError] = useState('')

  // Kategorien-Verwaltung
  const [showCatModal, setShowCatModal] = useState(false)
  const [catForm, setCatForm] = useState({ name: '', description: '' })
  const [catEditing, setCatEditing] = useState<any | null>(null)
  const [catSubmitting, setCatSubmitting] = useState(false)
  const [catError, setCatError] = useState('')

  const loadCategories = () => articleCategoriesApi.list().then(setCategories)
  const loadStorageLocations = () => storageLocationsApi.list().then(setStorageLocations)

  useEffect(() => {
    loadCategories()
    loadStorageLocations()
    catalogApi.labelStatus().then((r) => setAiEnabled(r.enabled)).catch(() => setAiEnabled(false))
    suppliersApi.list().then(setSuppliers)
    // Alle Hersteller laden und danach für jeden die Modelle
    manufacturersApi.list().then(async (manfs) => {
      setManufacturers(manfs)
      const modelArrays = await Promise.all(manfs.map((m: any) => manufacturersApi.getModels(m.id).catch(() => [])))
      const flat = modelArrays.flatMap((models: any[], i: number) =>
        models.map((mod: any) => ({ ...mod, manufacturer_name: manfs[i].name, manufacturer_id: manfs[i].id }))
      )
      setAllModels(flat)
    })
  }, [])

  useEffect(() => {
    // Ältere Antworten verwerfen (z. B. Scan direkt nach dem Öffnen der Seite)
    let stale = false
    setLoading(true)
    articlesApi
      .list({ search: barcodeFilter ? undefined : (search || undefined), barcode: barcodeFilter || undefined, category_id: categoryFilter || undefined, vehicle_model_id: modelFilter || undefined, limit: PAGE_SIZE, skip: 0 })
      .then((data) => {
        if (stale) return
        setArticles(data)
        setHasMore(data.length === PAGE_SIZE)
      })
      .finally(() => { if (!stale) setLoading(false) })
    return () => { stale = true }
  }, [search, barcodeFilter, categoryFilter, modelFilter])

  const handleLoadMore = async () => {
    setLoadingMore(true)
    try {
      const more = await articlesApi.list({ search: barcodeFilter ? undefined : (search || undefined), barcode: barcodeFilter || undefined, category_id: categoryFilter || undefined, vehicle_model_id: modelFilter || undefined, limit: PAGE_SIZE, skip: articles.length })
      setArticles((prev) => [...prev, ...more])
      setHasMore(more.length === PAGE_SIZE)
    } finally {
      setLoadingMore(false)
    }
  }

  const getCategoryName = (id: string | null) => {
    if (!id) return '–'
    return categories.find((c) => c.id === id)?.name || '–'
  }

  const toggleModel = (modelId: string) => {
    setForm((f) => ({
      ...f,
      compatible_model_ids: f.compatible_model_ids.includes(modelId)
        ? f.compatible_model_ids.filter((id) => id !== modelId)
        : [...f.compatible_model_ids, modelId],
    }))
  }

  const resetForm = () => {
    setForm({
      article_number: '',
      name: '',
      description: '',
      category_id: '',
      supplier_id: '',
      storage_location_id: '',
      purchase_price: 0,
      sales_price_b2c: 0,
      sales_price_b2b: 0,
      vat_rate: 19,
      minimum_stock: 0,
      target_stock: '',
      supplier_article_number: '',
      part_manufacturer: '',
      oem_number: '',
      barcode: '',
      compatible_model_ids: [],
    })
    setEditing(null)
    setCatalogHits([])
    setPrefillNote('')
    setCatalogQuery('')
    setCatalogSearchHits([])
    setLabelError('')
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.target_stock !== '' && (!/^\d+$/.test(form.target_stock) || parseInt(form.target_stock, 10) < form.minimum_stock)) {
      setError('Der Zielbestand muss eine ganze Zahl und mindestens so groß wie der Mindestbestand sein.')
      return
    }
    setSubmitting(true)
    try {
      if (editing) {
        const updateData = {
          name: form.name,
          description: form.description || undefined,
          category_id: form.category_id || undefined,
          supplier_id: form.supplier_id || undefined,
          storage_location_id: form.storage_location_id || undefined,
          purchase_price: form.purchase_price,
          sales_price_b2c: form.sales_price_b2c,
          sales_price_b2b: form.sales_price_b2b,
          vat_rate: form.vat_rate,
          minimum_stock: form.minimum_stock,
          target_stock: form.target_stock === '' ? null : parseInt(form.target_stock, 10),
          supplier_article_number: form.supplier_article_number.trim() || null,
          part_manufacturer: form.part_manufacturer.trim() || null,
          oem_number: form.oem_number.trim() || null,
          barcode: form.barcode || undefined,
          compatible_model_ids: form.compatible_model_ids,
        }
        await articlesApi.update(editing.id, updateData)
        const updated = await articlesApi.list({ search: barcodeFilter ? undefined : (search || undefined), barcode: barcodeFilter || undefined })
        setArticles(categoryFilter ? updated.filter((a: any) => a.category_id === categoryFilter) : updated)
      } else {
        const createData = {
          article_number: form.article_number,
          name: form.name,
          description: form.description || undefined,
          category_id: form.category_id || undefined,
          supplier_id: form.supplier_id || undefined,
          storage_location_id: form.storage_location_id || undefined,
          purchase_price: form.purchase_price,
          sales_price_b2c: form.sales_price_b2c,
          sales_price_b2b: form.sales_price_b2b,
          vat_rate: form.vat_rate,
          minimum_stock: form.minimum_stock,
          target_stock: form.target_stock === '' ? null : parseInt(form.target_stock, 10),
          supplier_article_number: form.supplier_article_number.trim() || null,
          part_manufacturer: form.part_manufacturer.trim() || null,
          oem_number: form.oem_number.trim() || null,
          barcode: form.barcode || undefined,
          compatible_model_ids: form.compatible_model_ids,
        }
        await articlesApi.create(createData)
        const updated = await articlesApi.list({ search: barcodeFilter ? undefined : (search || undefined), barcode: barcodeFilter || undefined })
        setArticles(categoryFilter ? updated.filter((a: any) => a.category_id === categoryFilter) : updated)
      }
      setShowForm(false)
      resetForm()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (a: any) => {
    if (!confirm(`Artikel "${a.name}" wirklich löschen?`)) return
    try {
      await articlesApi.delete(a.id)
      setArticles((prev) => prev.filter((x) => x.id !== a.id))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const handleScanResult = useCallback((code: string) => {
    const clean = code.replace(/\s+/g, '')
    if (scanTarget === 'form') {
      setForm((f) => ({ ...f, barcode: clean }))
      setScanModalOpen(false)
      lookupRef.current(clean)
      return
    }
    setBarcodeFilter(clean)
    setBarcodeInput(clean)  // gescannten Code sichtbar machen
    setSearch('')
    setAssignSearch('')
    setAssignHits([])
    setAssignMsg('')
  }, [scanTarget])

  // Unbekannter Barcode: passende Artikel zum Zuordnen suchen
  useEffect(() => {
    const q = assignSearch.trim()
    if (!barcodeFilter || q.length < 2) {
      setAssignHits([])
      return
    }
    const t = setTimeout(() => {
      articlesApi.list({ search: q, limit: 20 }).then(setAssignHits).catch(() => setAssignHits([]))
    }, 300)
    return () => clearTimeout(t)
  }, [assignSearch, barcodeFilter])

  const assignTo = async (a: any) => {
    setAssignMsg('')
    try {
      let updated
      try {
        updated = await articlesApi.assignBarcode(a.id, barcodeFilter)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Fehler'
        if (!/Ersetzen\?/.test(msg)) throw err
        if (!confirm(`${msg}\n\nOK = neuen Barcode ${barcodeFilter} speichern.`)) return
        updated = await articlesApi.assignBarcode(a.id, barcodeFilter, true)
      }
      setArticles([updated])
      setAssignHits([])
      setAssignSearch('')
    } catch (err) {
      setAssignMsg(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const newWithBarcode = () => {
    resetForm()
    setForm((f) => ({ ...f, barcode: barcodeFilter }))
    setShowForm(true)
    lookupRef.current(barcodeFilter)
  }

  /** Vorschlag übernehmen: nur leere Felder füllen – bereits Eingetragenes bleibt. */
  const applyCatalog = (c: CatalogItem) => {
    setForm((f) => ({
      ...f,
      barcode: f.barcode || c.barcode || '',
      article_number: f.article_number || c.supplier_article_number || '',
      name: f.name || c.name,
      description: f.description || c.description || '',
      part_manufacturer: f.part_manufacturer || c.manufacturer || '',
      oem_number: f.oem_number || c.manufacturer_part_number || '',
      supplier_article_number: f.supplier_article_number || c.supplier_article_number || '',
      supplier_id: f.supplier_id || c.supplier_id || '',
      purchase_price: f.purchase_price || c.purchase_price || 0,
      sales_price_b2c: f.sales_price_b2c || c.retail_price_net || 0,
      vat_rate: c.vat_rate != null && f.vat_rate === 19 ? c.vat_rate : f.vat_rate,
    }))
    const src = c.source === 'einvoice' ? `E-Rechnung ${c.source_ref || ''}`.trim() : `Artikeldatei ${c.source_ref || ''}`.trim()
    setPrefillNote(`Vorgeschlagen aus Lieferantendaten „${c.supplier_name}“ (${src}). Bitte alle Angaben prüfen, `
      + 'besonders Artikelnummer, Preise und MwSt.')
  }

  const applyLabel = (l: LabelSuggestion) => {
    setForm((f) => ({
      ...f,
      barcode: f.barcode || l.barcode || '',
      name: f.name || l.name || '',
      description: f.description || l.description || '',
      part_manufacturer: f.part_manufacturer || l.manufacturer || '',
      oem_number: f.oem_number || l.manufacturer_part_number || '',
    }))
  }

  /** Barcode im Formular → Lieferantendaten nachschlagen (nur beim Anlegen) */
  const lookupCatalog = async (code: string) => {
    const c = (code || '').replace(/\s+/g, '')
    if (!c || editing) return
    try {
      const hits = await catalogApi.lookup(c)
      setCatalogHits(hits)
      if (hits.length >= 1) applyCatalog(hits[0])
      else setPrefillNote('Zu diesem Barcode gibt es keine Lieferantendaten.'
        + (aiEnabled ? ' Tipp: „Etikett fotografieren“ füllt Bezeichnung und Hersteller vor.' : ''))
    } catch {
      setCatalogHits([])
    }
  }
  const lookupRef = useRef(lookupCatalog)
  lookupRef.current = lookupCatalog

  // Suche in den Lieferantendaten (für Artikel ohne Barcode)
  useEffect(() => {
    const q = catalogQuery.trim()
    if (q.length < 2) {
      setCatalogSearchHits([])
      return
    }
    const t = setTimeout(() => {
      catalogApi.search(q).then(setCatalogSearchHits).catch(() => setCatalogSearchHits([]))
    }, 300)
    return () => clearTimeout(t)
  }, [catalogQuery])

  /** Etikett-Foto an die KI schicken; Vorschläge füllen leere Felder */
  const recognizeLabel = async (file: File) => {
    setLabelCameraOpen(false)
    setLabelError('')
    setLabelBusy(true)
    try {
      const r = await catalogApi.recognizeLabel(file)
      if (r.catalog.length) {
        setCatalogHits(r.catalog)
        applyCatalog(r.catalog[0])
      }
      applyLabel(r.suggestion)
      if (!r.catalog.length) {
        setPrefillNote('Vorgeschlagen aus dem Etikett-Foto (KI). Bitte alle Angaben prüfen; Preise und Artikelnummer '
          + 'stehen meist nicht auf dem Etikett.')
      }
    } catch (err) {
      setLabelError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setLabelBusy(false)
      if (labelFileRef.current) labelFileRef.current.value = ''
    }
  }

  const openEdit = (a: any) => {
    setEditing(a)
    setForm({
      article_number: a.article_number,
      name: a.name,
      description: a.description || '',
      category_id: a.category_id || '',
      supplier_id: a.supplier_id || '',
      storage_location_id: a.storage_location_id || '',
      purchase_price: Number(a.purchase_price),
      sales_price_b2c: Number(a.sales_price_b2c),
      sales_price_b2b: Number(a.sales_price_b2b),
      vat_rate: Number(a.vat_rate),
      minimum_stock: a.minimum_stock,
      target_stock: a.target_stock != null ? String(a.target_stock) : '',
      supplier_article_number: a.supplier_article_number || '',
      part_manufacturer: a.part_manufacturer || '',
      oem_number: a.oem_number || '',
      barcode: a.barcode || '',
      compatible_model_ids: (a.compatible_model_ids || []).map((id: any) => String(id)),
    })
    setShowForm(true)
  }

  // Lagerorte-Verwaltung
  const openLocModal = () => {
    setLocForm({ name: '', description: '' })
    setLocEditing(null)
    setLocError('')
    setShowLocModal(true)
  }

  const openLocEdit = (loc: any) => {
    setLocEditing(loc)
    setLocForm({ name: loc.name, description: loc.description || '' })
    setLocError('')
  }

  const handleLocSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!locForm.name.trim()) return
    setLocSubmitting(true)
    setLocError('')
    try {
      if (locEditing) {
        await storageLocationsApi.update(locEditing.id, {
          name: locForm.name.trim(),
          description: locForm.description || undefined,
        })
      } else {
        await storageLocationsApi.create({
          name: locForm.name.trim(),
          description: locForm.description || undefined,
        })
      }
      await loadStorageLocations()
      setLocForm({ name: '', description: '' })
      setLocEditing(null)
    } catch (err) {
      setLocError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setLocSubmitting(false)
    }
  }

  const handleLocDelete = async (loc: any) => {
    if (!confirm(`Lagerort "${loc.name}" wirklich löschen?`)) return
    try {
      await storageLocationsApi.delete(loc.id)
      await loadStorageLocations()
      if (form.storage_location_id === loc.id) setForm((f) => ({ ...f, storage_location_id: '' }))
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  const getStorageLocationName = (id: string | null) => {
    if (!id) return '–'
    return storageLocations.find((l) => l.id === id)?.name || '–'
  }

  // Kategorien-Verwaltung
  const openCatModal = () => {
    setCatForm({ name: '', description: '' })
    setCatEditing(null)
    setCatError('')
    setShowCatModal(true)
  }

  const openCatEdit = (cat: any) => {
    setCatEditing(cat)
    setCatForm({ name: cat.name, description: cat.description || '' })
    setCatError('')
  }

  const handleCatSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!catForm.name.trim()) return
    setCatSubmitting(true)
    setCatError('')
    try {
      if (catEditing) {
        await articleCategoriesApi.update(catEditing.id, {
          name: catForm.name.trim(),
          description: catForm.description || undefined,
        })
      } else {
        await articleCategoriesApi.create({
          name: catForm.name.trim(),
          description: catForm.description || undefined,
        })
      }
      await loadCategories()
      setCatForm({ name: '', description: '' })
      setCatEditing(null)
    } catch (err) {
      setCatError(err instanceof Error ? err.message : 'Fehler')
    } finally {
      setCatSubmitting(false)
    }
  }

  const handleCatDelete = async (cat: any) => {
    if (!confirm(`Kategorie "${cat.name}" wirklich löschen?`)) return
    try {
      await articleCategoriesApi.delete(cat.id)
      await loadCategories()
      if (categoryFilter === cat.id) setCategoryFilter('')
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Fehler')
    }
  }

  return (
    <div className="page">
      <h1>Artikel</h1>
      <div className="toolbar">
        <input
          type="search"
          placeholder="Nr., Name, OEM, Hersteller..."
          aria-label="Artikel suchen"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setBarcodeFilter('') }}
        />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="select"
        >
          <option value="">Alle Kategorien</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <select
          value={modelFilter}
          onChange={(e) => setModelFilter(e.target.value)}
          className="select"
          aria-label="Passend für Fahrzeugmodell"
          style={{ maxWidth: 240 }}
        >
          <option value="">Alle Fahrzeugmodelle</option>
          {manufacturers
            .filter((m) => allModels.some((mod) => mod.manufacturer_id === m.id))
            .map((m) => (
              <optgroup key={m.id} label={m.name}>
                {allModels.filter((mod) => mod.manufacturer_id === m.id).map((mod) => (
                  <option key={mod.id} value={mod.id}>{m.name} {mod.name}{mod.variant ? ` ${mod.variant}` : ''}</option>
                ))}
              </optgroup>
            ))}
          {modelFilter && !allModels.some((mod) => mod.id === modelFilter) && (
            <option value={modelFilter}>Gewähltes Modell</option>
          )}
        </select>
        <input
          type="text"
          placeholder="Barcode (Enter)"
          value={barcodeInput}
          onChange={(e) => setBarcodeInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              const val = barcodeInput.trim()
              if (val) {
                setBarcodeFilter(val)
                setSearch('')
              }
            }
          }}
          style={{ maxWidth: 160 }}
        />
        <button type="button" onClick={() => { setScanTarget('filter'); setScanModalOpen(true) }} className="btn-secondary">
          Kamera scannen
        </button>
        {hasRight(user, 'lager_einkauf') && (
          <button type="button" onClick={() => setShowCatalogImport(true)} className="btn-secondary">Lieferantendaten</button>
        )}
        <button type="button" onClick={openLocModal} className="btn-secondary">Lagerorte</button>
        <button type="button" onClick={openCatModal} className="btn-secondary">Kategorien</button>
        <button type="button" onClick={() => { resetForm(); setShowForm(true) }} className="btn-primary">+ Neuer Artikel</button>
      </div>

      {/* Artikel-Formular */}
      {showForm && (
        <div className="modal-overlay" onClick={() => { setShowForm(false); resetForm() }}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? 'Artikel bearbeiten' : 'Neuer Artikel'}</h2>
            <form onSubmit={handleSubmit}>
              {!editing && (
                <div className="card" style={{ padding: '0.75rem', marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>
                    Schnell anlegen: Barcode scannen (Feld „Barcode“ → „Scannen“), in den Lieferantendaten suchen
                    {aiEnabled ? ' oder das Etikett fotografieren' : ''}. Die Felder werden vorbelegt – bitte prüfen.
                  </div>
                  <div className="toolbar" style={{ margin: 0 }}>
                    <input
                      type="search"
                      placeholder="Lieferantendaten durchsuchen (Bezeichnung, Bestellnr., OEM)…"
                      aria-label="Lieferantendaten durchsuchen"
                      value={catalogQuery}
                      onChange={(e) => setCatalogQuery(e.target.value)}
                    />
                    {aiEnabled && (
                      <>
                        <button type="button" className="btn-secondary" disabled={labelBusy}
                          onClick={() => (cameraSupported() ? setLabelCameraOpen(true) : labelFileRef.current?.click())}>
                          {labelBusy ? 'Etikett wird gelesen…' : 'Etikett fotografieren (KI)'}
                        </button>
                        <button type="button" className="btn-secondary" disabled={labelBusy} onClick={() => labelFileRef.current?.click()}>
                          Etikett-Bild wählen
                        </button>
                        <input ref={labelFileRef} type="file" accept="image/*" capture="environment" style={{ display: 'none' }}
                          aria-label="Etikett-Bild" onChange={(e) => { const f = e.target.files?.[0]; if (f) recognizeLabel(f) }} />
                      </>
                    )}
                  </div>
                  {catalogSearchHits.length > 0 && (
                    <ul style={{ listStyle: 'none', padding: 0, margin: '0.5rem 0 0', maxHeight: 180, overflowY: 'auto' }}>
                      {catalogSearchHits.map((c) => (
                        <li key={c.id} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.2rem 0' }}>
                          <span style={{ flex: 1, fontSize: '0.875rem' }}>
                            {c.name}
                            <span className="muted"> · {c.supplier_name}{c.supplier_article_number ? ` · ${c.supplier_article_number}` : ''}
                              {c.purchase_price != null ? ` · EK ${c.purchase_price.toFixed(2)} €` : ''}</span>
                          </span>
                          <button type="button" className="btn-secondary btn-sm"
                            onClick={() => { applyCatalog(c); setCatalogQuery(''); setCatalogSearchHits([]) }}>
                            Übernehmen
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  {catalogQuery.trim().length >= 2 && catalogSearchHits.length === 0 && (
                    <p className="muted" style={{ margin: '0.5rem 0 0', fontSize: '0.85rem' }}>Nichts gefunden.</p>
                  )}
                  {catalogHits.length > 1 && (
                    <div style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
                      Mehrere Lieferanten führen diesen Barcode:{' '}
                      {catalogHits.map((c) => (
                        <button key={c.id} type="button" className="btn-secondary btn-sm" style={{ marginRight: '0.3rem' }}
                          onClick={() => applyCatalog(c)}>
                          {c.supplier_name}{c.purchase_price != null ? ` (EK ${c.purchase_price.toFixed(2)} €)` : ''}
                        </button>
                      ))}
                    </div>
                  )}
                  {prefillNote && <p role="status" style={{ margin: '0.5rem 0 0', fontSize: '0.875rem', color: 'var(--color-warning, #d97706)' }}>{prefillNote}</p>}
                  {labelError && <p className="error" style={{ margin: '0.5rem 0 0' }}>{labelError}</p>}
                  {aiEnabled && (
                    <p className="muted" style={{ margin: '0.5rem 0 0', fontSize: '0.75rem' }}>
                      Beim Etikett-Foto wird das Bild zur Auswertung an den KI-Dienst (Anthropic) gesendet und nicht
                      gespeichert. Nur das Etikett fotografieren – keine Personen oder Kundenunterlagen.
                    </p>
                  )}
                </div>
              )}
              <div className="form-row">
                <div className="form-group">
                  <label>Artikelnummer *</label>
                  <input value={form.article_number} onChange={(e) => setForm({ ...form, article_number: e.target.value })} required disabled={!!editing} />
                </div>
                <div className="form-group">
                  <label>Barcode</label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      value={form.barcode}
                      onChange={(e) => setForm({ ...form, barcode: e.target.value })}
                      onBlur={(e) => { if (!catalogHits.length) lookupCatalog(e.target.value) }}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); lookupCatalog(form.barcode) } }}
                      placeholder="EAN/GTIN"
                      aria-label="Barcode"
                      style={{ flex: 1 }}
                    />
                    <button type="button" className="btn-secondary" onClick={() => { setScanTarget('form'); setScanModalOpen(true) }}>
                      Scannen
                    </button>
                  </div>
                </div>
              </div>
              <div className="form-group">
                <label>Bezeichnung *</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Kategorie</label>
                  <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
                    <option value="">– Keine Kategorie –</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Lieferant</label>
                  <select value={form.supplier_id} onChange={(e) => setForm({ ...form, supplier_id: e.target.value })}>
                    <option value="">– Kein Lieferant –</option>
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="art-part-maker">Hersteller des Teils (Marke)</label>
                <input
                  id="art-part-maker"
                  list="art-part-maker-list"
                  maxLength={150}
                  placeholder="z. B. NGK, Motul, Original-Teil"
                  value={form.part_manufacturer}
                  onChange={(e) => setForm({ ...form, part_manufacturer: e.target.value })}
                />
                <datalist id="art-part-maker-list">
                  {Array.from(new Set([
                    ...manufacturers.map((m) => m.name),
                    ...articles.map((a) => a.part_manufacturer).filter(Boolean),
                  ])).sort().map((n) => <option key={n} value={n} />)}
                </datalist>
              </div>
              <div className="form-group">
                <label htmlFor="art-oem">Herstellernummer / OEM-Nummer</label>
                <input id="art-oem" maxLength={100} value={form.oem_number}
                  onChange={(e) => setForm({ ...form, oem_number: e.target.value })} placeholder="Teilenummer des Herstellers" />
              </div>
              <div className="form-group">
                <label>Lagerort</label>
                <select value={form.storage_location_id} onChange={(e) => setForm({ ...form, storage_location_id: e.target.value })}>
                  <option value="">– Kein Lagerort –</option>
                  {storageLocations.map((l) => (
                    <option key={l.id} value={l.id}>{l.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Beschreibung</label>
                <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>EK (€)</label>
                  <input type="number" step="0.01" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: parseFloat(e.target.value) || 0 })} />
                </div>
                <div className="form-group">
                  <label>VK B2C (€)</label>
                  <input type="number" step="0.01" value={form.sales_price_b2c} onChange={(e) => setForm({ ...form, sales_price_b2c: parseFloat(e.target.value) || 0 })} />
                </div>
                <div className="form-group">
                  <label>VK B2B (€)</label>
                  <input type="number" step="0.01" value={form.sales_price_b2b} onChange={(e) => setForm({ ...form, sales_price_b2b: parseFloat(e.target.value) || 0 })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>MwSt %</label>
                  <input type="number" step="0.01" value={form.vat_rate} onChange={(e) => setForm({ ...form, vat_rate: parseFloat(e.target.value) || 19 })} />
                </div>
                <div className="form-group">
                  <label>Mindestbestand</label>
                  <input type="number" value={form.minimum_stock} onChange={(e) => setForm({ ...form, minimum_stock: parseInt(e.target.value, 10) || 0 })} min="0" />
                </div>
                <div className="form-group">
                  <label htmlFor="art-target">Zielbestand (Bestellvorschlag)</label>
                  <input id="art-target" type="number" min="0" placeholder="leer = Mindestbestand" value={form.target_stock} onChange={(e) => setForm({ ...form, target_stock: e.target.value })} />
                </div>
              </div>
              <div className="form-group">
                <label htmlFor="art-supplier-no">Artikelnummer beim Lieferanten</label>
                <input id="art-supplier-no" maxLength={100} value={form.supplier_article_number} onChange={(e) => setForm({ ...form, supplier_article_number: e.target.value })} placeholder="steht auf der Bestellung" />
              </div>
              {/* Kompatible Fahrzeugmodelle */}
              {allModels.length > 0 && (
                <div className="form-group">
                  <label>Kompatible Fahrzeugmodelle (optional)</label>
                  <div style={{
                    maxHeight: 180,
                    overflowY: 'auto',
                    border: '1px solid var(--color-border)',
                    borderRadius: 6,
                    padding: '0.5rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.25rem',
                  }}>
                    {manufacturers
                      .filter((m) => allModels.some((mod) => mod.manufacturer_id === m.id))
                      .map((m) => (
                        <div key={m.id}>
                          <div style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>{m.name}</div>
                          {allModels.filter((mod) => mod.manufacturer_id === m.id).map((mod) => (
                            <label key={mod.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.1rem 0.25rem', cursor: 'pointer', fontSize: '0.9rem' }}>
                              <input
                                type="checkbox"
                                checked={form.compatible_model_ids.includes(mod.id)}
                                onChange={() => toggleModel(mod.id)}
                              />
                              {mod.name}{mod.variant ? ` (${mod.variant})` : ''}
                            </label>
                          ))}
                        </div>
                      ))}
                  </div>
                  {form.compatible_model_ids.length > 0 && (
                    <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: '0.25rem' }}>
                      {form.compatible_model_ids.length} Modell{form.compatible_model_ids.length !== 1 ? 'e' : ''} ausgewählt
                    </p>
                  )}
                </div>
              )}
              {error && <p className="error">{error}</p>}
              <div className="form-actions">
                <button type="button" onClick={() => { setShowForm(false); resetForm() }} className="btn-secondary">Abbrechen</button>
                <button type="submit" disabled={submitting} className="btn-primary">{submitting ? 'Speichern...' : (editing ? 'Speichern' : 'Anlegen')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Lagerorte-Verwaltung */}
      {showLocModal && (
        <div className="modal-overlay" onClick={() => setShowLocModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Lagerorte verwalten</h2>
            <form onSubmit={handleLocSubmit} style={{ marginBottom: '1rem' }}>
              <div className="form-group">
                <label>{locEditing ? 'Lagerort bearbeiten' : 'Neuer Lagerort'}</label>
                <input
                  value={locForm.name}
                  onChange={(e) => setLocForm({ ...locForm, name: e.target.value })}
                  placeholder="Name *"
                  required
                />
              </div>
              <div className="form-group">
                <input
                  value={locForm.description}
                  onChange={(e) => setLocForm({ ...locForm, description: e.target.value })}
                  placeholder="Beschreibung (optional)"
                />
              </div>
              {locError && <p className="error">{locError}</p>}
              <div className="form-actions">
                {locEditing && (
                  <button type="button" onClick={() => { setLocEditing(null); setLocForm({ name: '', description: '' }) }} className="btn-secondary">Abbrechen</button>
                )}
                <button type="submit" disabled={locSubmitting} className="btn-primary">
                  {locSubmitting ? 'Speichern...' : (locEditing ? 'Speichern' : 'Hinzufügen')}
                </button>
              </div>
            </form>
            {storageLocations.length === 0 ? (
              <p>Noch keine Lagerorte vorhanden.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {storageLocations.map((l) => (
                  <li key={l.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span style={{ flex: 1 }}><strong>{l.name}</strong>{l.description && <span style={{ color: 'var(--color-text-muted)' }}> – {l.description}</span>}</span>
                    <button type="button" onClick={() => openLocEdit(l)} className="btn-secondary btn-sm">Bearbeiten</button>
                    <button type="button" onClick={() => handleLocDelete(l)} className="btn-secondary btn-sm">Löschen</button>
                  </li>
                ))}
              </ul>
            )}
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={() => setShowLocModal(false)} className="btn-secondary">Schließen</button>
            </div>
          </div>
        </div>
      )}

      {/* Kategorien-Verwaltung */}
      {showCatModal && (
        <div className="modal-overlay" onClick={() => setShowCatModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Kategorien verwalten</h2>
            <form onSubmit={handleCatSubmit} style={{ marginBottom: '1rem' }}>
              <div className="form-group">
                <label>{catEditing ? 'Kategorie bearbeiten' : 'Neue Kategorie'}</label>
                <input
                  value={catForm.name}
                  onChange={(e) => setCatForm({ ...catForm, name: e.target.value })}
                  placeholder="Name *"
                  required
                />
              </div>
              <div className="form-group">
                <input
                  value={catForm.description}
                  onChange={(e) => setCatForm({ ...catForm, description: e.target.value })}
                  placeholder="Beschreibung (optional)"
                />
              </div>
              {catError && <p className="error">{catError}</p>}
              <div className="form-actions">
                {catEditing && (
                  <button type="button" onClick={() => { setCatEditing(null); setCatForm({ name: '', description: '' }) }} className="btn-secondary">Abbrechen</button>
                )}
                <button type="submit" disabled={catSubmitting} className="btn-primary">
                  {catSubmitting ? 'Speichern...' : (catEditing ? 'Speichern' : 'Hinzufügen')}
                </button>
              </div>
            </form>
            {categories.length === 0 ? (
              <p>Noch keine Kategorien vorhanden.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {categories.map((c) => (
                  <li key={c.id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span style={{ flex: 1 }}><strong>{c.name}</strong>{c.description && <span style={{ color: 'var(--color-text-muted)' }}> – {c.description}</span>}</span>
                    <button type="button" onClick={() => openCatEdit(c)} className="btn-secondary btn-sm">Bearbeiten</button>
                    <button type="button" onClick={() => handleCatDelete(c)} className="btn-secondary btn-sm">Löschen</button>
                  </li>
                ))}
              </ul>
            )}
            <div className="form-actions" style={{ marginTop: '1rem' }}>
              <button type="button" onClick={() => setShowCatModal(false)} className="btn-secondary">Schließen</button>
            </div>
          </div>
        </div>
      )}

      {barcodeFilter && (
        <div className="card" role="status" style={{ padding: '0.75rem 1rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <span>Barcode <strong>{barcodeFilter}</strong>{!loading && articles.length === 0 && ' ist noch keinem Artikel zugeordnet.'}</span>
            <button type="button" className="btn-secondary btn-sm" onClick={() => { setBarcodeFilter(''); setBarcodeInput('') }}>
              Filter aufheben
            </button>
          </div>
          {!loading && articles.length === 0 && (
            <div style={{ marginTop: '0.75rem' }}>
              <div className="toolbar" style={{ margin: 0 }}>
                <input
                  type="search"
                  placeholder="Vorhandenen Artikel suchen (Nr., Name)…"
                  aria-label="Artikel zum Zuordnen suchen"
                  value={assignSearch}
                  onChange={(e) => setAssignSearch(e.target.value)}
                />
                <span className="muted">oder</span>
                <button type="button" className="btn-primary" style={{ width: 'auto' }} onClick={newWithBarcode}>+ Neuer Artikel mit diesem Barcode</button>
              </div>
              {assignHits.length > 0 && (
                <ul style={{ listStyle: 'none', padding: 0, margin: '0.5rem 0 0' }}>
                  {assignHits.map((a) => (
                    <li key={a.id} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', padding: '0.25rem 0' }}>
                      <span style={{ flex: 1 }}>
                        {a.article_number} – {a.name}
                        {a.barcode && <span className="muted"> (hat schon Barcode {a.barcode})</span>}
                      </span>
                      <button type="button" className="btn-secondary btn-sm" onClick={() => assignTo(a)}>Zuordnen</button>
                    </li>
                  ))}
                </ul>
              )}
              {assignSearch.trim().length >= 2 && assignHits.length === 0 && (
                <p className="muted" style={{ margin: '0.5rem 0 0' }}>Kein Artikel gefunden.</p>
              )}
              {assignMsg && <p className="error" style={{ margin: '0.5rem 0 0' }}>{assignMsg}</p>}
            </div>
          )}
        </div>
      )}

      {loading ? (
        <p>Laden...</p>
      ) : (
        <div className="table-wrapper">
        <table className="table">
          <thead>
            <tr>
              <th>Art.-Nr.</th>
              <th>Name</th>
              <th>Hersteller</th>
              <th>Kategorie</th>
              <th>Lagerort</th>
              <th>Barcode</th>
              <th>Bestand</th>
              <th>EK</th>
              <th>VK B2C</th>
              <th>Passend für Modelle</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {articles.map((a) => (
              <tr key={a.id} className={a.minimum_stock > 0 && a.stock_quantity < a.minimum_stock ? 'warning-row' : ''}>
                <td>{a.article_number}</td>
                <td>{a.name}</td>
                <td>{a.part_manufacturer || '–'}</td>
                <td>{getCategoryName(a.category_id)}</td>
                <td>{getStorageLocationName(a.storage_location_id)}</td>
                <td>{a.barcode || '–'}</td>
                <td>{a.stock_quantity}</td>
                <td>{Number(a.purchase_price).toFixed(2)} €</td>
                <td>{Number(a.sales_price_b2c).toFixed(2)} €</td>
                <td style={{ fontSize: '0.8rem' }}>
                  {(a.compatible_model_ids || []).length === 0
                    ? '–'
                    : allModels
                        .filter((m) => (a.compatible_model_ids || []).includes(m.id))
                        .map((m) => `${m.manufacturer_name} ${m.name}`)
                        .join(', ') || `${(a.compatible_model_ids || []).length} Modelle`
                  }
                </td>
                <td>
                  <button type="button" onClick={() => openEdit(a)} className="btn-secondary btn-sm">Bearbeiten</button>
                  <button type="button" onClick={() => handleDelete(a)} className="btn-secondary btn-sm">Löschen</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {hasMore && (
          <div style={{ textAlign: 'center', marginTop: '1rem' }}>
            <button type="button" onClick={handleLoadMore} disabled={loadingMore} className="btn-secondary">
              {loadingMore ? 'Laden...' : `Weitere laden (${articles.length} geladen)`}
            </button>
          </div>
        )}
        </div>
      )}
      {showCatalogImport && <CatalogImport onClose={() => setShowCatalogImport(false)} />}
      {labelCameraOpen && <CameraCapture onCapture={recognizeLabel} onClose={() => setLabelCameraOpen(false)} />}
      {/* Zuletzt, damit der Scanner auch über dem Artikel-Formular liegt */}
      <BarcodeScanner
        open={scanModalOpen}
        onScan={handleScanResult}
        onClose={() => setScanModalOpen(false)}
      />
    </div>
  )
}
