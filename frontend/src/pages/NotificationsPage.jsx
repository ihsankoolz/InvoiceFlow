import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, AlertTriangle, CheckCircle, DollarSign, Info } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import { useInView } from '../hooks/useInView'

/* ── Animation helper ── */
function fadeUp(visible, delay = 0) {
  if (visible) return { animation: 'fadeUp 500ms cubic-bezier(0,0,0.2,1) both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(12px)' }
}

function fmtDate(str) {
  if (!str) return ''
  const d = new Date(str)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return d.toLocaleDateString('en-SG', { day: '2-digit', month: 'short', timeZone: 'Asia/Singapore' })
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

const EVENT_TITLES = {
  'wallet.credited':          'Wallet Credited',
  'wallet.topup':             'Wallet Top-Up',
  'bid.placed':               'New Bid on Your Invoice',
  'bid.confirmed':            'Bid Placed Successfully',
  'bid.outbid':               "You've Been Outbid",
  'auction.closing.warning':  'Auction Closing Soon',
  'auction.extended':         'Auction Deadline Extended',
  'auction.closed.winner':    'You Won the Auction!',
  'auction.closed.loser':     'Auction Ended',
  'auction.expired':          'Auction Expired',
  'invoice.listed':           'Invoice Listed',
  'invoice.rejected':         'Invoice Rejected',
  'loan.created':             'Loan Created',
  'loan.repaid':              'Loan Repaid',
  'loan.due':                 'Loan Repayment Due',
  'loan.overdue':             'Loan Overdue',
}

function getNotifTitle(notif) {
  return notif.title || EVENT_TITLES[notif.event_type] || notif.event_type || 'Notification'
}

function getNotifLink(eventType, role) {
  const t = (eventType || '').toUpperCase()
  const isSeller = role !== 'INVESTOR'
  if (t.includes('WALLET') || t.includes('TOPUP') || t.includes('CREDITED')) return '/wallet'
  if (t.includes('BID') || t.includes('OUTBID')) return isSeller ? null : '/bids'
  if (t.includes('LOAN') || t.includes('REPAID') || t.includes('FINANCED')) return '/loans'
  if (t.includes('INVOICE') || t.includes('LISTING')) return isSeller ? '/invoices' : '/marketplace'
  return null
}

export default function NotificationsPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [notifications, setNotifications] = useState([])
  const [loading, setLoading]             = useState(true)
  const [error, setError]                 = useState('')

  const wsRef = useRef(null)

  const [headerRef] = useInView(0.05)
  const [listRef, listInView]     = useInView(0.05)

  useEffect(() => {
    if (!user) return
    loadNotifications()

    let cancelled = false
    try {
      const ws = new WebSocket(`ws://localhost:5005/ws/${user.sub}`)
      wsRef.current = ws

      ws.onopen = () => {
        if (cancelled) ws.close()
      }
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          const newNotif = {
            id: msg.id || Date.now(),
            title: msg.title || msg.event_type || 'Notification',
            message: msg.message || msg.body || '',
            event_type: msg.event_type || 'NOTIFICATION',
            created_at: msg.created_at || new Date().toISOString(),
            is_read: false,
            isNew: true,
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

    return () => {
      cancelled = true
      const ws = wsRef.current
      wsRef.current = null
      if (ws && ws.readyState === WebSocket.OPEN) ws.close()
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


  async function markRead(id) {
    setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, is_read: true } : n))
    try { await api.patch(`/notifications/${id}/read`) } catch { /* best effort */ }
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length

  return (
    <AppLayout>
      {/* Header strip */}
      <div ref={headerRef} className="bg-teal px-8 py-10">
        <div className="max-w-3xl mx-auto flex items-end justify-between">
          <div>
            <h1 className="font-['Lato'] font-semibold text-[42px] text-white leading-tight flex items-center gap-3">
              Notifications
              {unreadCount > 0 && (
                <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-[#ff9500] text-white font-['Lato'] text-xs font-bold">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </h1>
            <p className="font-['Lato'] text-white/60 text-sm mt-1">Your recent activity and alerts</p>
          </div>
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
                <div key={i} className="h-20 bg-white border border-ink/10 rounded-[14px] animate-pulse" style={{ animationDelay: `${i * 80}ms` }} />
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
                  onClick={() => { markRead(notif.id); const link = getNotifLink(notif.event_type, user?.role); if (link) navigate(link) }}
                  className={`bg-white border border-ink/10 rounded-[14px] p-4 flex items-start gap-3 cursor-pointer hover:bg-cream/60 transition-[background-color,box-shadow,border-left-width,border-color] duration-200 hover:shadow-sm ${!notif.is_read ? 'border-l-4' : ''}`}
                  style={{
                    ...fadeUp(listInView, i * 40),
                    ...(notif.isNew ? { animation: 'fadeUp 300ms cubic-bezier(0,0,0.2,1) both' } : {}),
                    ...(!notif.is_read ? { borderLeftColor: '#ff9500' } : {}),
                  }}
                >
                  {/* Icon */}
                  <div className="w-8 h-8 rounded-full bg-cream flex items-center justify-center flex-shrink-0 mt-0.5">
                    <NotifIcon eventType={notif.event_type} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className={`font-['Lato'] text-sm ${!notif.is_read ? 'font-semibold text-ink' : 'font-medium text-ink'}`}>
                      {getNotifTitle(notif)}
                    </p>
                    {notif.message && (
                      <p className="font-['Lato'] text-sm text-ink/60 mt-0.5 leading-snug">{notif.message}</p>
                    )}
                  </div>

                  {/* Timestamp + unread dot */}
                  <div className="flex-shrink-0 ml-2 flex flex-col items-end gap-1">
                    <span className="font-['Lato'] text-xs text-ink/40">{fmtDate(notif.created_at)}</span>
                    <div
                      className="w-2 h-2 rounded-full bg-[#ff9500] transition-opacity duration-300"
                      style={{ opacity: notif.is_read ? 0 : 1 }}
                    />
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
