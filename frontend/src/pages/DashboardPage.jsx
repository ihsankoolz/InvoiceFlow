import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { PlusCircle, FileText, ShoppingCart, ArrowRight } from 'lucide-react'
import DashboardLayout from '../components/layout/DashboardLayout'
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
  return `$${Number(n ?? 0).toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtDate(str) {
  if (!str) return '—'
  const utc = /Z|[+-]\d{2}:\d{2}$/.test(str) ? str : str + 'Z'
  return new Date(utc).toLocaleDateString('en-SG', { day: '2-digit', month: 'long', year: 'numeric', timeZone: 'Asia/Singapore' })
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

const TX_LABELS = {
  'WALLET_CREDIT':  'Wallet Top-Up',
  'WALLET_DEBIT':   'Wallet Debit',
  'BID_LOCK':       'Bid Placed',
  'BID_UNLOCK':     'Bid Released',
  'BID_DEDUCT':     'Bid Won',
  'LOAN_REPAYMENT': 'Loan Repayment',
  'LOAN_RETURN':    'Loan Return',
}

function txLabel(tx) {
  return TX_LABELS[tx.description] || TX_LABELS[tx.type] || tx.description || tx.type || 'Transaction'
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
  const [pageRef, pageInView] = useInView(0.01)

  const [invoices, setInvoices]           = useState([])
  const [allLoans, setAllLoans]           = useState([])
  const [activeListings, setActiveListings] = useState([])
  const [upcomingLoans, setUpcomingLoans] = useState([])
  const [loansCount, setLoansCount]       = useState(0)
  const [totalOutstanding, setTotalOutstanding] = useState(0)
  const [loading, setLoading]             = useState(true)

  const fetchSellerData = () => {
    if (!user) return
    Promise.allSettled([
      api.get(`/invoices?seller_id=${user.sub}`),
      api.get(`/loans?seller_id=${user.sub}`),
      api.get(`/listings?seller_id=${user.sub}`),
    ]).then(([invoicesRes, loansRes, listingsRes]) => {
      const allInvoices = invoicesRes.status === 'fulfilled' ? (invoicesRes.value.data?.invoices || invoicesRes.value.data || []) : []
      const loans       = loansRes.status === 'fulfilled' ? (loansRes.value.data?.loans || loansRes.value.data || []) : []
      const listings    = listingsRes.status === 'fulfilled' ? (listingsRes.value.data || []) : []
      const active      = loans.filter(l => l.status === 'ACTIVE' || l.status === 'DUE')
      active.sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
      setInvoices(allInvoices)
      setAllLoans(loans)
      setActiveListings(listings.slice(0, 5))
      setLoansCount(active.length)
      setUpcomingLoans(active.slice(0, 3))
      setTotalOutstanding(active.reduce((s, l) => s + Number(l.principal || 0), 0))
    }).finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchSellerData()
    const interval = setInterval(fetchSellerData, 30000)
    return () => clearInterval(interval)
  }, [user])

  // Derived performance stats
  const totalFinanced   = invoices.filter(i => ['FINANCED', 'ACCEPTED'].includes(i.status))
  const totalRaised     = allLoans.reduce((s, l) => s + Number(l.bid_amount || 0), 0)
  // Financing rate = financed / invoices that actually reached market (excludes DRAFT & REJECTED)
  const listedOrBeyond  = invoices.filter(i => ['LISTED', 'FINANCED', 'ACCEPTED', 'REPAID', 'DEFAULTED'].includes(i.status))
  const totalSubmitted  = listedOrBeyond.length
  const financingRate   = totalSubmitted > 0 ? Math.round((totalFinanced.length / totalSubmitted) * 100) : 0

  function daysProgress(loan) {
    if (!loan.created_at || !loan.due_date) return { pct: 50, days: null }
    const total     = new Date(loan.due_date) - new Date(loan.created_at)
    const remaining = new Date(loan.due_date) - Date.now()
    const pct  = Math.max(0, Math.min(100, (remaining / total) * 100))
    const days = Math.max(0, Math.ceil(remaining / 86400000))
    return { pct, days }
  }

  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 18 ? 'Good afternoon' : 'Good evening'

  return (
    <>
      {/* Teal greeting strip */}
      <div className="bg-teal px-10 py-10">
        <h1 className="font-['Lato'] font-bold text-[32px] text-white leading-tight">{greeting}, {user?.full_name || 'there'}</h1>
        <p className="font-['Lato'] text-white/60 text-base mt-1">Here is an overview of your listings and loans.</p>
      </div>

      {/* 3-column layout */}
      <div ref={pageRef} className="px-10 py-8 grid grid-cols-3 gap-6 max-w-[1400px] mx-auto">

        {/* ── Col 1: Performance ── */}
        <div className="flex flex-col gap-6">
          {/* Total Raised */}
          <div className="bg-cream rounded-[16px] p-6 flex flex-col gap-4" style={fadeUp(pageInView, 0)}>
            <p className="font-['Lato'] font-semibold text-xs text-ink uppercase tracking-wider">Total Raised</p>
            {loading
              ? <div className="h-10 w-36 bg-ink/10 rounded animate-pulse" />
              : <p className="font-['Lato'] font-bold text-[32px] text-ink leading-none">{fmt(totalRaised)}</p>
            }
            <p className="font-['Lato'] text-sm text-ink/60">across {totalFinanced.length} financed invoices</p>
            <Link
              to="/invoices/new"
              className="self-start bg-teal text-white font-['Lato'] font-semibold text-sm px-5 py-2 rounded-[22px] hover:opacity-90 transition-opacity"
            >
              List Invoice
            </Link>
          </div>

          {/* Performance stats */}
          <div className="bg-white border border-black/8 rounded-[16px] p-6 flex flex-col gap-5" style={fadeUp(pageInView, 60)}>
            <p className="font-['Lato'] font-semibold text-xs text-ink uppercase tracking-wider">Performance</p>
            {loading ? (
              <div className="space-y-4">{[...Array(3)].map((_, i) => <div key={i} className="h-8 bg-ink/5 rounded animate-pulse" />)}</div>
            ) : (
              <div className="flex flex-col gap-4">
                {/* Financing rate */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <p className="font-['Lato'] text-xs text-ink/50">Financing Rate</p>
                    <p className="font-['Lato'] font-semibold text-sm text-ink">{financingRate}%</p>
                  </div>
                  <div className="h-1.5 bg-[#e0eae8] rounded-full">
                    <div className="h-1.5 bg-teal rounded-full transition-all duration-700" style={{ width: `${financingRate}%` }} />
                  </div>
                </div>
                {/* Total submitted */}
                <div className="flex items-center justify-between">
                  <p className="font-['Lato'] text-xs text-ink/50">Invoices Submitted</p>
                  <p className="font-['Lato'] font-semibold text-sm text-ink">{totalSubmitted}</p>
                </div>
                {/* Avg face value */}
                <div className="flex items-center justify-between">
                  <p className="font-['Lato'] text-xs text-ink/50">Total Outstanding</p>
                  <p className="font-['Lato'] font-semibold text-sm text-ink">{fmt(totalOutstanding)}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Col 2: Active Listings ── */}
        <div className="bg-white border border-black/8 rounded-[16px] overflow-hidden flex flex-col" style={fadeUp(pageInView, 80)}>
          <div className="bg-teal px-6 pt-6 pb-5 flex flex-col gap-4">
            <p className="font-['Lato'] font-semibold text-xs text-white uppercase tracking-wider">Active Listings</p>
            {loading
              ? <div className="h-10 w-16 bg-white/20 rounded animate-pulse" />
              : (
                <div className="flex items-end justify-between">
                  <p className="font-['Lato'] font-medium text-[36px] text-white leading-none">{activeListings.length}</p>
                  <p className="font-['Lato'] text-sm text-white/70">currently on market</p>
                </div>
              )
            }
          </div>

          <div className="flex-1 px-6 pt-5 pb-4 flex flex-col gap-4">
            {loading ? (
              <div className="space-y-4">{[...Array(3)].map((_, i) => <div key={i} className="h-16 bg-ink/5 rounded-lg animate-pulse" />)}</div>
            ) : activeListings.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center py-10">
                <FileText size={32} className="text-ink/15 mb-3" />
                <p className="font-['Lato'] text-sm text-ink/40 mb-4">No active listings</p>
                <Link to="/invoices/new" className="inline-flex items-center gap-2 bg-teal text-white rounded-[22px] px-5 py-2 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity">
                  <PlusCircle size={15} /> List an invoice
                </Link>
              </div>
            ) : (
              activeListings.map((inv, i) => (
                <div key={inv.id || i} className="border-b border-black/5 pb-4 last:border-0 flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <p className="font-['Lato'] font-medium text-sm text-ink">{inv.invoice_token || inv.id}</p>
                    <p className="font-['Lato'] font-medium text-sm text-ink">{inv.current_bid ? fmt(inv.current_bid) : '—'}</p>
                  </div>
                  <div className="flex items-center justify-between">
                    <p className="font-['Lato'] text-xs text-ink/40">{inv.debtor_name || '—'}</p>
                    {inv.deadline && (
                      <p className="font-['Lato'] text-xs text-ink/40">Due {fmtDate(inv.deadline)}</p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {!loading && activeListings.length > 0 && (
            <div className="px-6 pb-5">
              <Link to="/invoices" className="bg-teal text-white font-['Lato'] font-semibold text-sm px-5 py-2 rounded-[22px] hover:opacity-90 transition-opacity">
                View all
              </Link>
            </div>
          )}
        </div>

        {/* ── Col 3: Upcoming Repayments ── */}
        <div className="bg-white border border-black/8 rounded-[16px] p-6 flex flex-col gap-5" style={fadeUp(pageInView, 160)}>
          <p className="font-['Lato'] font-semibold text-xs text-ink uppercase tracking-wider">Upcoming Repayments</p>
          {loading ? (
            <div className="h-10 w-16 bg-ink/5 rounded animate-pulse" />
          ) : (
            <div className="flex items-end gap-2">
              <p className="font-['Lato'] font-medium text-[36px] text-ink leading-none">{loansCount}</p>
              <p className="font-['Lato'] text-sm text-ink pb-1">active loans</p>
            </div>
          )}

          {loading ? (
            <div className="space-y-4">{[...Array(2)].map((_, i) => <div key={i} className="h-20 bg-ink/5 rounded-lg animate-pulse" />)}</div>
          ) : upcomingLoans.length === 0 ? (
            <p className="font-['Lato'] text-sm text-ink/40 py-6 text-center">No upcoming repayments</p>
          ) : (
            <div className="flex flex-col gap-6">
              {upcomingLoans.map((loan, i) => {
                const { pct, days } = daysProgress(loan)
                const isUrgent   = days != null && days <= 7
                const barColor   = isUrgent ? 'bg-[#eeb300]' : 'bg-teal'
                const trackColor = isUrgent ? 'bg-[#ffe8a4]' : 'bg-[#e0eae8]'
                const daysColor  = isUrgent ? 'text-[#eeb300]' : 'text-teal'
                return (
                  <div key={loan.id || i} className="flex flex-col gap-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-['Lato'] font-medium text-sm text-ink">{loan.invoice_token || `LOAN-${loan.id}`}</p>
                        <p className="font-['Lato'] text-xs text-ink/40 mt-0.5">Due {fmtDate(loan.due_date)}</p>
                      </div>
                      <p className="font-['Lato'] font-medium text-sm text-ink">{fmt(loan.principal)}</p>
                    </div>
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

          {!loading && loansCount > 0 && (
            <Link to="/loans" className="self-start font-['Lato'] text-sm text-ink/40 hover:text-ink transition-colors flex items-center gap-1 mt-auto">
              View all loans <ArrowRight size={13} />
            </Link>
          )}
        </div>

      </div>
    </>
  )
}

/* ── Investor Dashboard ── */
function InvestorDashboard({ user }) {
  const [pageRef, pageInView] = useInView(0.01)

  const [walletBalance, setWalletBalance]   = useState(null)
  const [lockedBalance, setLockedBalance]   = useState(0)
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
  const [loanBalance, setLoanBalance]       = useState(0)

  const fetchDashboardData = () => {
    if (!user) return

    Promise.allSettled([
      api.get(`/wallet/balance?user_id=${user.sub}`),
      api.get(`/wallet/transactions?user_id=${user.sub}`),
      api.get(`/bids?investor_id=${user.sub}`),
      api.get(`/loans?investor_id=${user.sub}`),
    ]).then(([walletRes, txRes, bidsRes, loansRes]) => {
      // Wallet balance + locked escrow
      if (walletRes.status === 'fulfilled') {
        setWalletBalance(Number(walletRes.value.data?.balance ?? walletRes.value.data?.available_balance ?? 0))
        setLockedBalance(Number(walletRes.value.data?.locked_balance ?? 0))
      } else {
        setWalletBalance(null)
      }
      setWalletLoading(false)

      // Transactions (activity feed)
      if (txRes.status === 'fulfilled') {
        const data = txRes.value.data?.transactions || txRes.value.data || []
        setTransactions(Array.isArray(data) ? data.slice(0, 5) : [])
      } else {
        setTransactions([])
      }
      setTxLoading(false)

      // Active bids
      if (bidsRes.status === 'fulfilled') {
        const bids = bidsRes.value.data?.bids || bidsRes.value.data || []
        const pending = bids.filter(b => b.status === 'PENDING' || b.status === 'ACTIVE' || b.status === 'OUTBID')
        setActiveBids(pending.slice(0, 3))
        setLeadingCount(pending.filter(b => b.status === 'PENDING' || b.status === 'ACTIVE').length)
        setOutbidCount(pending.filter(b => b.status === 'OUTBID').length)
        setTotalInBids(pending.reduce((s, b) => s + Number(b.amount || 0), 0))
      } else {
        setActiveBids([]); setLeadingCount(0); setOutbidCount(0)
      }
      setBidsLoading(false)

      // Upcoming repayments (loans investor is involved in)
      if (loansRes.status === 'fulfilled') {
        const loans = loansRes.value.data?.loans || loansRes.value.data || []
        const active = loans.filter(l => l.status === 'ACTIVE' || l.status === 'DUE')
        active.sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
        setLoansCount(active.length)
        setUpcomingLoans(active.slice(0, 3))
        setLoanBalance(active.reduce((s, l) => s + Number(l.principal || 0), 0))
      } else {
        setUpcomingLoans([]); setLoansCount(0); setLoanBalance(0)
      }
      setLoansLoading(false)
    })
  }

  useEffect(() => {
    fetchDashboardData()
    const interval = setInterval(fetchDashboardData, 30000)
    return () => clearInterval(interval)
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
  const firstName = user?.full_name || 'there'

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

          {/* Total Assets card */}
          <div className="bg-cream rounded-[16px] p-6 flex flex-col gap-4" style={fadeUp(pageInView, 0)}>
            <p className="font-['Lato'] font-semibold text-xs text-ink uppercase tracking-wider">Total Assets</p>
            {walletLoading
              ? <div className="h-10 w-36 bg-ink/10 rounded animate-pulse" />
              : <p className="font-['Lato'] font-bold text-[32px] text-ink leading-none">{fmt((walletBalance ?? 0) + lockedBalance + loanBalance)}</p>
            }
            {/* Progress bar */}
            <div>
              {(() => {
                const total = (walletBalance ?? 0) + lockedBalance + loanBalance
                const walletPct  = total > 0 ? (walletBalance ?? 0) / total * 100 : 100
                const escrowPct  = total > 0 ? lockedBalance / total * 100 : 0
                const loanPct    = total > 0 ? loanBalance / total * 100 : 0
                return (
                  <div className="relative h-1.5 bg-[#e0eae8] rounded-full w-full">
                    {/* Green segment — wallet available */}
                    <div
                      className="absolute left-0 top-0 h-1.5 bg-teal rounded-l-full group/green"
                      style={{ width: `${walletPct}%` }}
                    >
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-ink text-white text-xs rounded whitespace-nowrap opacity-0 group-hover/green:opacity-100 transition-opacity pointer-events-none">
                        {fmt(walletBalance ?? 0)} available
                      </div>
                    </div>
                    {/* Grey segment — locked in escrow */}
                    <div
                      className="absolute top-0 h-1.5 bg-[#b0c4c0] group/grey"
                      style={{ left: `${walletPct}%`, width: `${escrowPct}%` }}
                    >
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-ink text-white text-xs rounded whitespace-nowrap opacity-0 group-hover/grey:opacity-100 transition-opacity pointer-events-none">
                        {fmt(lockedBalance)} in escrow
                      </div>
                    </div>
                    {/* Yellow segment — with seller as loan */}
                    <div
                      className="absolute top-0 h-1.5 bg-amber-400 rounded-r-full group/loan"
                      style={{ left: `${walletPct + escrowPct}%`, width: `${loanPct}%` }}
                    >
                      <div className="absolute bottom-full right-0 mb-2 px-2 py-1 bg-ink text-white text-xs rounded whitespace-nowrap opacity-0 group-hover/loan:opacity-100 transition-opacity pointer-events-none">
                        {fmt(loanBalance)} with seller
                      </div>
                    </div>
                  </div>
                )
              })()}
              <div className="flex items-center justify-between mt-2">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-teal" />
                  <span className="font-['Lato'] text-xs text-ink">Wallet Balance</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-[#b0c4c0]" />
                  <span className="font-['Lato'] text-xs text-ink">Locked in Bids</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-amber-400" />
                  <span className="font-['Lato'] text-xs text-ink">With Seller</span>
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
                      <p className="font-['Lato'] text-sm text-ink leading-snug">{txLabel(tx)}</p>
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
                const isLeading = bid.status === 'PENDING' || bid.status === 'ACTIVE'
                return (
                  <div key={bid.id || i} className="border-b border-black/5 pb-4 last:border-0 flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                      {bid.listing_id ? (
                        <Link to={`/marketplace/${bid.listing_id}`} className="font-['Lato'] font-medium text-sm text-ink hover:text-teal hover:underline transition-colors duration-100">
                          {bid.invoice_token || bid.invoice_id || `BID-${bid.id}`}
                        </Link>
                      ) : (
                        <p className="font-['Lato'] font-medium text-sm text-ink">{bid.invoice_token || bid.invoice_id || `BID-${bid.id}`}</p>
                      )}
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
                    {isLeading && bid.face_value != null && (
                      <p className="font-['Lato'] text-xs">
                        <span className="text-teal">+{fmt(Number(bid.face_value) - Number(bid.amount))}</span>
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
                Total expected: +{fmt(activeBids.filter(b => b.is_leading || b.leading).reduce((s, b) => s + (b.face_value != null ? Number(b.face_value) - Number(b.amount) : 0), 0))}
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
                const totalPayout = Number(loan.principal || 0) + Number(loan.penalty_amount || 0)
                return (
                  <div key={loan.id || i} className="flex flex-col gap-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-['Lato'] font-medium text-sm text-ink">{loan.invoice_token || `LOAN-${loan.id}`}</p>
                        <p className="font-['Lato'] text-xs text-ink/40 mt-0.5">Due {fmtDate(loan.due_date)}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-['Lato'] font-medium text-sm text-ink">{fmt(totalPayout)} total payout</p>
                        {Number(loan.penalty_amount) > 0 && (
                          <p className="font-['Lato'] text-xs text-ink/40">{fmt(loan.penalty_amount)} penalty</p>
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

          {!loansLoading && loansCount > 0 && (
            <Link to="/repayments" className="self-start font-['Lato'] text-sm text-ink/40 hover:text-ink transition-colors flex items-center gap-1 mt-auto">
              View all repayments <ArrowRight size={13} />
            </Link>
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
