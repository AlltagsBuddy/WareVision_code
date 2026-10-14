import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { articlesApi, articleCategoriesApi, suppliersApi, manufacturersApi, storageLocationsApi } from '../api/client'
import BarcodeScanner from '../components/BarcodeScanner'

export default function Articles() {
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
    barcode: '',
    compatible_model_ids: [] as string[],
  })
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
    setLoading(true)
    articlesApi
      .list({ search: barcodeFilter ? undefined : (search || undefined), barcode: barcodeFilter || undefined, category_id: categoryFilter || undefined, vehicle_model_id: modelFilter || undefined, limit: PAGE_SIZE, skip: 0 })
      .then((data) => {
        setArticles(data)
        setHasMore(data.length === PAGE_SIZE)
      })
      .finally(() => setLoading(false))
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
      barcode: '',
      compatible_model_ids: [],
    })
    setEditing(null)
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
          barcode: form.barcode || undefined,
          compatible_model_ids: form.compatible_model_ids,
        }
        await articlesApi.update(editing.id, updateData)
        const updated = await articlesApi.list({ search: search || undefined })
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
          barcode: form.barcode || undefined,
          compatible_model_ids: form.compatible_model_ids,
        }
        await articlesApi.create(createData)
        const updated = await articlesApi.list({ search: search || undefined })
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
    setBarcodeFilter(code.trim())
    setBarcodeInput(code.trim())  // gescannten Code sichtbar machen
    setSearch('')
  }, [])

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
        <button type="button" onClick={() => setScanModalOpen(true)} className="btn-secondary">
          Kamera scannen
        </button>
        <button type="button" onClick={openLocModal} className="btn-secondary">Lagerorte</button>
        <button type="button" onClick={openCatModal} className="btn-secondary">Kategorien</button>
        <button type="button" onClick={() => { resetForm(); setShowForm(true) }} className="btn-primary">+ Neuer Artikel</button>
      </div>
      <BarcodeScanner
        open={scanModalOpen}
        onScan={handleScanResult}
        onClose={() => setScanModalOpen(false)}
      />

      {/* Artikel-Formular */}
      {showForm && (
        <div className="modal-overlay" onClick={() => { setShowForm(false); resetForm() }}>
          <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
            <h2>{editing ? 'Artikel bearbeiten' : 'Neuer Artikel'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label>Artikelnummer *</label>
                  <input value={form.article_number} onChange={(e) => setForm({ ...form, article_number: e.target.value })} required disabled={!!editing} />
                </div>
                <div className="form-group">
                  <label>Barcode</label>
                  <input value={form.barcode} onChange={(e) => setForm({ ...form, barcode: e.target.value })} placeholder="EAN/GTIN" />
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
    </div>
  )
}
