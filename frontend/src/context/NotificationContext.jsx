import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from './AuthContext'
import api from '../api/axios'

const NotificationContext = createContext(null)

export function NotificationProvider({ children }) {
  const { user } = useAuth()
  const [toasts, setToasts] = useState([])
  const [lastMessage, setLastMessage] = useState(null)
  const [unreadCount, setUnreadCount] = useState(0)
  const wsRef = useRef(null)

  useEffect(() => {
    if (!user) { setUnreadCount(0); return }
    api.get(`/notifications?user_id=${user.sub}`)
      .then((res) => {
        const data = res.data?.notifications || res.data || []
        const arr = Array.isArray(data) ? data : []
        setUnreadCount(arr.filter((n) => !n.is_read).length)
      })
      .catch(() => {})
  }, [user])

  const resetUnreadCount = useCallback(() => setUnreadCount(0), [])

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.map((t) => t.id === id ? { ...t, leaving: true } : t))
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 300)
  }, [])

  const addToast = useCallback((msg) => {
    const id = msg.id ? `ws-${msg.id}` : `ws-${Date.now()}-${Math.random()}`
    setToasts((prev) => [...prev.slice(-4), { ...msg, id, leaving: false }])
    setUnreadCount((prev) => prev + 1)
    setTimeout(() => dismiss(id), 5000)
  }, [dismiss])

  useEffect(() => {
    if (!user) return

    let cancelled = false
    let retryTimeout = null
    let delay = 1000

    function connect() {
      if (cancelled) return
      try {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/${user.sub}`)
        wsRef.current = ws

        ws.onopen = () => {
          if (cancelled) { ws.close(); return }
          delay = 1000 // reset backoff on successful connection
        }
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            if (!cancelled) { addToast(msg); setLastMessage(msg) }
          } catch { /* ignore parse errors */ }
        }
        ws.onerror = () => { /* onclose will handle reconnect */ }
        ws.onclose = () => {
          if (cancelled) return
          retryTimeout = setTimeout(() => {
            delay = Math.min(delay * 2, 30000) // exponential backoff, cap at 30s
            connect()
          }, delay)
        }
      } catch { /* ignore if WS unavailable, onclose will retry */ }
    }

    connect()

    return () => {
      cancelled = true
      clearTimeout(retryTimeout)
      const ws = wsRef.current
      wsRef.current = null
      if (ws && ws.readyState === WebSocket.OPEN) ws.close()
    }
  }, [user, addToast])

  return (
    <NotificationContext.Provider value={{ toasts, dismiss, lastMessage, unreadCount, resetUnreadCount }}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotifications() {
  const ctx = useContext(NotificationContext)
  if (!ctx) throw new Error('useNotifications must be used inside <NotificationProvider>')
  return ctx
}
