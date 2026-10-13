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

  const login = async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password)
    localStorage.setItem('token', access_token)
    setToken(access_token)
    const u = await authApi.me()
    setUser(u)
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

  return { token, user, loading, login, logout, canView, canWrite }
}
