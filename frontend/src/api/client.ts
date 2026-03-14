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

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText || 'Fehler')
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const authApi = {
  login: (email: string, password: string) =>
    api<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: () => api<{ id: string; email: string; first_name: string; last_name: string; role_name: string }>('/auth/me'),
}

export const customersApi = {
  list: (params?: { skip?: number; limit?: number; search?: string }) => {
    const p = new URLSearchParams()
    if (params?.skip) p.set('skip', String(params.skip))
    if (params?.limit) p.set('limit', String(params.limit))
    if (params?.search) p.set('search', params.search)
    return api<any[]>('/customers?' + p)
  },
  create: (data: Record<string, unknown>) =>
    api<any>('/customers', { method: 'POST', body: JSON.stringify(data) }),
  get: (id: string) => api<any>(`/customers/${id}`),
  update: (id: string, data: Record<string, unknown>) =>
    api<any>(`/customers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/customers/${id}`, { method: 'DELETE' }),
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
  get: (id: string) => api<any>(`/appointments/${id}`),
  update: (id: string, data: Record<string, unknown>) =>
    api<any>(`/appointments/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) =>
    api<void>(`/appointments/${id}`, { method: 'DELETE' }),
}

export const invoicesApi = {
  list: (params?: { customer_id?: string; status_filter?: string; skip?: number; limit?: number }) => {
    const p = new URLSearchParams()
    if (params?.customer_id) p.set('customer_id', params.customer_id)
    if (params?.status_filter) p.set('status_filter', params.status_filter)
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
  getPdfUrl: (id: string) => `/api/v1/invoices/${id}/pdf`,
  downloadPdf: async (id: string): Promise<Blob> => {
    const token = getToken()
    const res = await fetch(`${API_BASE}/invoices/${id}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new Error('PDF konnte nicht geladen werden')
    return res.blob()
  },
}

export const workshopOrdersApi = {
  list: (params?: { customer_id?: string; status_filter?: string; skip?: number; limit?: number }) => {
    const p = new URLSearchParams()
    if (params?.customer_id) p.set('customer_id', params.customer_id)
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
}
