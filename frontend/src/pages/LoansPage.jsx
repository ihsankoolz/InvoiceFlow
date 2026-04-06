import { useState, useEffect, useRef } from 'react'
import { CreditCard, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import Badge from '../components/ui/Badge'
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
  if (visible) return { animation: 'loanFadeUp 600ms ease both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(20px)' }
}

function fmt(n) {
  if (n == null) return '—'
  return `$${Number(n).toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtDate(str) {
  if (!str) return '—'
  const utc = /Z|[+-]\d{2}:\d{2}$/.test(str) ? str : str + 'Z'
  return new Date(utc).toLocaleDateString('en-SG', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Singapore' })
}

const STATUS_TABS = ['ALL', 'ACTIVE', 'DUE', 'OVERDUE', 'REPAID']

export default function LoansPage() {
  const { user } = useAuth()

  const [loans, setLoans]         = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')
  const [activeTab, setActiveTab] = useState('ALL')
  const [repayingId, setRepayingId] = useState(null)
  const [repayError, setRepayError] = useState('')

  const [headerRef, headerInView] = useInView(0.05)
  const [gridRef, gridInView]     = useInView(0.05)

  useEffect(() => {
    if (!user) return
    async function load() {
      setLoading(true)
      setError('')
      try {
        const res = await api.get(`/loans?seller_id=${user.sub}`)
        const data = res.data?.loans || res.data || []
        setLoans(Array.isArray(data) ? data : [])
      } catch (e) {
        setError(e.response?.data?.detail || e.message || 'Failed to load loans.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user])

  async function handleRepay(loanId) {
    setRepayError('')
    setRepayingId(loanId)
    try {
      const res = await api.post(`/loans/${loanId}/repay`)
      const url = res.data?.checkout_url || res.data?.url
      if (url) {
        window.location.href = url
      } else {
        setRepayError('No checkout URL returned.')
      }
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.message || e.message || 'Repayment failed.'
      setRepayError(msg)
    } finally {
      setRepayingId(null)
    }
  }

  const filtered = activeTab === 'ALL' ? loans : loans.filter((l) => l.status === activeTab)

  function loanIcon(status) {
    switch (status) {
      case 'REPAID':  return <CheckCircle size={20} className="text-[#3e9b00]" />
      case 'OVERDUE': return <AlertTriangle size={20} className="text-red-500" />
      case 'DUE':     return <Clock size={20} className="text-[#ff9500]" />
      default:        return <CreditCard size={20} className="text-ink/40" />
    }
  }

  return (
    <AppLayout>
      <style>{`
        @keyframes loanFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Header strip */}
      <div ref={headerRef} className="bg-teal px-8 py-10" style={fadeUp(headerInView, 0)}>
        <div className="max-w-6xl mx-auto">
          <h1 className="font-['Lato'] font-semibold text-[42px] text-white leading-tight">My Loans</h1>
          <p className="font-['Lato'] text-white/60 text-sm mt-1">Manage your active loans and repayments</p>
        </div>
      </div>

      <div className="px-8 py-8 max-w-6xl mx-auto">
        {/* Status tabs */}
        <div style={fadeUp(headerInView, 60)} className="flex flex-wrap gap-2 mb-6">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-[22px] font-['Lato'] text-sm font-medium transition-colors duration-150 ${
                activeTab === tab
                  ? 'bg-teal text-white'
                  : 'border border-ink/20 text-ink/70 hover:border-ink/50 hover:text-ink bg-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Error */}
        {(error || repayError) && (
          <div className="mb-5 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 font-['Lato'] text-sm">
            {error || repayError}
          </div>
        )}

        {/* Loans grid */}
        <div ref={gridRef}>
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="bg-white border border-ink/10 rounded-[20px] p-6 space-y-3">
                  {[80, 60, 40, 80].map((w, j) => (
                    <div key={j} className="h-4 bg-ink/5 rounded animate-pulse" style={{ width: `${w}%` }} />
                  ))}
                </div>
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-16">
              <CreditCard size={44} className="text-ink/20 mx-auto mb-3" />
              <p className="font-['Lato'] font-medium text-ink/40 mb-1">No loans found</p>
              <p className="font-['Lato'] text-sm text-ink/30">
                {activeTab === 'ALL' ? "You don't have any active loans." : `No loans with status "${activeTab}".`}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((loan, i) => {
                const isOverdue = loan.status === 'OVERDUE'
                const isDue     = loan.status === 'DUE'

                return (
                  <div
                    key={loan.id}
                    className={`bg-white rounded-[20px] p-6 flex flex-col gap-4 ${
                      isOverdue
                        ? 'border-2 border-red-400'
                        : 'border border-ink/10'
                    }`}
                    style={fadeUp(gridInView, i * 60)}
                  >
                    {/* Top */}
                    <div className="flex items-start justify-between">
                      {loanIcon(loan.status)}
                      <Badge status={loan.status} />
                    </div>

                    {/* Invoice token */}
                    <div>
                      <p className="font-['Lato'] text-xs text-ink/50 mb-0.5">Invoice</p>
                      <p className="font-['Lato'] font-semibold text-sm text-ink">
                        {loan.invoice_token || loan.invoice_id || loan.id}
                      </p>
                    </div>

                    <div className="h-px bg-ink/10" />

                    {/* Amount */}
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-sm font-['Lato']">
                        <span className="text-ink/50">Amount</span>
                        <span className="font-semibold text-ink">{fmt(loan.principal)}</span>
                      </div>
                      <div className="flex justify-between text-sm font-['Lato']">
                        <span className="text-ink/50">Due date</span>
                        <span className="text-ink">{fmtDate(loan.due_date)}</span>
                      </div>
                      {isOverdue && loan.penalty_amount && (
                        <div className="flex justify-between text-sm font-['Lato']">
                          <span className="text-red-500">Penalty</span>
                          <span className="font-semibold text-red-600">{fmt(loan.penalty_amount)}</span>
                        </div>
                      )}
                    </div>

                    {/* Overdue note */}
                    {isOverdue && (
                      <div className="px-3 py-2 rounded-lg bg-red-50 border border-red-100">
                        <p className="font-['Lato'] text-xs text-red-600">
                          This loan is overdue. A penalty may apply.
                        </p>
                      </div>
                    )}

                    {/* Repay button (DUE or OVERDUE) */}
                    {(isDue || isOverdue) && (
                      <button
                        onClick={() => handleRepay(loan.id)}
                        disabled={repayingId === loan.id}
                        className={`w-full rounded-lg px-4 py-2.5 font-['Lato'] font-semibold text-sm transition-colors duration-200 disabled:opacity-60 disabled:cursor-not-allowed ${
                          isOverdue
                            ? 'bg-red-600 text-white hover:bg-red-700'
                            : 'bg-teal text-white hover:opacity-90'
                        }`}
                      >
                        {repayingId === loan.id ? 'Redirecting…' : 'Repay Now'}
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
