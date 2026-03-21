import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { BarChart2, ExternalLink, TrendingUp, DollarSign, CheckCircle } from 'lucide-react'
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
  if (visible) return { animation: 'bidsFadeUp 600ms ease both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(20px)' }
}

function fmt(n) {
  if (n == null) return '—'
  return `$${Number(n).toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtDate(str) {
  if (!str) return '—'
  return new Date(str).toLocaleDateString('en-SG', { day: '2-digit', month: 'short', year: 'numeric' })
}

function calcReturn(faceValue, bid) {
  const f = Number(faceValue)
  const b = Number(bid)
  if (!b || !f || b <= 0 || b >= f) return null
  return `+${((f - b) / b * 100).toFixed(1)}%`
}

const STATUS_TABS = ['ALL', 'PENDING', 'ACCEPTED', 'REJECTED']

export default function MyBidsPage() {
  const { user } = useAuth()

  const [bids, setBids]           = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')
  const [activeTab, setActiveTab] = useState('ALL')

  const [headerRef, headerInView] = useInView(0.05)
  const [statsRef, statsInView]   = useInView(0.05)
  const [tableRef, tableInView]   = useInView(0.05)

  useEffect(() => {
    if (!user) return
    async function load() {
      setLoading(true)
      setError('')
      try {
        const res = await api.get(`/bids?investor_id=${user.sub}`)
        const data = res.data?.bids || res.data || []
        setBids(Array.isArray(data) ? data : [])
      } catch (e) {
        setError(e.response?.data?.detail || e.message || 'Failed to load bids.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user])

  const totalBids     = bids.length
  const activeBids    = bids.filter((b) => b.status === 'PENDING').length
  const winningBids   = bids.filter((b) => b.status === 'ACCEPTED').length
  const totalInvested = bids.filter((b) => b.status === 'ACCEPTED').reduce((s, b) => s + Number(b.amount || 0), 0)

  const filtered = activeTab === 'ALL' ? bids : bids.filter((b) => b.status === activeTab)

  return (
    <AppLayout>
      <style>{`
        @keyframes bidsFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Header strip */}
      <div ref={headerRef} className="bg-teal px-8 py-10" style={fadeUp(headerInView, 0)}>
        <div className="max-w-6xl mx-auto">
          <h1 className="font-display font-semibold text-[42px] text-[#fff8ec] leading-tight">My Bids</h1>
          <p className="font-['Lato'] text-[#fff8ec]/60 text-sm mt-1">Track your marketplace bids and returns</p>
        </div>
      </div>

      <div className="px-8 py-8 max-w-6xl mx-auto">

        {/* Bento stats */}
        <div ref={statsRef} className="grid grid-cols-12 gap-4 mb-8">
          <div className="col-span-5 bg-cream rounded-[20px] p-7 flex flex-col justify-between" style={fadeUp(statsInView, 0)}>
            <div className="flex items-center gap-2 mb-2">
              <DollarSign size={16} className="text-ink/50" />
              <p className="font-['Lato'] text-sm text-ink/50">Total Invested</p>
            </div>
            {loading
              ? <div className="h-14 w-40 bg-ink/10 rounded-lg animate-pulse" />
              : <p className="font-display font-semibold text-[52px] text-ink leading-none">{fmt(totalInvested)}</p>
            }
            <p className="font-['Lato'] text-sm text-ink/40 mt-4">{winningBids} winning bid{winningBids !== 1 ? 's' : ''}</p>
          </div>

          <div className="col-span-3 bg-teal rounded-[20px] p-7 flex flex-col justify-between" style={fadeUp(statsInView, 60)}>
            <div className="flex items-center gap-2 mb-2">
              <BarChart2 size={16} className="text-[#fff8ec]/60" />
              <p className="font-['Lato'] text-sm text-[#fff8ec]/60">Active Bids</p>
            </div>
            {loading
              ? <div className="h-14 w-16 bg-white/20 rounded-lg animate-pulse" />
              : <p className="font-display font-semibold text-[52px] text-[#fff8ec] leading-none">{activeBids}</p>
            }
            <p className="font-['Lato'] text-sm text-[#fff8ec]/50 mt-4">of {totalBids} total</p>
          </div>

          <div className="col-span-4 bg-white border border-ink/10 rounded-[20px] p-7 flex flex-col justify-between" style={fadeUp(statsInView, 120)}>
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle size={16} className="text-ink/50" />
              <p className="font-['Lato'] text-sm text-ink/50">Won Auctions</p>
            </div>
            {loading
              ? <div className="h-14 w-16 bg-ink/5 rounded-lg animate-pulse" />
              : <p className="font-display font-semibold text-[52px] text-ink leading-none">{winningBids}</p>
            }
            <div className="flex items-center gap-2 mt-4">
              <TrendingUp size={14} className="text-[#3e9b00]" />
              <span className="font-['Lato'] text-sm text-[#3e9b00]">Returns in wallet on repayment</span>
            </div>
          </div>
        </div>

        {/* Status tabs */}
        <div style={fadeUp(headerInView, 80)} className="flex flex-wrap gap-2 mb-6">
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
        {error && (
          <div className="mb-5 px-4 py-3 rounded-[12px] bg-red-50 border border-red-200 text-red-700 font-['Lato'] text-sm">
            {error}
          </div>
        )}

        {/* Table card */}
        <div ref={tableRef} style={fadeUp(tableInView, 0)}>
          <div className="bg-white border border-ink/10 rounded-[20px] overflow-hidden">
            {loading ? (
              <div className="p-8 space-y-4">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-10 bg-ink/5 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-16 px-6">
                <BarChart2 size={44} className="text-ink/15 mx-auto mb-3" />
                <p className="font-['Lato'] font-medium text-ink/40 mb-1">No bids found</p>
                <p className="font-['Lato'] text-sm text-ink/30">
                  {activeTab === 'ALL' ? "You haven't placed any bids yet." : `No bids with status "${activeTab}".`}
                </p>
                {activeTab === 'ALL' && (
                  <Link
                    to="/marketplace"
                    className="inline-block mt-4 bg-teal text-white rounded-[22px] px-5 py-2.5 font-['Lato'] text-sm font-semibold hover:opacity-90 transition-opacity"
                  >
                    Browse Marketplace
                  </Link>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm font-['Lato']">
                  <thead>
                    <tr className="border-b border-ink/10 bg-cream/60">
                      <th className="text-left px-6 py-3 font-medium text-ink/50">Invoice Token</th>
                      <th className="text-right px-4 py-3 font-medium text-ink/50">Bid Amount</th>
                      <th className="text-right px-4 py-3 font-medium text-ink/50">Face Value</th>
                      <th className="text-right px-4 py-3 font-medium text-ink/50">Est. Return</th>
                      <th className="text-center px-4 py-3 font-medium text-ink/50">Status</th>
                      <th className="text-left px-4 py-3 font-medium text-ink/50">Deadline</th>
                      <th className="text-center px-6 py-3 font-medium text-ink/50">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((bid, i) => (
                      <tr
                        key={bid.id}
                        className="border-b border-ink/5 hover:bg-cream transition-colors"
                        style={fadeUp(tableInView, i * 40)}
                      >
                        <td className="px-6 py-3 font-medium text-ink">{bid.invoice_token || bid.listing_id || '—'}</td>
                        <td className="px-4 py-3 text-right text-ink font-medium">{fmt(bid.amount)}</td>
                        <td className="px-4 py-3 text-right text-ink/60">{fmt(bid.face_value)}</td>
                        <td className="px-4 py-3 text-right text-[#3e9b00] font-semibold">
                          {calcReturn(bid.face_value, bid.amount) || '—'}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <Badge status={bid.status} />
                        </td>
                        <td className="px-4 py-3 text-ink/50">{fmtDate(bid.deadline)}</td>
                        <td className="px-6 py-3 text-center">
                          {bid.status === 'PENDING' && bid.listing_id ? (
                            <Link
                              to={`/marketplace/${bid.listing_id}`}
                              className="inline-flex items-center gap-1 font-['Lato'] text-xs font-medium text-ink hover:text-teal transition-colors"
                            >
                              <ExternalLink size={13} />
                              View
                            </Link>
                          ) : (
                            <span className="text-ink/30 text-xs">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
