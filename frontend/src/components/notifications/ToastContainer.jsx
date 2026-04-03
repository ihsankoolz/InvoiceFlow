import { useNotifications } from '../../context/NotificationContext'
import { X, Bell, AlertTriangle, CheckCircle, DollarSign, Info } from 'lucide-react'

function ToastIcon({ eventType }) {
  const t = (eventType || '').toUpperCase()
  if (t.includes('BID') || t.includes('OUTBID') || t.includes('WALLET') || t.includes('TOPUP') || t.includes('CREDITED')) {
    return <DollarSign size={16} className="text-[#ff9500]" />
  }
  if (t.includes('ALERT') || t.includes('WARN') || t.includes('OVERDUE')) {
    return <AlertTriangle size={16} className="text-red-500" />
  }
  if (t.includes('SUCCESS') || t.includes('REPAID') || t.includes('FINANCED') || t.includes('ACCEPTED') || t.includes('WINNER')) {
    return <CheckCircle size={16} className="text-[#3e9b00]" />
  }
  if (t.includes('BELL') || t.includes('NOTIFICATION')) {
    return <Bell size={16} className="text-ink/50" />
  }
  return <Info size={16} className="text-ink/50" />
}

const EVENT_TITLES = {
  'wallet.credited':         'Wallet Credited',
  'wallet.topup':            'Wallet Top-Up',
  'bid.placed':              'New Bid on Your Invoice',
  'bid.confirmed':           'Bid Placed Successfully',
  'bid.outbid':              "You've Been Outbid",
  'auction.closing.warning': 'Auction Closing Soon',
  'auction.extended':        'Auction Deadline Extended',
  'auction.closed.winner':   'You Won the Auction!',
  'auction.closed.loser':    'Auction Ended',
  'auction.expired':         'Auction Expired',
  'invoice.listed':          'Invoice Listed',
  'invoice.rejected':        'Invoice Rejected',
  'loan.created':            'Loan Created',
  'loan.repaid':             'Loan Repaid',
  'loan.due':                'Loan Repayment Due',
  'loan.overdue':            'Loan Overdue',
}

export default function ToastContainer() {
  const { toasts, dismiss } = useNotifications()

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 items-end pointer-events-none">
      {toasts.map((toast) => {
        const title = toast.title || EVENT_TITLES[toast.event_type] || toast.event_type || 'Notification'
        const message = toast.message || toast.body || ''

        return (
          <div
            key={toast.id}
            className="pointer-events-auto w-80 bg-white border border-ink/10 rounded-[14px] shadow-lg p-4 flex items-start gap-3"
            style={{
              animation: toast.leaving
                ? 'toastOut 300ms cubic-bezier(0.4,0,1,1) both'
                : 'toastIn 300ms cubic-bezier(0,0,0.2,1) both',
            }}
          >
            <div className="w-7 h-7 rounded-full bg-[#fffcf7] border border-ink/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <ToastIcon eventType={toast.event_type} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-['Lato'] text-sm font-semibold text-ink leading-snug">{title}</p>
              {message && (
                <p className="font-['Lato'] text-xs text-ink/60 mt-0.5 leading-snug">{message}</p>
              )}
            </div>
            <button
              onClick={() => dismiss(toast.id)}
              className="flex-shrink-0 text-ink/30 hover:text-ink/60 transition-colors mt-0.5"
            >
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
