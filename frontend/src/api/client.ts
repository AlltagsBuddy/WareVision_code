const API_BASE = '/api/v1'

function getToken(): string | null {
  return localStorage.getItem('token')
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  // ngrok Free: Browser-Warnung überspringen, damit API-Anfragen durchgehen
  if (typeof window !== 'undefined' && window.location?.hostname?.includes('ngrok')) {
    headers['ngrok-skip-browser-warning'] = '1'
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const ct = res.headers.get('content-type') || ''
    const err = ct.includes('application/json')
      ? await res.json().catch(() => ({}))
      : {}
    let msg = err.detail || err.message || res.statusText || 'Fehler'
    // ngrok-Interstitial liefert HTML statt JSON
    if (ct.includes('text/html')) {
      msg = 'Bitte zuerst auf „Visit Site“ klicken (ngrok-Zwischenseite) und erneut versuchen.'
    }
    throw new Error(msg)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const dashboardApi = {
  getStats: () => api<Record<string, number>>('/dashboard/stats'),
}

export const authApi = {
  login: (email: string, password: string) =>
    api<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  register: (data: { email: string; first_name: string; last_name: string; password: string }) =>
    api<{ access_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  me: () => api<{ id: string; email: string; first_name: string; last_name: string; role_name: string }>('/auth/me'),
  exportMyData: () => api<Record<string, unknown>>('/auth/me/export'),
  changePassword: (current_password: string, new_password: string) =>
    api<{ message: string }>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    }),
}

export const settingsApi = {
  get: () => api<{
    company_name: string
    company_address: string
    company_vat_id: string
    company_email: string
    company_phone: string
    company_website: string
    company_bank_name: string
    company_bank_iban: string
    company_bank_bic: string
    company_bank_account_holder: string
    invoice_vat_exemption_note: string
    smtp_host: string
    smtp_port: string
    smtp_user: string
    smtp_password: string
    smtp_from: string
    smtp_tls: string
    termin_marktplatz_configured: boolean
    termin_marktplatz_webhook_base_url: string
    termin_marktplatz_cancel_callback_url: string
    resend_api_key: string
    resend_from_email: string
    resend_from_name: string
    resend_configured: boolean
    ai_help_api_key: string
    ai_help_model: string
    ai_help_configured: boolean
    company_logo_path: string
    company_logo_set: boolean
  }>('/settings'),
  update: (data: {
    company_name?: string
    company_address?: string
    company_vat_id?: string
    company_email?: string
    company_phone?: string
    company_website?: string
    company_bank_name?: string
    company_bank_iban?: string
    company_bank_bic?: string
    company_bank_account_holder?: string
    invoice_vat_exemption_note?: string
    smtp_host?: string
    smtp_port?: string
    smtp_user?: string
    smtp_password?: string
    smtp_from?: string
    smtp_tls?: string
    termin_marktplatz_api_key?: string
    termin_marktplatz_webhook_base_url?: string
    termin_marktplatz_cancel_callback_url?: string
    resend_api_key?: string
    resend_from_email?: string
    resend_from_name?: string
    ai_help_api_key?: string
    ai_help_model?: string
    ai_help_api_key_remove?: boolean
  }) =>
    api<{ company_name: string; company_address: string; company_vat_id: string }>('/settings', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  getTerminMarktplatzApiKey: () =>
    api<{ api_key: string | null }>('/settings/termin-marktplatz-api-key'),
  uploadLogo: async (file: File): Promise<void> => {
    const token = getToken()
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE}/settings/logo`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Logo-Upload fehlgeschlagen')
    }
  },
  sendTestEmail: (recipientEmail?: string) =>
    api<{ message: string; recipient: string }>('/settings/test-email', {
      method: 'POST',
      body: JSON.stringify(recipientEmail ? { recipient_email: recipientEmail } : {}),
    }),
}

export const auditApi = {
  list: (params?: { entity_type?: string; entity_id?: string; action?: string; skip?: number; limit?: number }) => {
    const p = new URLSearchParams()
    if (params?.entity_type) p.set('entity_type', params.entity_type)
    if (params?.entity_id) p.set('entity_id', params.entity_id)
    if (params?.action) p.set('action', params.action)
    if (params?.skip != null) p.set('skip', String(params.skip))
    if (params?.limit != null) p.set('limit', String(params.limit))
    return api<any[]>(`/audit-logs?${p}`)
  },
}

export const usersApi = {
  list: () => api<any[]>('/users'),
  roles: () => api<any[]>('/users/roles'),
  create: (data: Record<string, unknown>) =>
    api<any>('/users', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    api<any>(`/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deactivate: (id: string) =>
    api<void>(`/users/${id}`, { method: 'DELETE' }),
}

export const customersApi = {
  list: (params?: { skip?: number; limit?: number; search?: string; include_inactive?: boolean }) => {
    const p = new URLSearchParams()
    if (params?.skip) p.set('skip', String(params.skip))
    if (params?.limit) p.set('limit', String(params.limit))
    if (params?.search) p.set('search', params.search)
    if (params?.include_inactive) p.set('include_inactive', 'true')
    return api<any[]>('/customers?' + p)
  },
  create: (data: Record<string, unknown>) =>
    api<any>('/customers', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/customers/${id}`),
  update: (id: string, data: Record<string, unknown>) =>
    api<any>(`/customers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/customers/${id}`, { method: 'DELETE' }),
  getAddresses: (customerId: string) => api<any[]>(`/customers/${customerId}/addresses`),
  addAddress: (customerId: string, data: { address_type: string; street: string; house_number?: string; postal_code: string; city: string; country?: string }) =>
    api<any>(`/customers/${customerId}/addresses`, { method: 'POST', body: JSON.stringify(data) }),
  deleteAddress: (customerId: string, addressId: string) =>
    api<void>(`/customers/${customerId}/addresses/${addressId}`, { method: 'DELETE' }),
  exportData: (customerId: string) =>
    api<any>(`/customers/${customerId}/export`),
  dsgvoDelete: (customerId: string) =>
    api<{ action: string; reason?: string }>(`/customers/${customerId}/dsgvo-delete`, { method: 'POST' }),
  getDsgvoConsentPdf: async (customerId: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/customers/${customerId}/dsgvo-consent-pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('PDF konnte nicht geladen werden')
    return res.blob()
  },
  signDsgvoConsent: (customerId: string, signatureDataUrl: string) =>
    api<{ document_id: string; filename: string }>(`/customers/${customerId}/dsgvo-sign`, {
      method: 'POST',
      body: JSON.stringify({ signature_data_url: signatureDataUrl }),
    }),
}

export const vehiclesApi = {
  list: (params?: { customer_id?: string }) => {
    const p = new URLSearchParams()
    if (params?.customer_id) p.set('customer_id', params.customer_id)
    return api<any[]>('/vehicles?' + p)
  },
  create: (data: Record<string, unknown>) =>
    api<any>('/vehicles', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/vehicles/${id}`),
  update: (id: string, data: Record<string, unknown>) =>
    api<any>(`/vehicles/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/vehicles/${id}`, { method: 'DELETE' }),
}

export const manufacturersApi = {
  list: () => api<any[]>('/manufacturers'),
  create: (data: { name: string }) =>
    api<any>('/manufacturers', { method: 'POST', body: JSON.stringify(data) }),
  getModels: (manufacturerId: string) =>
    api<any[]>(`/manufacturers/${manufacturerId}/models`),
  createModel: (data: { manufacturer_id: string; name: string; variant?: string }) =>
    api<any>('/manufacturers/models', { method: 'POST', body: JSON.stringify(data) }),
}

export const articlesApi = {
  list: (params?: { search?: string; barcode?: string; category_id?: string; skip?: number; limit?: number }) => {
    const p = new URLSearchParams()
    if (params?.search) p.set('search', params.search)
    if (params?.barcode) p.set('barcode', params.barcode)
    if (params?.category_id) p.set('category_id', params.category_id)
    if (params?.skip != null) p.set('skip', String(params.skip))
    if (params?.limit != null) p.set('limit', String(params.limit))
    return api<any[]>('/articles?' + p)
  },
  create: (data: Record<string, unknown>) =>
    api<any>('/articles', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/articles/${id}`),
  getByBarcode: (barcode: string) =>
    api<any>(`/articles/barcode/${encodeURIComponent(barcode)}`),
  update: (id: string, data: Record<string, unknown>) =>
    api<any>(`/articles/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/articles/${id}`, { method: 'DELETE' }),
}

export const suppliersApi = {
  list: (params?: { search?: string }) => {
    const p = new URLSearchParams()
    if (params?.search) p.set('search', params.search)
    return api<any[]>('/suppliers?' + p)
  },
  get: (id: string) => api<any>(`/suppliers/${id}`),
  create: (data: Record<string, unknown>) =>
    api<any>('/suppliers', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Record<string, unknown>) =>
    api<any>(`/suppliers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/suppliers/${id}`, { method: 'DELETE' }),
}

export const articleCategoriesApi = {
  list: () => api<any[]>('/article-categories'),
  create: (data: { name: string; description?: string }) =>
    api<any>('/article-categories', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: { name?: string; description?: string }) =>
    api<any>(`/article-categories/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/article-categories/${id}`, { method: 'DELETE' }),
}

export const storageLocationsApi = {
  list: (includeInactive = false) => {
    const p = new URLSearchParams()
    if (includeInactive) p.set('include_inactive', 'true')
    return api<any[]>(`/storage-locations?${p}`)
  },
  create: (data: { name: string; description?: string }) =>
    api<any>('/storage-locations', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: { name?: string; description?: string; is_active?: boolean }) =>
    api<any>(`/storage-locations/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/storage-locations/${id}`, { method: 'DELETE' }),
}

export const stockApi = {
  movements: (params?: { article_id?: string }) => {
    const p = new URLSearchParams()
    if (params?.article_id) p.set('article_id', params.article_id)
    return api<any[]>('/stock/movements?' + p)
  },
  createMovement: (data: Record<string, unknown>) =>
    api<any>('/stock/movements', { method: 'POST', body: JSON.stringify(data) }),
  lowStock: () => api<any[]>('/stock/low-stock'),
  reservations: (params?: { article_id?: string; status?: string }) => {
    const p = new URLSearchParams()
    if (params?.article_id) p.set('article_id', params.article_id)
    if (params?.status) p.set('status', params.status)
    return api<any[]>('/stock/reservations?' + p)
  },
  createReservation: (data: { article_id: string; quantity: number; reference_type?: string; reference_id?: string; notes?: string }) =>
    api<any>('/stock/reservations', { method: 'POST', body: JSON.stringify(data) }),
  updateReservationStatus: (id: string, status: 'consumed' | 'cancelled') =>
    api<any>(`/stock/reservations/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
}

export const appointmentsApi = {
  list: (params?: {
    from_date?: string
    to_date?: string
    customer_id?: string
    status_filter?: string
    skip?: number
    limit?: number
  }) => {
    const p = new URLSearchParams()
    if (params?.from_date) p.set('from_date', params.from_date)
    if (params?.to_date) p.set('to_date', params.to_date)
    if (params?.customer_id) p.set('customer_id', params.customer_id)
    if (params?.status_filter) p.set('status_filter', params.status_filter)
    if (params?.skip != null) p.set('skip', String(params.skip))
    if (params?.limit != null) p.set('limit', String(params.limit))
    return api<any[]>('/appointments?' + p)
  },
  create: (data: {
    customer_id?: string
    vehicle_id?: string
    appointment_type: string
    title?: string
    description?: string
    starts_at: string
    ends_at: string
  }) => api<any>('/appointments', { method: 'POST', body: JSON.stringify(data) }),
  importExternal: (data: {
    external_booking_id: string
    starts_at: string
    ends_at: string
    customer_first_name?: string
    customer_last_name?: string
    customer_email?: string
    customer_phone?: string
    vehicle_license_plate?: string
    vehicle_vin?: string
    title?: string
    description?: string
    /** Leer = automatisch aus Titel/Beschreibung; sonst workshop | test_drive */
    appointment_type?: string
  }) => api<any>('/appointments/import-external', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/appointments/${id}`),
  update: (id: string, data: Record<string, unknown>) =>
    api<any>(`/appointments/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string, params?: { reason?: string }) => {
    const p = new URLSearchParams()
    if (params?.reason != null && params.reason !== '') p.set('reason', params.reason)
    const qs = p.toString()
    return api<{ termin_marktplatz_notified?: boolean; termin_marktplatz_error?: string }>(
      `/appointments/${id}${qs ? `?${qs}` : ''}`,
      { method: 'DELETE' }
    )
  },
}

export const documentsApi = {
  list: (params?: { customer_id?: string; vehicle_id?: string; skip?: number; limit?: number }) => {
    const p = new URLSearchParams()
    if (params?.customer_id) p.set('customer_id', params.customer_id)
    if (params?.vehicle_id) p.set('vehicle_id', params.vehicle_id)
    if (params?.skip != null) p.set('skip', String(params.skip))
    if (params?.limit != null) p.set('limit', String(params.limit))
    return api<any[]>('/documents?' + p)
  },
  upload: async (file: File, customerId?: string, vehicleId?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (customerId) formData.append('customer_id', customerId)
    if (vehicleId) formData.append('vehicle_id', vehicleId)
    const token = getToken()
    const res = await fetch(`${API_BASE}/documents`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (res.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
      throw new Error('Unauthorized')
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || res.statusText || 'Fehler')
    }
    return res.json()
  },
  get: (id: string) => api<any>(`/documents/${id}`),
  extractText: (id: string) =>
    api<any>(`/documents/${id}/extract-text`, { method: 'POST' }),
  update: (id: string, data: { customer_id?: string; vehicle_id?: string }) =>
    api<any>(`/documents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/documents/${id}`, { method: 'DELETE' }),
  sendEmail: (id: string, recipientEmail?: string) =>
    api<{ message: string; recipient: string }>('/documents/' + id + '/send-email', {
      method: 'POST',
      body: JSON.stringify({ recipient_email: recipientEmail || undefined }),
    }),
  getDownloadUrl: (id: string) => `${API_BASE}/documents/${id}/download`,
  getBlob: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/documents/${id}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('Laden fehlgeschlagen')
    return res.blob()
  },
  download: async (id: string, filename: string): Promise<void> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/documents/${id}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('Download fehlgeschlagen')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  },
}

export const invoicesApi = {
  list: (params?: { customer_id?: string; status_filter?: string; overdue?: boolean; date_from?: string; date_to?: string; skip?: number; limit?: number }) => {
    const p = new URLSearchParams()
    if (params?.customer_id) p.set('customer_id', params.customer_id)
    if (params?.date_from) p.set('date_from', params.date_from)
    if (params?.date_to) p.set('date_to', params.date_to)
    if (params?.status_filter) p.set('status_filter', params.status_filter)
    if (params?.overdue) p.set('overdue', 'true')
    if (params?.skip != null) p.set('skip', String(params.skip))
    if (params?.limit != null) p.set('limit', String(params.limit))
    return api<any[]>('/invoices?' + p)
  },
  create: (data: {
    customer_id: string
    workshop_order_id?: string
    invoice_date: string
    service_date?: string
    due_date?: string
    notes?: string
    items?: { description: string; quantity: number; unit?: string; unit_price: number; vat_rate?: number }[]
  }) => api<any>('/invoices', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/invoices/${id}`),
  getItems: (id: string) => api<any[]>(`/invoices/${id}/items`),
  issue: (id: string) =>
    api<any>(`/invoices/${id}/issue`, { method: 'POST' }),
  markPaid: (id: string) =>
    api<any>(`/invoices/${id}/mark-paid`, { method: 'POST' }),
  cancel: (id: string, reason?: string) =>
    api<any>(`/invoices/${id}/cancel`, { method: 'POST', body: JSON.stringify({ reason: reason || '' }) }),
  markReminder: (id: string, level: 1 | 2 | 3) =>
    api<any>(`/invoices/${id}/reminder?reminder_level=${level}`, { method: 'POST' }),
  correctionInfo: (id: string) => api<any>(`/invoices/${id}/correction-info`),
  createCorrection: (id: string, data: {
    reason: string
    lines: { item_id: string; quantity: number; return_to_stock: boolean }[]
    free_lines: { description: string; net_amount: number; vat_rate: number }[]
  }) => api<any>(`/invoices/${id}/correction`, { method: 'POST', body: JSON.stringify(data) }),
  downloadReminderPdf: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/invoices/${id}/reminder-pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('Mahnbrief konnte nicht geladen werden')
    return res.blob()
  },
  getPdfUrl: (id: string) => `/api/v1/invoices/${id}/pdf`,
  downloadPdf: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/invoices/${id}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('PDF konnte nicht geladen werden')
    return res.blob()
  },
  sendEmail: (id: string, recipientEmail?: string) =>
    api<{ message: string; recipient: string }>('/invoices/' + id + '/send-email', {
      method: 'POST',
      body: JSON.stringify({ recipient_email: recipientEmail || undefined }),
    }),
  downloadZugferd: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/invoices/${id}/zugferd`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('ZUGFeRD konnte nicht geladen werden')
    return res.blob()
  },
  importZugferd: async (file: File): Promise<any> => {
    const token = getToken()
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE}/invoices/zugferd/import`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'ZUGFeRD-Import fehlgeschlagen')
    }
    return res.json()
  },
}

export const accountingApi = {
  exportZip: async (dateFrom: string, dateTo: string): Promise<Blob> => {
    const token = getToken()
    const p = new URLSearchParams({ date_from: dateFrom, date_to: dateTo })
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}
    if (typeof window !== 'undefined' && window.location?.hostname?.includes('ngrok')) {
      headers['ngrok-skip-browser-warning'] = '1'
    }
    const res = await fetch(`${API_BASE}/accounting/export?${p}`, { headers })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Export fehlgeschlagen')
    }
    return res.blob()
  },
  datevSettings: () => api<any>('/accounting/datev/settings'),
  saveDatevSettings: (data: Record<string, unknown>) =>
    api<any>('/accounting/datev/settings', { method: 'PUT', body: JSON.stringify(data) }),
  datevPreview: (dateFrom: string, dateTo: string, includeIncoming: boolean) =>
    api<any>(`/accounting/datev/preview?${new URLSearchParams({ date_from: dateFrom, date_to: dateTo, include_incoming: String(includeIncoming) })}`),
  datevExport: async (dateFrom: string, dateTo: string, includeIncoming: boolean): Promise<Blob> => {
    const token = getToken()
    const p = new URLSearchParams({ date_from: dateFrom, date_to: dateTo, include_incoming: String(includeIncoming) })
    const res = await fetch(`${API_BASE}/accounting/datev/export?${p}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'DATEV-Export fehlgeschlagen')
    }
    return res.blob()
  },
}

