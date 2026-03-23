import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { PlusCircle, FileText, ShoppingCart, ArrowRight } from 'lucide-react'
import iconArrow from '../assets/icons/8.svg'
import DashboardLayout from '../components/layout/DashboardLayout'
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
  if (visible) return { animation: 'dashFadeUp 600ms ease both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(20px)' }
}

/* ── Format currency ── */
function fmt(n) {
  if (n == null) return '—'
  return `$${Number(n).toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}


export default function DashboardPage() {
  const { user } = useAuth()
  const [statsRef, statsInView] = useInView(0.05)
  const [bodyRef,  bodyInView]  = useInView(0.05)

  const isSeller = user?.role === 'SELLER'

  /* ── Seller state ── */
  const [sellerStats, setSellerStats]         = useState(null)
  const [recentInvoices, setRecentInvoices]   = useState([])
  const [invoicesLoading, setInvoicesLoading] = useState(false)

  /* ── Investor state ── */
  const [investorStats, setInvestorStats] = useState(null)
  const [recentBids, setRecentBids]       = useState([])
  const [bidsLoading, setBidsLoading]     = useState(false)

  const [statsLoading, setStatsLoading] = useState(true)

  useEffect(() => {
    if (!user) return

    async function loadSellerData() {
      setStatsLoading(true)
      setInvoicesLoading(true)
      try {
        const [invoicesRes, walletRes, loansRes] = await Promise.allSettled([
          api.get(`/invoices?seller_id=${user.sub}`),
          api.get('/wallet/balance'),
          api.get(`/loans?seller_id=${user.sub}`),
        ])
        const invoices = invoicesRes.status === 'fulfilled' ? (invoicesRes.value.data?.invoices || invoicesRes.value.data || []) : []
        const wallet   = walletRes.status === 'fulfilled' ? walletRes.value.data : null
        const loans    = loansRes.status === 'fulfilled' ? (loansRes.value.data?.loans || loansRes.value.data || []) : []
        const activeListings = invoices.filter((i) => i.status === 'LISTED').length
        const totalFinanced  = invoices.filter((i) => ['FINANCED', 'ACCEPTED'].includes(i.status)).reduce((s, i) => s + Number(i.face_value || 0), 0)
        const activeLoans    = loans.filter((l) => l.status === 'ACTIVE' || l.status === 'DUE').length
        setSellerStats({ activeListings, totalFinanced, activeLoans, walletBalance: wallet?.balance ?? wallet?.available_balance ?? null })
        setRecentInvoices(invoices.slice(0, 5))
      } catch {
        setSellerStats({ activeListings: 0, totalFinanced: 0, activeLoans: 0, walletBalance: null })
        setRecentInvoices([])
      } finally {
        setStatsLoading(false)
        setInvoicesLoading(false)
      }
    }

    async function loadInvestorData() {
      setStatsLoading(true)
      setBidsLoading(true)
      try {
        const [bidsRes, walletRes] = await Promise.allSettled([
          api.get(`/bids?investor_id=${user.sub}`),
          api.get('/wallet/balance'),
        ])
        const bids   = bidsRes.status === 'fulfilled' ? (bidsRes.value.data?.bids || bidsRes.value.data || []) : []
        const wallet = walletRes.status === 'fulfilled' ? walletRes.value.data : null
        const activeBids    = bids.filter((b) => b.status === 'PENDING').length
        const totalInvested = bids.filter((b) => b.status === 'ACCEPTED').reduce((s, b) => s + Number(b.amount || 0), 0)
        setInvestorStats({ walletBalance: wallet?.balance ?? wallet?.available_balance ?? null, activeBids, totalInvested, activeReturns: bids.filter((b) => b.status === 'ACCEPTED').length })
        setRecentBids(bids.slice(0, 5))
      } catch {
        setInvestorStats({ walletBalance: null, activeBids: 0, totalInvested: 0, activeReturns: 0 })
        setRecentBids([])
      } finally {
        setStatsLoading(false)
        setBidsLoading(false)
      }
    }

    if (isSeller) loadSellerData()
    else loadInvestorData()
  }, [user, isSeller])

  return (
    <DashboardLayout>
      <style>{`
        @keyframes dashFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div className="px-10 py-10 max-w-6xl mx-auto">

        {/* ── Greeting ── */}
        <div className="mb-10" style={fadeUp(statsInView, 0)}>
          <h1 className="font-['Lato'] font-bold text-[28px] text-ink leading-tight">
            Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}, {user?.full_name?.split(' ')[0] || 'there'}
          </h1>
          <p className="font-['Lato'] text-sm text-ink/40 mt-1">
            {isSeller ? "Here's an overview of your listings and loans." : "Here's an overview of your portfolio."}
          </p>
        </div>

        {/* ── Stat cards ── */}
        <div ref={statsRef} className="grid grid-cols-4 gap-4 mb-10">
          {isSeller ? (
            <>
              {/* Wallet — teal */}
              <div className="bg-teal rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 0)}>
                <p className="font-['Lato'] text-xs text-white/60 uppercase tracking-wider">Wallet Balance</p>
                {statsLoading
                  ? <div className="h-9 w-32 bg-white/20 rounded animate-pulse" />
                  : <p className="font-['Lato'] font-bold text-[28px] text-white leading-none">{fmt(sellerStats?.walletBalance)}</p>
                }
                <Link to="/wallet" className="font-['Lato'] text-xs text-white/60 hover:text-white transition-colors flex items-center gap-1 mt-auto">
                  Manage <ArrowRight size={11} />
                </Link>
              </div>
              <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 60)}>
                <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Active Listings</p>
                {statsLoading
                  ? <div className="h-9 w-16 bg-ink/8 rounded animate-pulse" />
                  : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{sellerStats?.activeListings ?? 0}</p>
                }
                <Link to="/invoices" className="font-['Lato'] text-xs text-ink/40 hover:text-ink transition-colors flex items-center gap-1 mt-auto">
                  View all <ArrowRight size={11} />
                </Link>
              </div>
              <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 120)}>
                <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Total Financed</p>
                {statsLoading
                  ? <div className="h-9 w-32 bg-ink/8 rounded animate-pulse" />
                  : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{fmt(sellerStats?.totalFinanced)}</p>
                }
                <p className="font-['Lato'] text-xs text-ink/40 mt-auto">across financed invoices</p>
              </div>
              <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 180)}>
                <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Active Loans</p>
                {statsLoading
                  ? <div className="h-9 w-16 bg-ink/8 rounded animate-pulse" />
                  : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{sellerStats?.activeLoans ?? 0}</p>
                }
                <Link to="/loans" className="font-['Lato'] text-xs text-ink/40 hover:text-ink transition-colors flex items-center gap-1 mt-auto">
                  View loans <ArrowRight size={11} />
                </Link>
              </div>
            </>
          ) : (
            <>
              {/* Wallet — teal */}
              <div className="bg-teal rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 0)}>
                <p className="font-['Lato'] text-xs text-white/60 uppercase tracking-wider">Wallet Balance</p>
                {statsLoading
                  ? <div className="h-9 w-32 bg-white/20 rounded animate-pulse" />
                  : <p className="font-['Lato'] font-bold text-[28px] text-white leading-none">{fmt(investorStats?.walletBalance)}</p>
                }
                <Link to="/wallet" className="inline-flex items-center gap-2 mt-auto bg-white text-teal font-['Lato'] font-semibold text-sm px-5 py-2 rounded-[22px] hover:opacity-90 transition-opacity w-fit">
                  <img src={iconArrow} alt="" className="w-4 h-4" />
                  Top up
                </Link>
              </div>
              <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 60)}>
                <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Active Bids</p>
                {statsLoading
                  ? <div className="h-9 w-16 bg-ink/8 rounded animate-pulse" />
                  : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{investorStats?.activeBids ?? 0}</p>
                }
                <Link to="/bids" className="inline-flex items-center gap-2 mt-auto bg-teal text-white font-['Lato'] font-semibold text-sm px-5 py-2 rounded-[22px] hover:opacity-90 transition-opacity w-fit">
                  <img src={iconArrow} alt="" className="w-4 h-4 brightness-0 invert" />
                  View bids
                </Link>
              </div>
              <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 120)}>
                <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Total Invested</p>
                {statsLoading
                  ? <div className="h-9 w-32 bg-ink/8 rounded animate-pulse" />
                  : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{fmt(investorStats?.totalInvested)}</p>
                }
                <p className="font-['Lato'] text-xs text-ink/40 mt-auto">across won auctions</p>
              </div>
              <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 180)}>
                <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Active Returns</p>
                {statsLoading
                  ? <div className="h-9 w-16 bg-ink/8 rounded animate-pulse" />
                  : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{investorStats?.activeReturns ?? 0}</p>
                }
                <p className="font-['Lato'] text-xs text-ink/40 mt-auto">pending repayment</p>
              </div>
            </>
          )}
        </div>

        {/* ── Table section ── */}
        <div ref={bodyRef}>
          {isSeller ? (
            <div style={fadeUp(bodyInView, 0)}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-['Lato'] font-semibold text-base text-ink">Recent Invoices</h2>
                <Link to="/invoices" className="font-['Lato'] text-sm text-ink/40 hover:text-ink transition-colors flex items-center gap-1">
                  View all <ArrowRight size={13} />
                </Link>
              </div>
              {invoicesLoading ? (
                <div className="space-y-3">
                  {[...Array(4)].map((_, i) => <div key={i} className="h-10 bg-ink/5 rounded-lg animate-pulse" />)}
                </div>
              ) : recentInvoices.length === 0 ? (
                <div className="text-center py-16 border border-ink/8 rounded-[16px]">
                  <FileText size={36} className="text-ink/15 mx-auto mb-3" />
                  <p className="font-['Lato'] text-sm text-ink/40 mb-4">No invoices yet</p>
                  <Link
                    to="/invoices/new"
                    className="inline-flex items-center gap-2 bg-teal text-white rounded-[22px] px-5 py-2 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity"
                  >
                    <PlusCircle size={15} /> List your first invoice
                  </Link>
                </div>
              ) : (
                <table className="w-full text-sm font-['Lato']">
                  <thead>
                    <tr className="border-b border-ink/10">
                      <th className="text-left py-3 font-medium text-ink/40 text-xs uppercase tracking-wider">Token</th>
                      <th className="text-left py-3 font-medium text-ink/40 text-xs uppercase tracking-wider">Debtor</th>
                      <th className="text-right py-3 font-medium text-ink/40 text-xs uppercase tracking-wider">Face Value</th>
                      <th className="text-center py-3 font-medium text-ink/40 text-xs uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentInvoices.map((inv) => (
                      <tr key={inv.id} className="border-b border-ink/5 hover:bg-ink/[0.02] transition-colors">
                        <td className="py-4 text-ink font-medium">{inv.invoice_token || inv.id}</td>
                        <td className="py-4 text-ink/60">{inv.debtor_name || '—'}</td>
                        <td className="py-4 text-right text-ink font-medium">{fmt(inv.face_value)}</td>
                        <td className="py-4 text-center"><Badge status={inv.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ) : (
            <div style={fadeUp(bodyInView, 0)}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-['Lato'] font-semibold text-base text-ink">Recent Bids</h2>
                <Link to="/bids" className="font-['Lato'] text-sm text-ink/40 hover:text-ink transition-colors flex items-center gap-1">
                  View all <ArrowRight size={13} />
                </Link>
              </div>
              {bidsLoading ? (
                <div className="space-y-3">
                  {[...Array(4)].map((_, i) => <div key={i} className="h-10 bg-ink/5 rounded-lg animate-pulse" />)}
                </div>
              ) : recentBids.length === 0 ? (
                <div className="text-center py-16 border border-ink/8 rounded-[16px]">
                  <ShoppingCart size={36} className="text-ink/15 mx-auto mb-3" />
                  <p className="font-['Lato'] text-sm text-ink/40 mb-4">No bids placed yet</p>
                  <Link
                    to="/marketplace"
                    className="inline-flex items-center gap-2 bg-teal text-white rounded-[22px] px-5 py-2 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity"
                  >
                    <ShoppingCart size={15} /> Browse the marketplace
                  </Link>
                </div>
              ) : (
                <table className="w-full text-sm font-['Lato']">
                  <thead>
                    <tr className="border-b border-ink/10">
                      <th className="text-left py-3 font-medium text-ink/40 text-xs uppercase tracking-wider">Invoice</th>
                      <th className="text-right py-3 font-medium text-ink/40 text-xs uppercase tracking-wider">Bid Amount</th>
                      <th className="text-center py-3 font-medium text-ink/40 text-xs uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentBids.map((bid) => (
                      <tr key={bid.id} className="border-b border-ink/5 hover:bg-ink/[0.02] transition-colors">
                        <td className="py-4 text-ink font-medium">{bid.invoice_token || bid.invoice_id || bid.id}</td>
                        <td className="py-4 text-right text-ink font-semibold">{fmt(bid.amount)}</td>
                        <td className="py-4 text-center"><Badge status={bid.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
