import { createContext, useContext, useState, useEffect } from 'react'
import { decodeJWT, isTokenExpired } from '../utils/jwt'

const AuthContext = createContext(null)

const TOKEN_KEY = 'invoiceflow_token'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Load token from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY)
    if (stored && !isTokenExpired(stored)) {
      const payload = decodeJWT(stored)
      if (payload) {
        setToken(stored)
        setUser({
          sub: Number(payload.sub),
          role: payload.role,        // SELLER | INVESTOR
          email: payload.email,
          full_name: payload.full_name,
        })
      }
    }
    setLoading(false)
  }, [])

  /**
   * Store JWT and decode user info from it.
   * Called after a successful login API response.
   */
  function login(newToken) {
    const payload = decodeJWT(newToken)
    if (!payload) return
    localStorage.setItem(TOKEN_KEY, newToken)
    setToken(newToken)
    setUser({
      sub: Number(payload.sub),
      role: payload.role,
      email: payload.email,
      full_name: payload.full_name,
    })
  }

  /**
   * Clear all auth state and localStorage.
   */
  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

/**
 * Hook to consume auth context.
 * Returns { token, user, loading, login, logout }
 */
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
