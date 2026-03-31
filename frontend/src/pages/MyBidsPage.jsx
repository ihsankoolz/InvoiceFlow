import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ShoppingCart, ExternalLink } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import Badge from '../components/ui/Badge'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import { useInView } from '../hooks/useInView'

/* ── Animation helper ── */
function fadeUp(visible, delay = 0) {
  if (visible) return { animation: 'fadeUp 500ms cubic-bezier(0,0,0.2,1) both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(12px)' }
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

function calcReturn(faceValue, bid) {
  const f = Number(faceValue)
  const b = Number(bid)
  if (!b || !f || b <= 0 || b >= f) return null
  return `+${((f - b) / b * 100).toFixed(1)}%`
}

function actionLabel(bid) {
  if (bid.status === 'PENDING' && bid.listing_id) return null // renders link
  if (bid.status === 'ACCEPTED') return 'Settled'
  if (bid.status === 'REJECTED') return 'Declined'
  return null
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
      {/* Header strip */}
      <div ref={headerRef} className="bg-teal px-8 py-10">
        <div className="max-w-6xl mx-auto">
          <h1 className="font-['Lato'] font-semibold text-[42px] text-white leading-tight">My Bids</h1>
          <p className="font-['Lato'] text-white/60 text-sm mt-1">Track your marketplace bids and returns</p>
        </div>
      </div>

      <div className="px-8 py-8 max-w-6xl mx-auto">

        {/* Stat cards */}
        <div ref={statsRef} className="grid grid-cols-4 gap-4 mb-8">
          <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3 hover:border-ink/20 transition-colors duration-150" style={fadeUp(statsInView, 0)}>
            <p className="font-['Lato'] text-xs text-ink/50 uppercase tracking-wider">Total Invested</p>
            {loading
              ? <div className="h-9 w-32 bg-ink/10 rounded animate-pulse" />
              : <p className="font-['Lato'] font-bold text-[28px] text-ink leading-none">{fmt(totalInvested)}</p>
            }
            <p className="font-['Lato'] text-xs text-ink/40 mt-auto">{winningBids} winning bid{winningBids !== 1 ? 's' : ''}</p>
          </div>

          <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3 hover:border-ink/20 transition-colors duration-150" style={fadeUp(statsInView, 60)}>
            <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Active Bids</p>
            {loading
              ? <div className="h-9 w-16 bg-ink/8 rounded animate-pulse" />
              : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{activeBids}</p>
            }
            <p className="font-['Lato'] text-xs text-ink/40 mt-auto">of {totalBids} total</p>
          </div>

          <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3 hover:border-ink/20 transition-colors duration-150" style={fadeUp(statsInView, 120)}>
            <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Won Auctions</p>
            {loading
              ? <div className="h-9 w-16 bg-ink/8 rounded animate-pulse" />
              : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{winningBids}</p>
            }
            <p className="font-['Lato'] text-xs text-ink/40 mt-auto">Returns credited on repayment</p>
          </div>

          <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3 hover:border-ink/20 transition-colors duration-150" style={fadeUp(statsInView, 180)}>
            <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Total Bids</p>
            {loading
              ? <div className="h-9 w-16 bg-ink/8 rounded animate-pulse" />
              : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{totalBids}</p>
            }
            <p className="font-['Lato'] text-xs text-ink/40 mt-auto">across all statuses</p>
          </div>
        </div>

        {/* Status tabs */}
        <div style={fadeUp(headerInView, 80)} className="flex flex-wrap gap-2 mb-6">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-[22px] font-['Lato'] text-sm font-medium transition-colors duration-150 active:scale-[0.97] ${
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
                  <div key={i} className="h-10 bg-ink/5 rounded-lg animate-pulse" style={{ animationDelay: `${i * 80}ms` }} />
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-16 px-6">
                <ShoppingCart size={44} className="text-ink/15 mx-auto mb-3" />
                <p className="font-['Lato'] font-medium text-ink/40 mb-1">No bids found</p>
                <p className="font-['Lato'] text-sm text-ink/30">
                  {activeTab === 'ALL' ? "You haven't placed any bids yet." : `No bids with status "${activeTab}".`}
                </p>
                {activeTab === 'ALL' && (
                  <Link
                    to="/marketplace"
                    className="inline-block mt-4 bg-teal text-white rounded-[22px] px-5 py-2.5 font-['Lato'] text-sm font-semibold hover:opacity-90 active:scale-[0.97] transition-[transform,opacity] duration-100"
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
                      <th className="text-left px-6 py-3 text-xs font-medium text-ink/50 uppercase tracking-wider">Invoice Token</th>
                      <th className="text-right px-4 py-3 text-xs font-medium text-ink/50 uppercase tracking-wider">Bid Amount</th>
                      <th className="text-right px-4 py-3 text-xs font-medium text-ink/50 uppercase tracking-wider">Face Value</th>
                      <th className="text-right px-4 py-3 text-xs font-medium text-ink/50 uppercase tracking-wider">Est. Return</th>
                      <th className="text-center px-4 py-3 text-xs font-medium text-ink/50 uppercase tracking-wider">Status</th>
                      <th className="text-left px-4 py-3 text-xs font-medium text-ink/50 uppercase tracking-wider">Deadline</th>
                      <th className="text-center px-6 py-3 text-xs font-medium text-ink/50 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((bid, i) => (
                      <tr
                        key={bid.id}
                        className="border-b border-ink/5 hover:bg-cream transition-colors duration-100"
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
                              className="inline-flex items-center gap-1 font-['Lato'] text-xs font-medium text-ink hover:text-teal hover:underline transition-colors duration-100"
                            >
                              <ExternalLink size={13} />
                              View
                            </Link>
                          ) : (
                            <span className="text-ink/30 text-xs">{actionLabel(bid) || '—'}</span>
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
