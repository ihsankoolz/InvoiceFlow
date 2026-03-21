import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Clock, ChevronDown, ArrowRight } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import Badge from '../components/ui/Badge'
import { fetchListings } from '../api/marketplace'

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
  if (visible) return { animation: 'mktFadeUp 600ms ease both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(20px)' }
}

/* ── Format helpers ── */
function fmt(n) {
  if (n == null) return '—'
  return `$${Number(n).toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function calcReturn(faceValue, bid) {
  const f = Number(faceValue)
  const b = Number(bid)
  if (!b || !f || b <= 0) return null
  return ((f - b) / b * 100).toFixed(1)
}

/* ── Countdown timer ── */
function useCountdown(deadline) {
  const [remaining, setRemaining] = useState('')
  useEffect(() => {
    function calc() {
      if (!deadline) { setRemaining('—'); return }
      const diff = new Date(deadline) - Date.now()
      if (diff <= 0) { setRemaining('Ended'); return }
      const days  = Math.floor(diff / 86400000)
      const hours = Math.floor((diff % 86400000) / 3600000)
      const mins  = Math.floor((diff % 3600000) / 60000)
      if (days > 0) setRemaining(`${days}d ${hours}h`)
      else if (hours > 0) setRemaining(`${hours}h ${mins}m`)
      else setRemaining(`${mins}m`)
    }
    calc()
    const id = setInterval(calc, 30000)
    return () => clearInterval(id)
  }, [deadline])
  return remaining
}

function CountdownBadge({ deadline }) {
  const remaining = useCountdown(deadline)
  return (
    <span className="flex items-center gap-1 font-['Lato'] text-xs text-ink/50">
      <Clock size={11} />
      {remaining}
    </span>
  )
}

/* ── Listing card ── */
function ListingCard({ listing, onBid, delay, inView }) {
  const ret = calcReturn(listing.face_value, listing.current_bid || listing.minimum_bid)
  return (
    <div
      className="bg-white border border-ink/10 rounded-[20px] overflow-hidden hover:shadow-md transition-shadow duration-200 flex flex-col"
      style={fadeUp(inView, delay)}
    >
      {/* Top accent */}
      <div className="bg-cream px-5 pt-5 pb-4 flex items-center justify-between">
        <Badge status={listing.urgency_level} />
        <CountdownBadge deadline={listing.deadline} />
      </div>

      <div className="px-5 py-4 flex flex-col gap-4 flex-1">
        {/* Invoice token */}
        <div>
          <p className="font-['Lato'] text-xs text-ink/40 mb-0.5">Invoice</p>
          <p className="font-['Lato'] font-semibold text-sm text-ink">{listing.invoice_token || listing.id}</p>
        </div>

        {/* Current bid + return */}
        <div className="flex items-end justify-between">
          <div>
            <p className="font-['Lato'] text-xs text-ink/40 mb-0.5">Current bid</p>
            <p className="font-display font-semibold text-[28px] text-ink leading-none">
              {fmt(listing.current_bid || listing.minimum_bid)}
            </p>
          </div>
          {ret && (
            <div className="bg-[#e8f5e0] rounded-lg px-2.5 py-1">
              <p className="font-['Lato'] text-xs font-semibold text-[#3e9b00]">+{ret}%</p>
            </div>
          )}
        </div>

        <div className="h-px bg-ink/6" />

        {/* Face value / Min bid */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs font-['Lato']">
            <span className="text-ink/40">Face value</span>
            <span className="font-medium text-ink">{fmt(listing.face_value)}</span>
          </div>
          <div className="flex justify-between text-xs font-['Lato']">
            <span className="text-ink/40">Min bid</span>
            <span className="font-medium text-ink">{fmt(listing.minimum_bid)}</span>
          </div>
        </div>

        <div className="h-px bg-ink/6" />

        {/* Debtor */}
        <div>
          <p className="font-['Lato'] text-sm font-medium text-ink truncate">{listing.debtor_name || '—'}</p>
          <p className="font-['Lato'] text-xs text-ink/40">{listing.debtor_uen || ''}</p>
        </div>

        {/* CTA */}
        <button
          onClick={() => onBid(listing.id)}
          className="mt-auto w-full bg-teal text-white rounded-[12px] px-4 py-3 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
        >
          Place Bid <ArrowRight size={14} />
        </button>
      </div>
    </div>
  )
}

/* ── Skeleton card ── */
function SkeletonCard() {
  return (
    <div className="bg-white border border-ink/10 rounded-[20px] overflow-hidden">
      <div className="bg-cream px-5 py-4 h-14 animate-pulse" />
      <div className="p-5 space-y-4">
        {[60, 80, 40, 60, 80].map((w, i) => (
          <div key={i} className="h-4 bg-ink/5 rounded" style={{ width: `${w}%` }} />
        ))}
      </div>
    </div>
  )
}

const URGENCY_OPTIONS = ['ALL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
const SORT_OPTIONS = [
  { value: 'deadline',   label: 'Deadline' },
  { value: 'face_value', label: 'Face Value' },
  { value: 'return',     label: 'Return' },
]

export default function MarketplacePage() {
  const navigate = useNavigate()

  const [listings, setListings] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  const [urgency, setUrgency]   = useState('ALL')
  const [search, setSearch]     = useState('')
  const [sortBy, setSortBy]     = useState('deadline')

  const [headerRef, headerInView] = useInView(0.05)
  const [gridRef, gridInView]     = useInView(0.05)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const data = await fetchListings({ urgency, search, sortBy })
      setListings(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(e.message || 'Failed to load listings.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [urgency, sortBy]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleSearchKeyDown(e) {
    if (e.key === 'Enter') load()
  }

  return (
    <AppLayout>
      <style>{`
        @keyframes mktFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* ── Header strip ── */}
      <div ref={headerRef} className="bg-teal px-8 py-10" style={fadeUp(headerInView, 0)}>
        <div className="max-w-7xl mx-auto">
          <h1 className="font-display font-semibold text-[42px] text-[#fff8ec] leading-tight">Marketplace</h1>
          <p className="font-['Lato'] text-[#fff8ec]/60 text-sm mt-1">Browse and bid on live invoice listings</p>
        </div>
      </div>

      <div className="px-8 py-8 max-w-7xl mx-auto">

        {/* Filter bar */}
        <div style={fadeUp(headerInView, 80)} className="flex flex-wrap gap-3 mb-8">
          {/* Urgency pills */}
          <div className="flex gap-2 flex-wrap">
            {URGENCY_OPTIONS.map((u) => (
              <button
                key={u}
                onClick={() => setUrgency(u)}
                className={`px-4 py-2 rounded-[22px] font-['Lato'] text-sm font-medium transition-colors duration-150 ${
                  urgency === u
                    ? 'bg-teal text-white'
                    : 'border border-ink/20 text-ink/70 hover:border-ink/50 hover:text-ink bg-white'
                }`}
              >
                {u === 'ALL' ? 'All' : u}
              </button>
            ))}
          </div>

          <div className="flex gap-3 ml-auto">
            {/* Search */}
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/40" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleSearchKeyDown}
                placeholder="Debtor or token…"
                className="border border-ink/20 rounded-[22px] pl-9 pr-4 py-2 font-['Lato'] text-sm text-ink bg-white focus:outline-none focus:border-ink/50 transition-colors w-52"
              />
            </div>

            {/* Sort */}
            <div className="relative">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="appearance-none border border-ink/20 rounded-[22px] px-4 py-2 pr-8 font-['Lato'] text-sm text-ink bg-white focus:outline-none focus:border-ink/50 transition-colors cursor-pointer"
              >
                {SORT_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>Sort: {s.label}</option>
                ))}
              </select>
              <ChevronDown size={13} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink/40 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 px-4 py-3 rounded-[12px] bg-red-50 border border-red-200 text-red-700 font-['Lato'] text-sm">
            {error}
          </div>
        )}

        {/* Grid */}
        <div ref={gridRef} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {loading
            ? [...Array(6)].map((_, i) => <SkeletonCard key={i} />)
            : listings.length === 0
              ? (
                <div className="col-span-full text-center py-24">
                  <Search size={40} className="text-ink/15 mx-auto mb-4" />
                  <p className="font-display text-2xl text-ink/30">No listings found</p>
                  <p className="font-['Lato'] text-sm text-ink/25 mt-1">Try adjusting your filters</p>
                </div>
              )
              : listings.map((listing, i) => (
                <ListingCard
                  key={listing.id}
                  listing={listing}
                  onBid={(id) => navigate(`/marketplace/${id}`)}
                  delay={i * 50}
                  inView={gridInView}
                />
              ))
          }
        </div>
      </div>
    </AppLayout>
  )
}
