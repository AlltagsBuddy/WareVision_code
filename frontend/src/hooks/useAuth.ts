import { useState, useEffect } from 'react'
import { authApi } from '../api/client'
import { canView as viewOf, canWrite as writeOf, hasRight as rightOf, isManager as managerOf, type Right } from '../utils/permissions'

export type ModulePermission = { visible: boolean; write: boolean }
export type UserPermissions = Record<string, any>

export type AuthUser = {
  id?: string
  email: string
  first_name: string
  last_name: string
  role_name: string
  role_label?: string
  is_manager?: boolean
  is_active?: boolean
  permissions?: UserPermissions
}

export type LoginStep =
  | { step: 'ok' }
  | { step: '2fa'; challenge: string }
  | { step: 'setup'; challenge: string }

export function useAuth() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    authApi.me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [token])

  /** Zugangstoken speichern und Benutzer laden (nach Passwort bzw. Zwei-Faktor-Schritt). */
  const completeLogin = async (accessToken: string) => {
    localStorage.setItem('token', accessToken)
    setToken(accessToken)
    const u = await authApi.me()
    setUser(u)
  }

  /**
   * Anmeldung mit Passwort. Ergebnis:
   * - 'ok': angemeldet
   * - '2fa': Code aus der Authenticator-App nötig
   * - 'setup': Zwei-Faktor muss erst eingerichtet werden
   */
  const login = async (email: string, password: string): Promise<LoginStep> => {
    const res = await authApi.login(email, password)
    if (res.access_token) {
      await completeLogin(res.access_token)
      return { step: 'ok' }
    }
    if (res.two_factor_required && res.challenge_token) return { step: '2fa', challenge: res.challenge_token }
    if (res.two_factor_setup_required && res.challenge_token) return { step: 'setup', challenge: res.challenge_token }
    throw new Error('Unerwartete Antwort bei der Anmeldung')
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
  }

  /** Bereich sehen bzw. ändern; Admin und Chef/Chefin dürfen alles. */
  const canView = (module: string): boolean => viewOf(user, module)
  const canWrite = (module: string): boolean => writeOf(user, module)
  /** Sonderrecht (Rechnungen, Buchhaltung, DSGVO, Lager & Einkauf) */
  const hasRight = (right: Right): boolean => rightOf(user, right)
  const isManager = managerOf(user)

  return { token, user, loading, login, completeLogin, logout, canView, canWrite, hasRight, isManager }
}
