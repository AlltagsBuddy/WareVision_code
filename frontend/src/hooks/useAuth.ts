import { useState, useEffect } from 'react'
import { authApi } from '../api/client'

export function useAuth() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
  const [user, setUser] = useState<{ email: string; first_name: string; last_name: string; role_name: string } | null>(null)
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

  return { token, user, loading, login, logout }
}
