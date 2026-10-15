import { describe, expect, it } from 'vitest'
import { canView, canWrite, hasRight, isManager } from './permissions'

const mitarbeiter = {
  role_name: 'mitarbeiter',
  is_manager: false,
  permissions: {
    appointments: { visible: true, write: true },
    customers: { visible: true, write: false },
    invoices: { visible: false, write: false },
    rights: { dsgvo_export: true, accounting: false },
  },
}

describe('Rechte im Frontend', () => {
  it('Admin und Chef/Chefin dürfen alles', () => {
    for (const role_name of ['admin', 'chef']) {
      const u = { role_name, permissions: { invoices: { visible: false, write: false } } }
      expect(isManager(u)).toBe(true)
      expect(canView(u, 'invoices')).toBe(true)
      expect(hasRight(u, 'dsgvo_delete')).toBe(true)
    }
  })

  it('Bereiche: sehen und ändern getrennt', () => {
    expect(canWrite(mitarbeiter, 'appointments')).toBe(true)
    expect(canView(mitarbeiter, 'customers')).toBe(true)
    expect(canWrite(mitarbeiter, 'customers')).toBe(false)
    expect(canView(mitarbeiter, 'invoices')).toBe(false)
  })

  it('Sonderrechte nur, wenn ausdrücklich freigegeben', () => {
    expect(hasRight(mitarbeiter, 'dsgvo_export')).toBe(true)
    expect(hasRight(mitarbeiter, 'accounting')).toBe(false)
    expect(hasRight(mitarbeiter, 'lager_einkauf')).toBe(false)
    expect(hasRight(null, 'accounting')).toBe(false)
  })
})
