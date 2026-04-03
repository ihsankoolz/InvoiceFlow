import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from './AuthContext'

const NotificationContext = createContext(null)

export function NotificationProvider({ children }) {
  const { user } = useAuth()
  const [toasts, setToasts] = useState([])
  const wsRef = useRef(null)

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.map((t) => t.id === id ? { ...t, leaving: true } : t))
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 300)
  }, [])

  const addToast = useCallback((msg) => {
    const id = msg.id ? `ws-${msg.id}` : `ws-${Date.now()}-${Math.random()}`
    setToasts((prev) => [...prev.slice(-4), { ...msg, id, leaving: false }])
    setTimeout(() => dismiss(id), 5000)
  }, [dismiss])

  useEffect(() => {
    if (!user) return

    let cancelled = false
    try {
      const ws = new WebSocket(`${import.meta.env.VITE_WS_URL}/ws/${user.sub}`)
      wsRef.current = ws

      ws.onopen = () => { if (cancelled) ws.close() }
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (!cancelled) addToast(msg)
        } catch { /* ignore parse errors */ }
      }
      ws.onerror = () => { /* silently ignore */ }
    } catch { /* silently ignore if WS unavailable */ }

    return () => {
      cancelled = true
      const ws = wsRef.current
      wsRef.current = null
      if (ws && ws.readyState === WebSocket.OPEN) ws.close()
    }
  }, [user, addToast])

  return (
    <NotificationContext.Provider value={{ toasts, dismiss }}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  const ctx = useContext(NotificationContext)
  if (!ctx) throw new Error('useNotifications must be used inside <NotificationProvider>')
  return ctx
}
