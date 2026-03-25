import { useState, useEffect } from 'react'
import { ArrowUpRight, ArrowDownLeft, RefreshCw } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import { useInView } from '../hooks/useInView'

/* ── Animation helper ── */
function fadeUp(visible, delay = 0) {
  if (visible) return { animation: 'fadeUp 500ms cubic-bezier(0,0,0.2,1) both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(12px)' }
}

function fmt(n, showCents = true) {
  if (n == null) return '—'
  return Number(n).toLocaleString('en-SG', {
    minimumFractionDigits: showCents ? 2 : 0,
    maximumFractionDigits: showCents ? 2 : 0,
  })
}

function fmtDate(str) {
  if (!str) return '—'
  return new Date(str).toLocaleDateString('en-SG', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const QUICK_AMOUNTS = [100, 500, 1000, 5000]

export default function WalletPage() {
  const { user } = useAuth()

  const [balance, setBalance]               = useState(null)
  const [balanceLoading, setBalanceLoading] = useState(true)

  const [transactions, setTransactions]     = useState([])
  const [txLoading, setTxLoading]           = useState(true)
  const [txError, setTxError]               = useState('')

  const [selectedAmt, setSelectedAmt]       = useState(null)
  const [customAmt, setCustomAmt]           = useState('')
  const [topupLoading, setTopupLoading]     = useState(false)
  const [topupError, setTopupError]         = useState('')

  const [headerRef, headerInView] = useInView(0.05)
  const [topupRef, topupInView]   = useInView(0.05)
  const [txRef, txInView]         = useInView(0.05)

  useEffect(() => {
    if (!user) return
    loadBalance()
    loadTransactions()
  }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadBalance() {
    setBalanceLoading(true)
    try {
      const res = await api.get(`/wallet/balance?user_id=${user.sub}`)
      setBalance(res.data?.balance ?? res.data?.available_balance ?? null)
    } catch {
      setBalance(null)
    } finally {
      setBalanceLoading(false)
    }
  }

  async function loadTransactions() {
    setTxLoading(true)
    setTxError('')
    try {
      const res = await api.get(`/wallet/transactions?user_id=${user.sub}`)
      const data = res.data?.transactions || res.data || []
      setTransactions(Array.isArray(data) ? data : [])
    } catch (e) {
      setTxError(e.response?.data?.detail || e.message || 'Failed to load transactions.')
    } finally {
      setTxLoading(false)
    }
  }

  function getEffectiveAmount() {
    if (customAmt && Number(customAmt) > 0) return Number(customAmt)
    if (selectedAmt) return selectedAmt
    return null
  }

  async function handleTopup() {
    const amount = getEffectiveAmount()
    setTopupError('')
    if (!amount || amount <= 0) { setTopupError('Please select or enter a top-up amount.'); return }

    setTopupLoading(true)
    try {
      const res = await api.post('/wallet/topup', { amount })
      const url = res.data?.checkout_url || res.data?.url
      if (url) {
        window.location.href = url
      } else {
        setTopupError('No checkout URL returned from server.')
      }
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.message || e.message || 'Top-up failed.'
      setTopupError(msg)
    } finally {
      setTopupLoading(false)
    }
  }

  function txIcon(type) {
    if (!type) return <RefreshCw size={15} className="text-ink/40" />
    const t = type.toUpperCase()
    if (t.includes('TOPUP') || t.includes('CREDIT') || t.includes('DEPOSIT')) return <ArrowDownLeft size={15} className="text-[#3e9b00]" />
    return <ArrowUpRight size={15} className="text-red-500" />
  }

  return (
    <AppLayout>
      {/* Header strip with balance */}
      <div ref={headerRef} className="bg-teal px-8 py-10">
        <div className="max-w-4xl mx-auto flex items-end justify-between">
          <div>
            <p className="font-['Lato'] text-white/50 text-sm mb-1">Available Balance</p>
            {balanceLoading ? (
              <div className="h-14 w-56 bg-white/20 rounded-lg animate-pulse" />
            ) : (
              <p className="font-['Lato'] font-semibold text-[52px] text-white leading-none" style={fadeUp(headerInView, 100)}>
                <span className="text-white/50 text-2xl font-['Lato'] font-medium mr-2">SGD</span>
                {fmt(balance)}
              </p>
            )}
            <p className="font-['Lato'] text-white/40 text-xs mt-2">InvoiceFlow Wallet</p>
          </div>
        </div>
      </div>

      <div className="px-8 py-8 max-w-4xl mx-auto">

        {/* Top-up section */}
        <div ref={topupRef} style={fadeUp(topupInView, 0)} className="mb-6">
          <div className="bg-white border border-ink/10 rounded-[20px] p-8">
            <h2 className="font-['Lato'] font-semibold text-lg text-ink mb-5">Add Funds</h2>

            {topupError && (
              <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 font-['Lato'] text-sm">
                {topupError}
              </div>
            )}

            {/* Quick amounts */}
            <div className="flex flex-wrap gap-3 mb-4">
              {QUICK_AMOUNTS.map((amt) => (
                <button
                  key={amt}
                  type="button"
                  onClick={() => { setSelectedAmt(amt); setCustomAmt('') }}
                  className={`px-5 py-2.5 rounded-[22px] font-['Lato'] font-medium text-sm transition-colors duration-150 active:scale-[0.97] ${
                    selectedAmt === amt && !customAmt
                      ? 'bg-teal text-white'
                      : 'border border-ink/20 text-ink hover:border-ink/50'
                  }`}
                >
                  ${amt.toLocaleString()}
                </button>
              ))}
            </div>

            {/* Custom amount */}
            <div className="mb-5">
              <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                Or enter custom amount (SGD)
              </label>
              <div className="relative max-w-xs">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 font-['Lato'] text-sm text-ink/50">$</span>
                <input
                  type="number"
                  min="1"
                  step="0.01"
                  value={customAmt}
                  onChange={(e) => { setCustomAmt(e.target.value); setSelectedAmt(null) }}
                  placeholder="e.g. 250"
                  className="w-full border border-ink/30 rounded-[12px] pl-7 pr-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={handleTopup}
              disabled={topupLoading || !getEffectiveAmount()}
              className="bg-teal text-white rounded-[12px] px-6 py-2.5 font-['Lato'] font-semibold hover:opacity-90 active:scale-[0.97] active:opacity-100 transition-[transform,opacity] duration-100 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
            >
              {topupLoading ? 'Redirecting…' : 'Proceed to Stripe Checkout'}
            </button>
          </div>
        </div>

        {/* Transaction history */}
        <div ref={txRef} style={fadeUp(txInView, 0)}>
          <div className="bg-white border border-ink/10 rounded-[20px] overflow-hidden">
            <div className="px-6 py-5 border-b border-ink/10">
              <h2 className="font-['Lato'] font-semibold text-base text-ink">Transaction History</h2>
            </div>

            {txError && (
              <div className="mx-6 my-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 font-['Lato'] text-sm">
                {txError}
              </div>
            )}

            {txLoading ? (
              <div className="p-6 space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-12 bg-ink/5 rounded-lg animate-pulse" style={{ animationDelay: `${i * 80}ms` }} />
                ))}
              </div>
            ) : transactions.length === 0 ? (
              <div className="text-center py-12">
                <ArrowDownLeft size={36} className="text-ink/20 mx-auto mb-3" />
                <p className="font-['Lato'] text-sm text-ink/40">No transactions yet</p>
              </div>
            ) : (
              <div className="divide-y divide-ink/5">
                {transactions.map((tx, i) => (
                  <div
                    key={tx.id || i}
                    className="flex items-center justify-between px-6 py-4 hover:bg-cream transition-colors duration-100"
                    style={fadeUp(txInView, i * 40)}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-cream flex items-center justify-center flex-shrink-0">
                        {txIcon(tx.type || tx.transaction_type)}
                      </div>
                      <div>
                        <p className="font-['Lato'] text-sm font-medium text-ink">
                          {tx.description || tx.type || 'Transaction'}
                        </p>
                        <p className="font-['Lato'] text-xs text-ink/50">{fmtDate(tx.created_at)}</p>
                      </div>
                    </div>
                    <p className={`font-['Lato'] font-semibold text-sm ${Number(tx.amount) >= 0 ? 'text-[#3e9b00]' : 'text-red-600'}`}>
                      {Number(tx.amount) >= 0 ? '+' : ''}${fmt(Math.abs(tx.amount))}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
