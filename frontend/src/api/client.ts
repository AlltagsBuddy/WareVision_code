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
    smtp_host: string
    smtp_port: string
    smtp_user: string
    smtp_password: string
    smtp_from: string
    smtp_tls: string
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
    smtp_host?: string
    smtp_port?: string
    smtp_user?: string
    smtp_password?: string
    smtp_from?: string
    smtp_tls?: string
    termin_marktplatz_api_key?: string
    termin_marktplatz_webhook_base_url?: string
  }) =>
    api<{ company_name: string; company_address: string; company_vat_id: string }>('/settings', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  getTerminMarktplatzApiKey: () =>
    api<{ api_key: string | null }>('/settings/termin-marktplatz-api-key'),
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
  create: (data: { email: string; first_name: string; last_name: string; password: string; role_id: string }) =>
    api<any>('/users', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: { first_name?: string; last_name?: string; is_active?: boolean; password?: string }) =>
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
  list: (params?: { search?: string; barcode?: string }) => {
    const p = new URLSearchParams()
    if (params?.search) p.set('search', params.search)
    if (params?.barcode) p.set('barcode', params.barcode)
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
  }) => api<any>('/appointments/import-external', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/appointments/${id}`),
  update: (id: string, data: Record<string, unknown>) =>
    api<any>(`/appointments/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/appointments/${id}`, { method: 'DELETE' }),
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
  list: (params?: { customer_id?: string; status_filter?: string; overdue?: boolean; skip?: number; limit?: number }) => {
    const p = new URLSearchParams()
    if (params?.customer_id) p.set('customer_id', params.customer_id)
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
  markReminder: (id: string, level: 1 | 2 | 3) =>
    api<any>(`/invoices/${id}/reminder?reminder_level=${level}`, { method: 'POST' }),
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
  delete: (id: string) =>
    api<void>(`/maintenance-plans/${id}`, { method: 'DELETE' }),
  getTasks: (planId: string) => api<any[]>(`/maintenance-plans/${planId}/tasks`),
  addTask: (planId: string, data: { name: string; description?: string; sort_order?: number }) =>
    api<any>(`/maintenance-plans/${planId}/tasks`, { method: 'POST', body: JSON.stringify(data) }),
  deleteTask: (planId: string, taskId: string) =>
    api<void>(`/maintenance-plans/${planId}/tasks/${taskId}`, { method: 'DELETE' }),
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
    complaint_description?: string
    internal_notes?: string
    mileage_at_checkin?: number
    operating_hours_at_checkin?: number
    estimated_work_minutes?: number
  }) => api<any>('/workshop-orders', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/workshop-orders/${id}`),
  update: (id: string, data: { status?: string; actual_work_minutes?: number; internal_notes?: string }) =>
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
}
