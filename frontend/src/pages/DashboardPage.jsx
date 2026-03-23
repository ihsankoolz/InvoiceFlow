import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { PlusCircle, FileText, ShoppingCart, ArrowRight } from 'lucide-react'
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

function fmt(n) {
  if (n == null) return '—'
  return `$${Number(n).toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtDate(str) {
  if (!str) return '—'
  return new Date(str).toLocaleDateString('en-SG', { day: '2-digit', month: 'long', year: 'numeric' })
}

function timeAgo(str) {
  if (!str) return ''
  const diff = Date.now() - new Date(str).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function txColor(type) {
  if (!type) return 'text-ink/40'
  const t = type.toUpperCase()
  if (t.includes('TOPUP') || t.includes('DEPOSIT')) return 'text-[#7a38fc]'
  if (t.includes('CREDIT') || t.includes('REPAY') || t.includes('RETURN') || t.includes('WON')) return 'text-[#397f75]'
  if (t.includes('DEBIT') || t.includes('BID') || t.includes('OUTBID')) return 'text-[#d90000]'
  return 'text-ink/60'
}

function txSign(type, amount) {
  if (!type) return fmt(amount)
  const t = type.toUpperCase()
  if (t.includes('TOPUP') || t.includes('DEPOSIT') || t.includes('CREDIT') || t.includes('REPAY') || t.includes('RETURN')) return `+${fmt(amount)}`
  return fmt(amount)
}

/* ── Seller Dashboard ── */
function SellerDashboard({ user }) {
  const [statsRef, statsInView] = useInView(0.05)
  const [bodyRef, bodyInView]   = useInView(0.05)

  const [sellerStats, setSellerStats]       = useState(null)
  const [recentInvoices, setRecentInvoices] = useState([])
  const [statsLoading, setStatsLoading]     = useState(true)
  const [invoicesLoading, setInvoicesLoading] = useState(false)

  useEffect(() => {
    if (!user) return
    setStatsLoading(true)
    setInvoicesLoading(true)
    Promise.allSettled([
      api.get(`/invoices?seller_id=${user.sub}`),
      api.get('/wallet/balance'),
      api.get(`/loans?seller_id=${user.sub}`),
    ]).then(([invoicesRes, walletRes, loansRes]) => {
      const invoices = invoicesRes.status === 'fulfilled' ? (invoicesRes.value.data?.invoices || invoicesRes.value.data || []) : []
      const wallet   = walletRes.status === 'fulfilled' ? walletRes.value.data : null
      const loans    = loansRes.status === 'fulfilled' ? (loansRes.value.data?.loans || loansRes.value.data || []) : []
      const activeListings = invoices.filter(i => i.status === 'LISTED').length
      const totalFinanced  = invoices.filter(i => ['FINANCED', 'ACCEPTED'].includes(i.status)).reduce((s, i) => s + Number(i.face_value || 0), 0)
      const activeLoans    = loans.filter(l => l.status === 'ACTIVE' || l.status === 'DUE').length
      setSellerStats({ activeListings, totalFinanced, activeLoans, walletBalance: wallet?.balance ?? wallet?.available_balance ?? null })
      setRecentInvoices(invoices.slice(0, 5))
    }).finally(() => {
      setStatsLoading(false)
      setInvoicesLoading(false)
    })
  }, [user])

  return (
    <div className="px-10 py-10 max-w-6xl mx-auto">
      {/* Greeting */}
      <div className="mb-10" style={fadeUp(true, 0)}>
        <h1 className="font-['Lato'] font-bold text-[28px] text-ink leading-tight">
          Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'}, {user?.full_name?.split(' ')[0] || 'there'}
        </h1>
        <p className="font-['Lato'] text-sm text-ink/40 mt-1">Here's an overview of your listings and loans.</p>
      </div>

      {/* Stat cards */}
      <div ref={statsRef} className="grid grid-cols-4 gap-4 mb-10">
        <div className="bg-teal rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 0)}>
          <p className="font-['Lato'] text-xs text-white/60 uppercase tracking-wider">Wallet Balance</p>
          {statsLoading ? <div className="h-9 w-32 bg-white/20 rounded animate-pulse" /> : <p className="font-['Lato'] font-bold text-[28px] text-white leading-none">{fmt(sellerStats?.walletBalance)}</p>}
          <Link to="/wallet" className="font-['Lato'] text-xs text-white/60 hover:text-white transition-colors flex items-center gap-1 mt-auto">Manage <ArrowRight size={11} /></Link>
        </div>
        <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 60)}>
          <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Active Listings</p>
          {statsLoading ? <div className="h-9 w-16 bg-ink/8 rounded animate-pulse" /> : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{sellerStats?.activeListings ?? 0}</p>}
          <Link to="/invoices" className="font-['Lato'] text-xs text-ink/40 hover:text-ink transition-colors flex items-center gap-1 mt-auto">View all <ArrowRight size={11} /></Link>
        </div>
        <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 120)}>
          <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Total Financed</p>
          {statsLoading ? <div className="h-9 w-32 bg-ink/8 rounded animate-pulse" /> : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{fmt(sellerStats?.totalFinanced)}</p>}
          <p className="font-['Lato'] text-xs text-ink/40 mt-auto">across financed invoices</p>
        </div>
        <div className="border border-ink/10 rounded-[16px] p-6 flex flex-col gap-3" style={fadeUp(statsInView, 180)}>
          <p className="font-['Lato'] text-xs text-ink/40 uppercase tracking-wider">Active Loans</p>
          {statsLoading ? <div className="h-9 w-16 bg-ink/8 rounded animate-pulse" /> : <p className="font-['Lato'] font-bold text-[28px] text-teal leading-none">{sellerStats?.activeLoans ?? 0}</p>}
          <Link to="/loans" className="font-['Lato'] text-xs text-ink/40 hover:text-ink transition-colors flex items-center gap-1 mt-auto">View loans <ArrowRight size={11} /></Link>
        </div>
      </div>

      {/* Recent invoices table */}
      <div ref={bodyRef} style={fadeUp(bodyInView, 0)}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-['Lato'] font-semibold text-base text-ink">Recent Invoices</h2>
          <Link to="/invoices" className="font-['Lato'] text-sm text-ink/40 hover:text-ink transition-colors flex items-center gap-1">View all <ArrowRight size={13} /></Link>
        </div>
        {invoicesLoading ? (
          <div className="space-y-3">{[...Array(4)].map((_, i) => <div key={i} className="h-10 bg-ink/5 rounded-lg animate-pulse" />)}</div>
        ) : recentInvoices.length === 0 ? (
          <div className="text-center py-16 border border-ink/8 rounded-[16px]">
            <FileText size={36} className="text-ink/15 mx-auto mb-3" />
            <p className="font-['Lato'] text-sm text-ink/40 mb-4">No invoices yet</p>
            <Link to="/invoices/new" className="inline-flex items-center gap-2 bg-teal text-white rounded-[22px] px-5 py-2 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity">
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
              {recentInvoices.map(inv => (
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
    </div>
  )
}

/* ── Investor Dashboard ── */
function InvestorDashboard({ user }) {
  const [pageRef, pageInView] = useInView(0.01)

  const [walletBalance, setWalletBalance]   = useState(null)
  const [walletLoading, setWalletLoading]   = useState(true)
  const [transactions, setTransactions]     = useState([])
  const [txLoading, setTxLoading]           = useState(true)
  const [activeBids, setActiveBids]         = useState([])
  const [bidsLoading, setBidsLoading]       = useState(true)
  const [leadingCount, setLeadingCount]     = useState(0)
  const [outbidCount, setOutbidCount]       = useState(0)
  const [totalInBids, setTotalInBids]       = useState(0)
  const [upcomingLoans, setUpcomingLoans]   = useState([])
  const [loansCount, setLoansCount]         = useState(0)
  const [loansLoading, setLoansLoading]     = useState(true)

  useEffect(() => {
    if (!user) return

    // Wallet balance
    api.get('/wallet/balance')
      .then(r => setWalletBalance(r.data?.balance ?? r.data?.available_balance ?? null))
      .catch(() => setWalletBalance(null))
      .finally(() => setWalletLoading(false))

    // Transactions (activity feed)
    api.get('/wallet/transactions')
      .then(r => {
        const data = r.data?.transactions || r.data || []
        setTransactions(Array.isArray(data) ? data.slice(0, 5) : [])
      })
      .catch(() => setTransactions([]))
      .finally(() => setTxLoading(false))

    // Active bids
    api.get(`/bids?investor_id=${user.sub}`)
      .then(r => {
        const bids = r.data?.bids || r.data || []
        const pending = bids.filter(b => b.status === 'PENDING' || b.status === 'ACTIVE')
        setActiveBids(pending.slice(0, 3))
        setLeadingCount(pending.filter(b => b.is_leading || b.leading).length)
        setOutbidCount(pending.filter(b => !b.is_leading && !b.leading).length)
        setTotalInBids(pending.reduce((s, b) => s + Number(b.amount || 0), 0))
      })
      .catch(() => { setActiveBids([]); setLeadingCount(0); setOutbidCount(0) })
      .finally(() => setBidsLoading(false))

    // Upcoming repayments (loans investor is involved in)
    api.get(`/loans?investor_id=${user.sub}`)
      .then(r => {
        const loans = r.data?.loans || r.data || []
        const active = loans.filter(l => l.status === 'ACTIVE' || l.status === 'DUE')
        setLoansCount(active.length)
        setUpcomingLoans(active.slice(0, 3))
      })
      .catch(() => { setUpcomingLoans([]); setLoansCount(0) })
      .finally(() => setLoansLoading(false))
  }, [user])

  // Days left progress for a loan
  function daysProgress(loan) {
    if (!loan.created_at || !loan.due_date) return { pct: 50, days: null }
    const total = new Date(loan.due_date) - new Date(loan.created_at)
    const remaining = new Date(loan.due_date) - Date.now()
    const pct = Math.max(0, Math.min(100, (remaining / total) * 100))
    const days = Math.max(0, Math.ceil(remaining / 86400000))
    return { pct, days }
  }

  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening'
  const firstName = user?.full_name?.split(' ')[0] || 'there'

  return (
    <>
      {/* Teal greeting strip */}
      <div className="bg-teal px-10 py-10">
        <h1 className="font-['Lato'] font-bold text-[32px] text-white leading-tight">{greeting}, {firstName}</h1>
        <p className="font-['Lato'] text-white/60 text-base mt-1">Here is an overview of your portfolio.</p>
      </div>

      {/* 3-column layout */}
      <div ref={pageRef} className="px-10 py-8 grid grid-cols-3 gap-6 max-w-[1400px] mx-auto">

        {/* ── Col 1: Wallet + Activity ── */}
        <div className="flex flex-col gap-6">

          {/* Wallet Balance card */}
          <div className="bg-cream rounded-[16px] p-6 flex flex-col gap-4" style={fadeUp(pageInView, 0)}>
            <p className="font-['Lato'] font-semibold text-xs text-ink uppercase tracking-wider">Wallet Balance</p>
            {walletLoading
              ? <div className="h-10 w-36 bg-ink/10 rounded animate-pulse" />
              : <p className="font-['Lato'] font-bold text-[32px] text-ink leading-none">{fmt(walletBalance)}</p>
            }
            {/* Progress bar */}
            <div>
              <div className="h-1.5 bg-[#e0eae8] rounded-full w-full">
                <div className="h-1.5 bg-teal rounded-full w-full" />
              </div>
              <div className="flex items-center justify-between mt-2">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-teal" />
                  <span className="font-['Lato'] text-xs text-ink">Available</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-[#e0eae8]" />
                  <span className="font-['Lato'] text-xs text-ink">Locked in bids</span>
                </div>
              </div>
            </div>
            <p className="font-['Lato'] text-sm text-ink/60">{fmt(walletBalance)} available to bid</p>
            {/* Actions */}
            <div className="flex items-center gap-4 mt-1">
              <Link
                to="/wallet"
                className="bg-teal text-white font-['Lato'] font-semibold text-sm px-5 py-2 rounded-[22px] hover:opacity-90 transition-opacity"
              >
                Top up
              </Link>
              <button className="font-['Lato'] font-semibold text-sm text-teal hover:opacity-70 transition-opacity">
                Withdraw
              </button>
            </div>
          </div>

          {/* Activity Feed card */}
          <div className="bg-white border border-black/8 rounded-[16px] p-6 flex flex-col gap-5" style={fadeUp(pageInView, 60)}>
            <p className="font-['Lato'] font-semibold text-xs text-ink uppercase tracking-wider">Activity Feed</p>
            {txLoading ? (
              <div className="space-y-4">{[...Array(3)].map((_, i) => <div key={i} className="h-10 bg-ink/5 rounded-lg animate-pulse" />)}</div>
            ) : transactions.length === 0 ? (
              <p className="font-['Lato'] text-sm text-ink/40 py-6 text-center">No recent activity</p>
            ) : (
              <div className="flex flex-col gap-5">
                {transactions.map((tx, i) => (
                  <div key={i} className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-['Lato'] text-sm text-ink leading-snug">{tx.description || tx.type || 'Transaction'}</p>
                      <p className="font-['Lato'] text-xs text-ink/40 mt-0.5">{timeAgo(tx.created_at || tx.timestamp)}</p>
                    </div>
                    <p className={`font-['Lato'] font-medium text-sm whitespace-nowrap ${txColor(tx.type)}`}>
                      {txSign(tx.type, tx.amount)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Col 2: Active Bids ── */}
        <div className="bg-white border border-black/8 rounded-[16px] overflow-hidden flex flex-col" style={fadeUp(pageInView, 80)}>
          {/* Teal header */}
          <div className="bg-teal px-6 pt-6 pb-5 flex flex-col gap-4">
            <p className="font-['Lato'] font-semibold text-xs text-white uppercase tracking-wider">Active Bids</p>
            {bidsLoading ? (
              <div className="h-10 w-16 bg-white/20 rounded animate-pulse" />
            ) : (
              <div className="flex items-end justify-between">
                <p className="font-['Lato'] font-medium text-[36px] text-white leading-none">{activeBids.length}</p>
                <div className="text-right">
                  <p className="font-['Lato'] text-sm text-white">{fmt(totalInBids)} in bids</p>
                  <p className="font-['Lato'] text-sm text-white/70">{leadingCount} leading · {outbidCount} outbid</p>
                </div>
              </div>
            )}
          </div>

          {/* Bid rows */}
          <div className="flex-1 px-6 pt-5 pb-4 flex flex-col gap-4">
            {bidsLoading ? (
              <div className="space-y-4">{[...Array(3)].map((_, i) => <div key={i} className="h-16 bg-ink/5 rounded-lg animate-pulse" />)}</div>
            ) : activeBids.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center py-10">
                <ShoppingCart size={32} className="text-ink/15 mb-3" />
                <p className="font-['Lato'] text-sm text-ink/40 mb-4">No active bids</p>
                <Link to="/marketplace" className="inline-flex items-center gap-2 bg-teal text-white rounded-[22px] px-5 py-2 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity">
                  Browse marketplace
                </Link>
              </div>
            ) : (
              activeBids.map((bid, i) => {
                const isLeading = bid.is_leading || bid.leading
                return (
                  <div key={bid.id || i} className="border-b border-black/5 pb-4 last:border-0 flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                      <p className="font-['Lato'] font-medium text-sm text-ink">{bid.invoice_token || bid.invoice_id || `BID-${bid.id}`}</p>
                      <p className="font-['Lato'] font-medium text-sm text-ink">{fmt(bid.amount)}</p>
                    </div>
                    <div className="flex items-center justify-between">
                      <p className="font-['Lato'] text-xs text-ink/40">
                        {bid.closes_at ? `Closes ${timeAgo(bid.closes_at)}` : 'Active'}
                      </p>
                      <span className={`font-['Lato'] font-medium text-xs px-3 py-1 rounded-full ${
                        isLeading ? 'bg-[#e0eae8] text-teal' : 'bg-[#ffdede] text-[#d90000]'
                      }`}>
                        {isLeading ? 'Leading' : 'Outbid'}
                      </span>
                    </div>
                    {isLeading && bid.expected_return != null && (
                      <p className="font-['Lato'] text-xs">
                        <span className="text-teal">+{fmt(bid.expected_return)}</span>
                        <span className="text-ink/40"> expected</span>
                      </p>
                    )}
                    {!isLeading && (
                      <p className="font-['Lato'] text-xs text-ink/40">No returns</p>
                    )}
                  </div>
                )
              })
            )}
          </div>

          {/* Footer */}
          {!bidsLoading && activeBids.length > 0 && (
            <div className="px-6 pb-5 flex items-center justify-between">
              <Link to="/bids" className="bg-teal text-white font-['Lato'] font-semibold text-sm px-5 py-2 rounded-[22px] hover:opacity-90 transition-opacity">
                View Bids
              </Link>
              <p className="font-['Lato'] text-xs text-ink/40">
                Total expected: +{fmt(activeBids.filter(b => b.is_leading || b.leading).reduce((s, b) => s + Number(b.expected_return || 0), 0))}
              </p>
            </div>
          )}
        </div>

        {/* ── Col 3: Upcoming Repayments ── */}
        <div className="bg-white border border-black/8 rounded-[16px] p-6 flex flex-col gap-5" style={fadeUp(pageInView, 160)}>
          <p className="font-['Lato'] font-semibold text-xs text-ink uppercase tracking-wider">Upcoming Repayments</p>
          {loansLoading ? (
            <div className="h-10 w-16 bg-ink/5 rounded animate-pulse" />
          ) : (
            <div className="flex items-end gap-2">
              <p className="font-['Lato'] font-medium text-[36px] text-ink leading-none">{loansCount}</p>
              <p className="font-['Lato'] text-sm text-ink pb-1">active loans</p>
            </div>
          )}

          {loansLoading ? (
            <div className="space-y-4">{[...Array(2)].map((_, i) => <div key={i} className="h-20 bg-ink/5 rounded-lg animate-pulse" />)}</div>
          ) : upcomingLoans.length === 0 ? (
            <p className="font-['Lato'] text-sm text-ink/40 py-6 text-center">No upcoming repayments</p>
          ) : (
            <div className="flex flex-col gap-6">
              {upcomingLoans.map((loan, i) => {
                const { pct, days } = daysProgress(loan)
                const isUrgent = days != null && days <= 7
                const barColor = isUrgent ? 'bg-[#eeb300]' : 'bg-teal'
                const trackColor = isUrgent ? 'bg-[#ffe8a4]' : 'bg-[#e0eae8]'
                const daysColor = isUrgent ? 'text-[#eeb300]' : 'text-teal'
                const totalPayout = Number(loan.amount || 0) + Number(loan.return_amount || loan.interest || 0)
                return (
                  <div key={loan.id || i} className="flex flex-col gap-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-['Lato'] font-medium text-sm text-ink">{loan.invoice_token || `LOAN-${loan.id}`}</p>
                        <p className="font-['Lato'] text-xs text-ink/40 mt-0.5">Due {fmtDate(loan.due_date)}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-['Lato'] font-medium text-sm text-ink">{fmt(totalPayout || loan.face_value)} total payout</p>
                        {loan.return_amount != null && (
                          <p className="font-['Lato'] text-xs text-ink/40">{fmt(loan.return_amount || loan.interest)} return</p>
                        )}
                      </div>
                    </div>
                    {/* Progress bar */}
                    <div className={`h-1.5 ${trackColor} rounded-full w-full`}>
                      <div className={`h-1.5 ${barColor} rounded-full`} style={{ width: `${100 - pct}%` }} />
                    </div>
                    {days != null && (
                      <p className={`font-['Lato'] text-xs ${daysColor}`}>{days} days left</p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

      </div>
    </>
  )
}

/* ── Main export ── */
export default function DashboardPage() {
  const { user } = useAuth()
  const isSeller = user?.role === 'SELLER'

  return (
    <DashboardLayout>
      <style>{`
        @keyframes dashFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      {isSeller ? <SellerDashboard user={user} /> : <InvestorDashboard user={user} />}
    </DashboardLayout>
  )
}
