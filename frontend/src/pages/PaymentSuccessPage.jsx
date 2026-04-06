import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle, Loader } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const WS_URL = (userId) => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${wsProtocol}//${window.location.host}/ws/${userId}`
}
const TIMEOUT_MS = 30000

const FLOW = {
  loan_repayment: {
    event_type: 'loan.repaid',
    processingTitle: 'Processing Repayment',
    processingSubtitle: 'Please wait while we confirm your loan repayment…',
    doneTitle: 'Loan Repaid',
    doneSubtitle: 'Redirecting to your loans…',
    redirectTo: '/loans',
    cancelRedirectTo: '/loans',
  },
  wallet_topup: {
    event_type: 'wallet.credited',
    processingTitle: 'Processing Payment',
    processingSubtitle: 'Please wait while we confirm your top-up…',
    doneTitle: 'Wallet Credited',
    doneSubtitle: 'Redirecting to your wallet…',
    redirectTo: '/wallet',
    cancelRedirectTo: '/wallet',
  },
}

export default function PaymentSuccessPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState('processing') // 'processing' | 'done'

  const type = searchParams.get('type') || 'wallet_topup'
  const flow = FLOW[type] || FLOW.wallet_topup

  const wsRef = useRef(null)
  const timeoutRef = useRef(null)

  useEffect(() => {
    if (!user) {
      navigate(flow.redirectTo, { replace: true })
      return
    }

    // Fallback: redirect after 30s regardless
    timeoutRef.current = setTimeout(() => {
      navigate(flow.redirectTo, { replace: true })
    }, TIMEOUT_MS)

    // Connect to notification service WebSocket and wait for the relevant event
    try {
      const ws = new WebSocket(WS_URL(user.sub))
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.event_type === flow.event_type) {
            setStatus('done')
            clearTimeout(timeoutRef.current)
            setTimeout(() => navigate(flow.redirectTo, { replace: true }), 1500)
          }
        } catch {
          // ignore parse errors
        }
      }

      ws.onerror = () => {
        // WS failed — fallback timeout will still redirect
      }
    } catch {
      // ignore if WS unavailable
    }

    return () => {
      clearTimeout(timeoutRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [user, navigate, flow])

  return (
    <div className="min-h-screen bg-[#f5f5f0] flex items-center justify-center px-4">
      <div className="bg-white border border-ink/10 rounded-[20px] p-10 max-w-sm w-full text-center">
        {status === 'done' ? (
          <>
            <CheckCircle size={48} className="text-teal mx-auto mb-4" />
            <h1 className="font-['Lato'] font-semibold text-2xl text-ink mb-2">{flow.doneTitle}</h1>
            <p className="font-['Lato'] text-sm text-ink/60">{flow.doneSubtitle}</p>
          </>
        ) : (
          <>
            <Loader size={48} className="text-teal mx-auto mb-4 animate-spin" />
            <h1 className="font-['Lato'] font-semibold text-2xl text-ink mb-2">{flow.processingTitle}</h1>
            <p className="font-['Lato'] text-sm text-ink/60">{flow.processingSubtitle}</p>
          </>
        )}
      </div>
    </div>
  )
}