export const incomingInvoicesApi = {
  list: (params?: { date_from?: string; date_to?: string; status_filter?: string; skip?: number; limit?: number }) => {
    const p = new URLSearchParams()
    if (params?.date_from) p.set('date_from', params.date_from)
    if (params?.date_to) p.set('date_to', params.date_to)
    if (params?.status_filter) p.set('status_filter', params.status_filter)
    if (params?.skip != null) p.set('skip', String(params.skip))
    if (params?.limit != null) p.set('limit', String(params.limit))
    return api<any[]>('/incoming-invoices?' + p)
  },
  create: (data: {
    supplier_name: string
    invoice_number: string
    invoice_date: string
    due_date?: string
    net_amount: number
    vat_rate?: number
    category?: string
    notes?: string
  }) => api<any>('/incoming-invoices', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/incoming-invoices/${id}`),
  update: (id: string, data: Partial<{
    supplier_name: string; invoice_number: string; invoice_date: string
    due_date: string; net_amount: number; vat_rate: number
    status: string; category: string; notes: string
  }>) => api<any>(`/incoming-invoices/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => api<void>(`/incoming-invoices/${id}`, { method: 'DELETE' }),
  uploadPdf: async (id: string, file: File): Promise<any> => {
    const token = getToken()
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE}/incoming-invoices/${id}/upload-pdf`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Upload fehlgeschlagen')
    }
    return res.json()
  },
  downloadPdf: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/incoming-invoices/${id}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('PDF nicht verfügbar')
    return res.blob()
  },
  /** E-Rechnung (ZUGFeRD-PDF oder XRechnung-XML) importieren und als Eingangsrechnung speichern */
  importEInvoice: async (file: File): Promise<any> => {
    const token = getToken()
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_BASE}/incoming-invoices/import-einvoice`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(typeof err.detail === 'string' ? err.detail : 'Import fehlgeschlagen')
    }
    return res.json()
  },
  /** Unverändertes Original der E-Rechnung herunterladen */
  downloadOriginal: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/incoming-invoices/${id}/original`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('Original nicht verfügbar')
    return res.blob()
  },
}

export const maintenancePlansApi = {
  list: (params?: { manufacturer_id?: string; vehicle_model_id?: string }) => {
    const p = new URLSearchParams()
    if (params?.manufacturer_id) p.set('manufacturer_id', params.manufacturer_id)
    if (params?.vehicle_model_id) p.set('vehicle_model_id', params.vehicle_model_id)
    return api<any[]>('/maintenance-plans?' + p)
  },
  create: (data: {
    manufacturer_id: string
    vehicle_model_id?: string
    name: string
    description?: string
    interval_km?: number
    interval_hours?: number
    interval_months?: number
  }) => api<any>('/maintenance-plans', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/maintenance-plans/${id}`),
  update: (id: string, data: { name?: string; description?: string; interval_km?: number; interval_hours?: number; interval_months?: number }) =>
    api<any>(`/maintenance-plans/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/maintenance-plans/${id}`, { method: 'DELETE' }),
  getTasks: (planId: string) => api<any[]>(`/maintenance-plans/${planId}/tasks`),
  addTask: (planId: string, data: { name: string; description?: string; sort_order?: number; article_id?: string; quantity?: number; unit?: string }) =>
    api<any>(`/maintenance-plans/${planId}/tasks`, { method: 'POST', body: JSON.stringify(data) }),
  updateTask: (planId: string, taskId: string, data: { name?: string; description?: string; sort_order?: number; article_id?: string | null; quantity?: number; unit?: string | null }) =>
    api<any>(`/maintenance-plans/${planId}/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteTask: (planId: string, taskId: string) =>
    api<void>(`/maintenance-plans/${planId}/tasks/${taskId}`, { method: 'DELETE' }),
  forVehicle: (vehicleId: string) =>
    api<any | null>(`/maintenance-plans/for-vehicle/${vehicleId}`),
  uploadDocument: async (planId: string, file: File): Promise<any> => {
    const token = getToken()
    const formData = new FormData()
    formData.append('file', file)
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}
    const res = await fetch(`${API_BASE}/maintenance-plans/${planId}/document`, {
      method: 'POST',
      headers,
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Upload fehlgeschlagen')
    }
    return res.json()
  },
  deleteDocument: (planId: string) =>
    api<void>(`/maintenance-plans/${planId}/document`, { method: 'DELETE' }),
  getDocumentUrl: (planId: string) => `${API_BASE}/maintenance-plans/${planId}/document`,
}

export const workshopOrdersApi = {
  list: (params?: { customer_id?: string; vehicle_id?: string; status_filter?: string; skip?: number; limit?: number }) => {
    const p = new URLSearchParams()
    if (params?.customer_id) p.set('customer_id', params.customer_id)
    if (params?.vehicle_id) p.set('vehicle_id', params.vehicle_id)
    if (params?.status_filter) p.set('status_filter', params.status_filter)
    if (params?.skip != null) p.set('skip', String(params.skip))
    if (params?.limit != null) p.set('limit', String(params.limit))
    return api<any[]>('/workshop-orders?' + p)
  },
  create: (data: {
    customer_id: string
    vehicle_id: string
    appointment_id?: string
    maintenance_plan_id?: string
    labor_rate_id?: string
    complaint_description?: string
    internal_notes?: string
    mileage_at_checkin?: number
    operating_hours_at_checkin?: number
    estimated_work_minutes?: number
  }) => api<any>('/workshop-orders', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/workshop-orders/${id}`),
  update: (id: string, data: { customer_id?: string; vehicle_id?: string; complaint_description?: string; status?: string; actual_work_minutes?: number; internal_notes?: string }) =>
    api<any>(`/workshop-orders/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  getItems: (orderId: string) => api<any[]>(`/workshop-orders/${orderId}/items`),
  addItem: (orderId: string, data: {
    item_type: string
    article_id?: string
    description: string
    quantity?: number
    unit?: string
    unit_price?: number
    vat_rate?: number
  }) => api<any>(`/workshop-orders/${orderId}/items`, { method: 'POST', body: JSON.stringify(data) }),
  deleteItem: (orderId: string, itemId: string) =>
    api<void>(`/workshop-orders/${orderId}/items/${itemId}`, { method: 'DELETE' }),
  getPdf: async (orderId: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/workshop-orders/${orderId}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('PDF konnte nicht geladen werden')
    return res.blob()
  },
}

export interface QuotePayload {
  quote_type: 'offer' | 'estimate'
  customer_id: string
  vehicle_id?: string | null
  quote_date: string
  valid_until?: string | null
  subject?: string | null
  notes?: string | null
  internal_notes?: string | null
  items: {
    item_type: 'labor' | 'material' | 'service'
    article_id?: string | null
    description: string
    quantity: number
    unit?: string | null
    unit_price: number
    vat_rate: number
  }[]
}

export const quotesApi = {
  list: (params?: { customer_id?: string; status_filter?: string; skip?: number; limit?: number }) => {
    const p = new URLSearchParams()
    if (params?.customer_id) p.set('customer_id', params.customer_id)
    if (params?.status_filter) p.set('status_filter', params.status_filter)
    if (params?.skip != null) p.set('skip', String(params.skip))
    if (params?.limit != null) p.set('limit', String(params.limit))
    return api<any[]>('/quotes?' + p)
  },
  get: (id: string) => api<any>(`/quotes/${id}`),
  create: (data: QuotePayload) => api<any>('/quotes', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: QuotePayload) => api<any>(`/quotes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string) => api<void>(`/quotes/${id}`, { method: 'DELETE' }),
  setStatus: (id: string, status: 'sent' | 'accepted' | 'rejected') =>
    api<any>(`/quotes/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) }),
  duplicate: (id: string) => api<any>(`/quotes/${id}/duplicate`, { method: 'POST' }),
  convert: (id: string, data: { vehicle_id?: string; complaint_description?: string }) =>
    api<any>(`/quotes/${id}/convert`, { method: 'POST', body: JSON.stringify(data) }),
  sendEmail: (id: string, recipientEmail?: string) =>
    api<any>(`/quotes/${id}/send-email`, { method: 'POST', body: JSON.stringify({ recipient_email: recipientEmail || null }) }),
  getPdf: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/quotes/${id}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('PDF konnte nicht geladen werden')
    return res.blob()
  },
}

export interface PurchaseOrderPayload {
  supplier_id: string
  order_date: string
  expected_date?: string | null
  notes?: string | null
  internal_notes?: string | null
  items: {
    article_id?: string | null
    description: string
    supplier_article_number?: string | null
    quantity: number
    unit?: string | null
    unit_price: number
    vat_rate: number
  }[]
}

export const purchaseOrdersApi = {
  list: (params?: { supplier_id?: string; status_filter?: string; open_only?: boolean }) => {
    const p = new URLSearchParams()
    if (params?.supplier_id) p.set('supplier_id', params.supplier_id)
    if (params?.status_filter) p.set('status_filter', params.status_filter)
    if (params?.open_only) p.set('open_only', 'true')
    return api<any[]>('/purchase-orders?' + p)
  },
  suggestions: () => api<any[]>('/purchase-orders/suggestions'),
  get: (id: string) => api<any>(`/purchase-orders/${id}`),
  create: (data: PurchaseOrderPayload) => api<any>('/purchase-orders', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: PurchaseOrderPayload) =>
    api<any>(`/purchase-orders/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string) => api<void>(`/purchase-orders/${id}`, { method: 'DELETE' }),
  markSent: (id: string) => api<any>(`/purchase-orders/${id}/mark-sent`, { method: 'POST' }),
  sendEmail: (id: string, recipientEmail?: string) =>
    api<any>(`/purchase-orders/${id}/send-email`, { method: 'POST', body: JSON.stringify({ recipient_email: recipientEmail || null }) }),
  receive: (id: string, data: { lines: { item_id: string; quantity: number }[]; delivery_note?: string | null; update_purchase_price?: boolean }) =>
    api<any>(`/purchase-orders/${id}/receive`, { method: 'POST', body: JSON.stringify(data) }),
  cancel: (id: string) => api<any>(`/purchase-orders/${id}/cancel`, { method: 'POST' }),
  getPdf: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/purchase-orders/${id}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('PDF konnte nicht geladen werden')
    return res.blob()
  },
}

