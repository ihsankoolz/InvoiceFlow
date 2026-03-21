import { useState, useEffect, useRef } from 'react'
import { Bell, AlertTriangle, CheckCircle, DollarSign, Info } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'

/* ── Animation helpers ── */
function useInView(threshold = 0.05) {
  const ref = useRef(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setInView(true); obs.disconnect() } },
      { threshold }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return [ref, inView]
}

function fadeUp(visible, delay = 0) {
  if (visible) return { animation: 'notifFadeUp 600ms ease both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(20px)' }
}

function fmtDate(str) {
  if (!str) return ''
  const d = new Date(str)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return d.toLocaleDateString('en-SG', { day: '2-digit', month: 'short' })
}

function NotifIcon({ eventType }) {
  const t = (eventType || '').toUpperCase()
  if (t.includes('BID') || t.includes('OUTBID')) return <DollarSign size={18} className="text-[#ff9500]" />
  if (t.includes('ALERT') || t.includes('WARN') || t.includes('OVERDUE')) return <AlertTriangle size={18} className="text-red-500" />
  if (t.includes('SUCCESS') || t.includes('REPAID') || t.includes('FINANCED') || t.includes('ACCEPTED')) return <CheckCircle size={18} className="text-[#3e9b00]" />
  if (t.includes('PAYMENT') || t.includes('WALLET')) return <DollarSign size={18} className="text-[#3e9b00]" />
  if (t.includes('BELL') || t.includes('NOTIFICATION')) return <Bell size={18} className="text-ink/50" />
  return <Info size={18} className="text-ink/50" />
}

export default function NotificationsPage() {
  const { user } = useAuth()

  const [notifications, setNotifications] = useState([])
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState('')
  const [markingAll, setMarkingAll]       = useState(false)

  const wsRef = useRef(null)

  const [headerRef, headerInView] = useInView(0.05)
  const [listRef, listInView]     = useInView(0.05)

  useEffect(() => {
    if (!user) return
    loadNotifications()
    connectWS()
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadNotifications() {
    setLoading(true)
    setError('')
    try {
      const res = await api.get(`/notifications?user_id=${user.sub}`)
      const data = res.data?.notifications || res.data || []
      setNotifications(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to load notifications.')
    } finally {
      setLoading(false)
    }
  }

  function connectWS() {
    try {
      const ws = new WebSocket(`ws://localhost:5005/ws/${user.sub}`)
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          // Push new notification to top of list
          const newNotif = {
            id: msg.id || Date.now(),
            title: msg.title || msg.event_type || 'Notification',
            message: msg.message || msg.body || '',
            event_type: msg.event_type || 'NOTIFICATION',
            created_at: msg.created_at || new Date().toISOString(),
            is_read: false,
            ...msg,
          }
          setNotifications((prev) => [newNotif, ...prev])
        } catch {
          // Ignore parse errors
        }
      }

      ws.onerror = () => {
        // Silently ignore WS errors — not all environments have WS running
      }
    } catch {
      // Silently ignore if WS is unavailable
    }
  }

  async function markAllRead() {
    setMarkingAll(true)
    try {
      await api.post('/notifications/mark-all-read', { user_id: user.sub })
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    } catch {
      // Optimistically mark as read even if request fails
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    } finally {
      setMarkingAll(false)
    }
  }

  async function markRead(id) {
    try {
      await api.post(`/notifications/${id}/read`)
    } catch {
      // ignore
    }
    setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, is_read: true } : n))
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length

  return (
    <AppLayout>
      <style>{`
        @keyframes notifFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Header strip */}
      <div ref={headerRef} className="bg-teal px-8 py-10" style={fadeUp(headerInView, 0)}>
        <div className="max-w-3xl mx-auto flex items-end justify-between">
          <div>
            <h1 className="font-display font-semibold text-[42px] text-[#fff8ec] leading-tight flex items-center gap-3">
              Notifications
              {unreadCount > 0 && (
                <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-[#ff9500] text-white font-['Lato'] text-xs font-bold">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </h1>
            <p className="font-['Lato'] text-[#fff8ec]/60 text-sm mt-1">Your recent activity and alerts</p>
          </div>
          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              disabled={markingAll}
              className="flex-shrink-0 bg-[#fff8ec] text-teal rounded-[22px] px-5 py-2.5 font-['Lato'] text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-60"
            >
              {markingAll ? 'Marking…' : 'Mark all read'}
            </button>
          )}
        </div>
      </div>

      <div className="px-8 py-8 max-w-3xl mx-auto">

        {/* Error */}
        {error && (
          <div className="mb-5 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 font-['Lato'] text-sm">
            {error}
          </div>
        )}

        {/* Notification list */}
        <div ref={listRef}>
          {loading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-20 bg-white border border-ink/10 rounded-[14px] animate-pulse" />
              ))}
            </div>
          ) : notifications.length === 0 ? (
            <div className="text-center py-16">
              <Bell size={44} className="text-ink/20 mx-auto mb-3" />
              <p className="font-['Lato'] font-medium text-ink/40 mb-1">No notifications</p>
              <p className="font-['Lato'] text-sm text-ink/30">You're all caught up!</p>
            </div>
          ) : (
            <div className="space-y-2">
              {notifications.map((notif, i) => (
                <div
                  key={notif.id || i}
                  onClick={() => !notif.is_read && markRead(notif.id)}
                  className={`bg-white border border-ink/10 rounded-[14px] p-4 mb-2 flex items-start gap-3 cursor-pointer transition-all duration-150 hover:shadow-sm ${
                    !notif.is_read ? 'border-l-4 border-l-[#ff9500]' : ''
                  }`}
                  style={fadeUp(listInView, i * 40)}
                >
                  {/* Icon */}
                  <div className="w-8 h-8 rounded-full bg-cream flex items-center justify-center flex-shrink-0 mt-0.5">
                    <NotifIcon eventType={notif.event_type} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className={`font-['Lato'] text-sm ${!notif.is_read ? 'font-semibold text-ink' : 'font-medium text-ink'}`}>
                      {notif.title || notif.event_type || 'Notification'}
                    </p>
                    {notif.message && (
                      <p className="font-['Lato'] text-sm text-ink/60 mt-0.5 leading-snug">{notif.message}</p>
                    )}
                  </div>

                  {/* Timestamp */}
                  <div className="flex-shrink-0 ml-2">
                    <span className="font-['Lato'] text-xs text-ink/40">{fmtDate(notif.created_at)}</span>
                    {!notif.is_read && (
                      <div className="w-2 h-2 rounded-full bg-[#ff9500] ml-auto mt-1" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
