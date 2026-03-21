import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { PlusCircle, FileText, ShoppingCart, Wallet, TrendingUp, DollarSign, BarChart2, CreditCard, ArrowRight } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import Badge from '../components/ui/Badge'
import api from '../api/axios'
import { fetchListings } from '../api/marketplace'
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

function Skeleton({ className = '' }) {
  return <div className={`bg-white/20 rounded-lg animate-pulse ${className}`} />
}

function SkeletonDark({ className = '' }) {
  return <div className={`bg-ink/5 rounded-lg animate-pulse ${className}`} />
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [heroRef,  heroInView]  = useInView(0.05)
  const [statsRef, statsInView] = useInView(0.05)
  const [bodyRef,  bodyInView]  = useInView(0.05)

  const isSeller = user?.role === 'SELLER'

  /* ── Seller state ── */
  const [sellerStats, setSellerStats]         = useState(null)
  const [recentInvoices, setRecentInvoices]   = useState([])
  const [invoicesLoading, setInvoicesLoading] = useState(false)

  /* ── Investor state ── */
  const [investorStats, setInvestorStats]     = useState(null)
  const [featuredListings, setFeaturedListings] = useState([])
  const [listingsLoading, setListingsLoading] = useState(false)

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
      setListingsLoading(true)
      try {
        const [bidsRes, walletRes, listingsRes] = await Promise.allSettled([
          api.get(`/bids?investor_id=${user.sub}`),
          api.get('/wallet/balance'),
          fetchListings({}),
        ])
        const bids     = bidsRes.status === 'fulfilled' ? (bidsRes.value.data?.bids || bidsRes.value.data || []) : []
        const wallet   = walletRes.status === 'fulfilled' ? walletRes.value.data : null
        const listings = listingsRes.status === 'fulfilled' ? listingsRes.value : []
        const activeBids    = bids.filter((b) => b.status === 'PENDING').length
        const totalInvested = bids.filter((b) => b.status === 'ACCEPTED').reduce((s, b) => s + Number(b.amount || 0), 0)
        setInvestorStats({ walletBalance: wallet?.balance ?? wallet?.available_balance ?? null, activeBids, totalInvested, activeReturns: bids.filter((b) => b.status === 'ACCEPTED').length })
        setFeaturedListings(Array.isArray(listings) ? listings.slice(0, 3) : [])
      } catch {
        setInvestorStats({ walletBalance: null, activeBids: 0, totalInvested: 0, activeReturns: 0 })
        setFeaturedListings([])
      } finally {
        setStatsLoading(false)
        setListingsLoading(false)
      }
    }

    if (isSeller) loadSellerData()
    else loadInvestorData()
  }, [user, isSeller])

  return (
    <AppLayout>
      <style>{`
        @keyframes dashFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* ── Welcome strip ── */}
      <div ref={heroRef} className="bg-teal px-8 py-10" style={fadeUp(heroInView, 0)}>
        <div className="max-w-6xl mx-auto flex items-end justify-between">
          <div>
            <p className="font-['Lato'] text-[#fff8ec]/60 text-sm mb-1">
              {isSeller ? 'Seller Dashboard' : 'Investor Dashboard'}
            </p>
            <h1 className="font-display font-semibold text-[42px] text-[#fff8ec] leading-tight">
              Welcome back, {user?.full_name?.split(' ')[0] || 'there'}
            </h1>
          </div>
          {isSeller ? (
            <Link
              to="/invoices/new"
              className="flex items-center gap-2 bg-[#fff8ec] text-teal rounded-[22px] px-6 py-3 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity"
            >
              <PlusCircle size={16} />
              List Invoice
            </Link>
          ) : (
            <Link
              to="/marketplace"
              className="flex items-center gap-2 bg-[#fff8ec] text-teal rounded-[22px] px-6 py-3 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity"
            >
              <ShoppingCart size={16} />
              Browse Market
            </Link>
          )}
        </div>
      </div>

      <div className="px-8 py-8 max-w-6xl mx-auto">

        {/* ── Bento stats ── */}
        {isSeller ? (
          <div ref={statsRef} className="grid grid-cols-12 gap-4 mb-8">
            {/* Wallet — wide cream card */}
            <div className="col-span-5 bg-cream rounded-[20px] p-7 flex flex-col justify-between" style={fadeUp(statsInView, 0)}>
              <div className="flex items-center gap-2 mb-2">
                <Wallet size={16} className="text-ink/50" />
                <p className="font-['Lato'] text-sm text-ink/50">Wallet Balance</p>
              </div>
              {statsLoading
                ? <div className="h-14 w-40 bg-ink/10 rounded-lg animate-pulse" />
                : <p className="font-display font-semibold text-[52px] text-ink leading-none">
                    {fmt(sellerStats?.walletBalance)}
                  </p>
              }
              <Link to="/wallet" className="flex items-center gap-1 font-['Lato'] text-sm text-ink/60 hover:text-ink transition-colors mt-4">
                Manage wallet <ArrowRight size={14} />
              </Link>
            </div>

            {/* Active Listings */}
            <div className="col-span-3 bg-teal rounded-[20px] p-7 flex flex-col justify-between" style={fadeUp(statsInView, 60)}>
              <div className="flex items-center gap-2 mb-2">
                <FileText size={16} className="text-[#fff8ec]/60" />
                <p className="font-['Lato'] text-sm text-[#fff8ec]/60">Active Listings</p>
              </div>
              {statsLoading
                ? <Skeleton className="h-14 w-16" />
                : <p className="font-display font-semibold text-[52px] text-[#fff8ec] leading-none">
                    {sellerStats?.activeListings ?? 0}
                  </p>
              }
              <Link to="/invoices" className="flex items-center gap-1 font-['Lato'] text-sm text-[#fff8ec]/60 hover:text-[#fff8ec] transition-colors mt-4">
                View all <ArrowRight size={14} />
              </Link>
            </div>

            {/* Total Financed */}
            <div className="col-span-4 bg-white border border-ink/10 rounded-[20px] p-7 flex flex-col justify-between" style={fadeUp(statsInView, 120)}>
              <div className="flex items-center gap-2 mb-2">
                <DollarSign size={16} className="text-ink/50" />
                <p className="font-['Lato'] text-sm text-ink/50">Total Financed</p>
              </div>
              {statsLoading
                ? <SkeletonDark className="h-14 w-36" />
                : <p className="font-display font-semibold text-[40px] text-ink leading-none">
                    {fmt(sellerStats?.totalFinanced)}
                  </p>
              }
              <div className="flex items-center gap-2 mt-4">
                <CreditCard size={14} className="text-ink/40" />
                <span className="font-['Lato'] text-sm text-ink/50">
                  {statsLoading ? '—' : sellerStats?.activeLoans ?? 0} active loan{sellerStats?.activeLoans !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div ref={statsRef} className="grid grid-cols-12 gap-4 mb-8">
            {/* Wallet — wide cream */}
            <div className="col-span-5 bg-cream rounded-[20px] p-7 flex flex-col justify-between" style={fadeUp(statsInView, 0)}>
              <div className="flex items-center gap-2 mb-2">
                <Wallet size={16} className="text-ink/50" />
                <p className="font-['Lato'] text-sm text-ink/50">Wallet Balance</p>
              </div>
              {statsLoading
                ? <div className="h-14 w-40 bg-ink/10 rounded-lg animate-pulse" />
                : <p className="font-display font-semibold text-[52px] text-ink leading-none">
                    {fmt(investorStats?.walletBalance)}
                  </p>
              }
              <Link to="/wallet" className="flex items-center gap-1 font-['Lato'] text-sm text-ink/60 hover:text-ink transition-colors mt-4">
                Top up wallet <ArrowRight size={14} />
              </Link>
            </div>

            {/* Active Bids */}
            <div className="col-span-3 bg-teal rounded-[20px] p-7 flex flex-col justify-between" style={fadeUp(statsInView, 60)}>
              <div className="flex items-center gap-2 mb-2">
                <BarChart2 size={16} className="text-[#fff8ec]/60" />
                <p className="font-['Lato'] text-sm text-[#fff8ec]/60">Active Bids</p>
              </div>
              {statsLoading
                ? <Skeleton className="h-14 w-16" />
                : <p className="font-display font-semibold text-[52px] text-[#fff8ec] leading-none">
                    {investorStats?.activeBids ?? 0}
                  </p>
              }
              <Link to="/bids" className="flex items-center gap-1 font-['Lato'] text-sm text-[#fff8ec]/60 hover:text-[#fff8ec] transition-colors mt-4">
                View bids <ArrowRight size={14} />
              </Link>
            </div>

            {/* Total Invested */}
            <div className="col-span-4 bg-white border border-ink/10 rounded-[20px] p-7 flex flex-col justify-between" style={fadeUp(statsInView, 120)}>
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp size={16} className="text-ink/50" />
                <p className="font-['Lato'] text-sm text-ink/50">Total Invested</p>
              </div>
              {statsLoading
                ? <SkeletonDark className="h-14 w-36" />
                : <p className="font-display font-semibold text-[40px] text-ink leading-none">
                    {fmt(investorStats?.totalInvested)}
                  </p>
              }
              <div className="flex items-center gap-2 mt-4">
                <DollarSign size={14} className="text-ink/40" />
                <span className="font-['Lato'] text-sm text-ink/50">
                  {statsLoading ? '—' : investorStats?.activeReturns ?? 0} active return{investorStats?.activeReturns !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ── Body content ── */}
        <div ref={bodyRef} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {isSeller ? (
            <>
              {/* Recent invoices */}
              <div className="lg:col-span-2 bg-white border border-ink/10 rounded-[20px] overflow-hidden" style={fadeUp(bodyInView, 0)}>
                <div className="flex items-center justify-between px-7 py-5 border-b border-ink/8">
                  <h2 className="font-['Lato'] font-semibold text-base text-ink">Recent Invoices</h2>
                  <Link to="/invoices" className="font-['Lato'] text-sm text-ink/50 hover:text-ink transition-colors flex items-center gap-1">
                    View all <ArrowRight size={13} />
                  </Link>
                </div>
                <div className="px-7 py-5">
                  {invoicesLoading ? (
                    <div className="space-y-3">
                      {[...Array(4)].map((_, i) => <SkeletonDark key={i} className="h-10 w-full" />)}
                    </div>
                  ) : recentInvoices.length === 0 ? (
                    <div className="text-center py-12">
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
                        <tr className="border-b border-ink/8 text-ink/40">
                          <th className="text-left pb-3 font-medium">Token</th>
                          <th className="text-left pb-3 font-medium">Debtor</th>
                          <th className="text-right pb-3 font-medium">Face Value</th>
                          <th className="text-center pb-3 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recentInvoices.map((inv) => (
                          <tr key={inv.id} className="border-b border-ink/5 hover:bg-cream transition-colors">
                            <td className="py-3 text-ink font-medium">{inv.invoice_token || inv.id}</td>
                            <td className="py-3 text-ink/60">{inv.debtor_name || '—'}</td>
                            <td className="py-3 text-right text-ink font-medium">{fmt(inv.face_value)}</td>
                            <td className="py-3 text-center"><Badge status={inv.status} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>

              {/* Quick actions */}
              <div className="space-y-4" style={fadeUp(bodyInView, 80)}>
                <div className="bg-cream rounded-[20px] p-7">
                  <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider mb-4">Quick Actions</p>
                  <div className="space-y-3">
                    <Link
                      to="/invoices/new"
                      className="flex items-center justify-between bg-teal text-[#fff8ec] rounded-[14px] px-5 py-4 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity"
                    >
                      <span className="flex items-center gap-2"><PlusCircle size={16} /> List New Invoice</span>
                      <ArrowRight size={16} />
                    </Link>
                    <Link
                      to="/invoices"
                      className="flex items-center justify-between bg-white border border-ink/10 rounded-[14px] px-5 py-4 font-['Lato'] font-medium text-sm text-ink hover:border-ink/30 hover:bg-white transition-all"
                    >
                      <span className="flex items-center gap-2"><FileText size={16} /> My Invoices</span>
                      <ArrowRight size={16} className="text-ink/40" />
                    </Link>
                    <Link
                      to="/loans"
                      className="flex items-center justify-between bg-white border border-ink/10 rounded-[14px] px-5 py-4 font-['Lato'] font-medium text-sm text-ink hover:border-ink/30 transition-all"
                    >
                      <span className="flex items-center gap-2"><CreditCard size={16} /> My Loans</span>
                      <ArrowRight size={16} className="text-ink/40" />
                    </Link>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Featured listings */}
              <div className="lg:col-span-2 bg-white border border-ink/10 rounded-[20px] overflow-hidden" style={fadeUp(bodyInView, 0)}>
                <div className="flex items-center justify-between px-7 py-5 border-b border-ink/8">
                  <h2 className="font-['Lato'] font-semibold text-base text-ink">Live Listings</h2>
                  <Link to="/marketplace" className="font-['Lato'] text-sm text-ink/50 hover:text-ink transition-colors flex items-center gap-1">
                    Browse all <ArrowRight size={13} />
                  </Link>
                </div>
                <div className="px-7 py-5">
                  {listingsLoading ? (
                    <div className="space-y-3">
                      {[...Array(3)].map((_, i) => <SkeletonDark key={i} className="h-16 w-full" />)}
                    </div>
                  ) : featuredListings.length === 0 ? (
                    <div className="text-center py-12">
                      <ShoppingCart size={36} className="text-ink/15 mx-auto mb-3" />
                      <p className="font-['Lato'] text-sm text-ink/40">No listings available</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {featuredListings.map((listing) => (
                        <Link
                          key={listing.id}
                          to={`/marketplace/${listing.id}`}
                          className="flex items-center justify-between p-4 rounded-[12px] border border-ink/8 hover:border-ink/20 hover:bg-cream transition-all duration-150"
                        >
                          <div>
                            <p className="font-['Lato'] font-medium text-sm text-ink">{listing.invoice_token}</p>
                            <p className="font-['Lato'] text-xs text-ink/50">{listing.debtor_name}</p>
                          </div>
                          <div className="flex items-center gap-3">
                            <Badge status={listing.urgency_level} />
                            <p className="font-['Lato'] font-semibold text-sm text-ink">{fmt(listing.current_bid || listing.minimum_bid)}</p>
                            <ArrowRight size={14} className="text-ink/30" />
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Quick actions */}
              <div className="space-y-4" style={fadeUp(bodyInView, 80)}>
                <div className="bg-cream rounded-[20px] p-7">
                  <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider mb-4">Quick Actions</p>
                  <div className="space-y-3">
                    <Link
                      to="/marketplace"
                      className="flex items-center justify-between bg-teal text-[#fff8ec] rounded-[14px] px-5 py-4 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity"
                    >
                      <span className="flex items-center gap-2"><ShoppingCart size={16} /> Browse Marketplace</span>
                      <ArrowRight size={16} />
                    </Link>
                    <Link
                      to="/wallet"
                      className="flex items-center justify-between bg-white border border-ink/10 rounded-[14px] px-5 py-4 font-['Lato'] font-medium text-sm text-ink hover:border-ink/30 transition-all"
                    >
                      <span className="flex items-center gap-2"><Wallet size={16} /> Top Up Wallet</span>
                      <ArrowRight size={16} className="text-ink/40" />
                    </Link>
                    <Link
                      to="/bids"
                      className="flex items-center justify-between bg-white border border-ink/10 rounded-[14px] px-5 py-4 font-['Lato'] font-medium text-sm text-ink hover:border-ink/30 transition-all"
                    >
                      <span className="flex items-center gap-2"><BarChart2 size={16} /> My Bids</span>
                      <ArrowRight size={16} className="text-ink/40" />
                    </Link>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </AppLayout>
  )
}
