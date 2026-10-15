/**
 * Rechte des angemeldeten Benutzers (Anzeige). Der Server prüft dieselben Regeln bei jeder Anfrage.
 * - Admin und Chef/Chefin (Leitung) dürfen alles.
 * - Sonst: Bereiche (sehen/ändern) und Sonderrechte wie in der Benutzerverwaltung freigegeben.
 */
export type Right = 'invoices_manage' | 'accounting' | 'dsgvo_export' | 'dsgvo_delete' | 'lager_einkauf'

type PermUser = {
  role_name?: string
  is_manager?: boolean
  permissions?: Record<string, unknown> | null
} | null | undefined

const MANAGER_ROLES = ['admin', 'chef']

export function isManager(user: PermUser): boolean {
  if (!user) return false
  return user.is_manager === true || MANAGER_ROLES.includes(user.role_name ?? '')
}

function moduleEntry(user: PermUser, module: string): { visible?: boolean; write?: boolean } {
  const entry = user?.permissions?.[module]
  return entry && typeof entry === 'object' ? (entry as { visible?: boolean; write?: boolean }) : {}
}

export function canView(user: PermUser, module: string): boolean {
  if (!user) return false
  return isManager(user) || moduleEntry(user, module).visible !== false
}

export function canWrite(user: PermUser, module: string): boolean {
  if (!user) return false
  return isManager(user) || (moduleEntry(user, module).visible !== false && moduleEntry(user, module).write !== false)
}

export function hasRight(user: PermUser, right: Right): boolean {
  if (!user) return false
  if (isManager(user)) return true
  const rights = user.permissions?.rights
  return !!rights && typeof rights === 'object' && (rights as Record<string, unknown>)[right] === true
}