export const stockCountsApi = {
  list: () => api<any[]>('/stock-counts'),
  get: (id: string) => api<any>(`/stock-counts/${id}`),
  create: (data: { count_date: string; storage_location_id?: string; category_id?: string; notes?: string }) =>
    api<any>('/stock-counts', { method: 'POST', body: JSON.stringify(data) }),
  updateItem: (countId: string, itemId: string, data: { counted_qty: number | null; note?: string }) =>
    api<any>(`/stock-counts/${countId}/items/${itemId}`, { method: 'PUT', body: JSON.stringify(data) }),
  complete: (id: string) => api<any>(`/stock-counts/${id}/complete`, { method: 'POST' }),
  cancel: (id: string) => api<any>(`/stock-counts/${id}/cancel`, { method: 'POST' }),
  getPdf: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/stock-counts/${id}/pdf`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    if (!res.ok) throw new Error('PDF konnte nicht geladen werden')
    return res.blob()
  },
  getCsv: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/stock-counts/${id}/csv`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    if (!res.ok) throw new Error('CSV konnte nicht geladen werden')
    return res.blob()
  },
}

export interface HelpSource { id: string; article_id: string; title: string }
export interface HelpAnswer { answer: string; mode: 'ai' | 'search'; sources: HelpSource[]; notice?: string | null }

