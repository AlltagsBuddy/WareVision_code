import { useState, useEffect } from 'react'
import { authApi } from '../api/client'

export type ModulePermission = { visible: boolean; write: boolean }
export type UserPermissions = Record<string, ModulePermission>

export type AuthUser = {
  id?: string
  email: string
  first_name: string
  last_name: string
  role_name: string
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

  /**
   * Prueft ob der aktuelle Benutzer ein Modul sehen darf.
   * Admins duerfen immer alles sehen.
   */
  const canView = (module: string): boolean => {
    if (!user) return false
    if (user.role_name === 'admin') return true
    return user.permissions?.[module]?.visible !== false
  }

  /**
   * Prueft ob der aktuelle Benutzer in ein Modul schreiben darf.
   * Admins duerfen immer schreiben.
   */
  const canWrite = (module: string): boolean => {
    if (!user) return false
    if (user.role_name === 'admin') return true
    return user.permissions?.[module]?.write !== false
  }

  return { token, user, loading, login, completeLogin, logout, canView, canWrite }
}
