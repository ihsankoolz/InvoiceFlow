import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, Loader } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const WS_URL = (userId) => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${wsProtocol}//${window.location.host}/ws/${userId}`
}
const TIMEOUT_MS = 30000

export default function PaymentSuccessPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const wsRef = useRef(null)
  const timeoutRef = useRef(null)
  const [status, setStatus] = useState('processing') // 'processing' | 'credited'

  useEffect(() => {
    if (!user) {
      navigate('/wallet', { replace: true })
      return
    }

    // Fallback: redirect after 30s regardless
    timeoutRef.current = setTimeout(() => {
      navigate('/wallet', { replace: true })
    }, TIMEOUT_MS)

    // Connect to notification service WebSocket
    try {
      const ws = new WebSocket(WS_URL(user.sub))
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.event_type === 'wallet.credited') {
            setStatus('credited')
            clearTimeout(timeoutRef.current)
            setTimeout(() => navigate('/wallet', { replace: true }), 1500)
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
  }, [user, navigate])

  return (
    <div className="min-h-screen bg-[#f5f5f0] flex items-center justify-center px-4">
      <div className="bg-white border border-ink/10 rounded-[20px] p-10 max-w-sm w-full text-center">
        {status === 'credited' ? (
          <>
            <CheckCircle size={48} className="text-teal mx-auto mb-4" />
            <h1 className="font-['Lato'] font-semibold text-2xl text-ink mb-2">Wallet Credited</h1>
            <p className="font-['Lato'] text-sm text-ink/60">Redirecting to your wallet…</p>
          </>
        ) : (
          <>
            <Loader size={48} className="text-teal mx-auto mb-4 animate-spin" />
            <h1 className="font-['Lato'] font-semibold text-2xl text-ink mb-2">Processing Payment</h1>
            <p className="font-['Lato'] text-sm text-ink/60">Please wait while we confirm your top-up…</p>
          </>
        )}
      </div>
    </div>
  )
}