export const helpApi = {
  status: () => api<{ ai_enabled: boolean; model: string | null }>('/help/status'),
  articles: () => api<{ id: string; title: string; sections: { id: string; heading: string; text: string }[] }[]>('/help/articles'),
  search: (q: string) => api<{ id: string; article_id: string; article_title: string; heading: string; text: string }[]>(`/help/search?q=${encodeURIComponent(q)}`),
  ask: (question: string, history: { role: 'user' | 'assistant'; content: string }[]) =>
    api<HelpAnswer>('/help/ask', { method: 'POST', body: JSON.stringify({ question, history }) }),
}

export const laborRatesApi = {
  list: () => api<any[]>('/labor-rates'),
  create: (data: { name: string; description?: string; rate_per_hour: number; is_default?: boolean }) =>
    api<any>('/labor-rates', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: { name?: string; description?: string; rate_per_hour?: number; is_default?: boolean; is_active?: boolean }) =>
    api<any>(`/labor-rates/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => api<void>(`/labor-rates/${id}`, { method: 'DELETE' }),
}

export const tasksApi = {
  list: () => api<any[]>('/tasks'),
  run: (taskName: string) =>
    api<{ task_id: string; task_name: string; status: string }>(`/tasks/${encodeURIComponent(taskName)}/run`, { method: 'POST' }),
  status: (taskId: string) =>
    api<{ task_id: string; status: string; result?: any; error?: string }>(`/tasks/${taskId}/status`),
}

export const healthApi = {
  check: async (): Promise<{ status: string; app: string; version: string; checks: Record<string, string>; timestamp: string }> => {
    const token = getToken()
    const res = await fetch(`${API_BASE.replace('/api/v1', '')}/health`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    return res.json()
  },
}

