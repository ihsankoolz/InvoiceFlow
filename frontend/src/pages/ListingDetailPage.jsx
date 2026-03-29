import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Clock, AlertTriangle, TrendingUp, Shield } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import Badge from '../components/ui/Badge'
import api from '../api/axios'
import { fetchListing } from '../api/marketplace'
import { useAuth } from '../context/AuthContext'

/* ── Animation ── */
function fadeUp(visible, delay = 0) {
  if (visible) return { animation: 'detailFadeUp 600ms ease both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(20px)' }
}

/* ── Format helpers ── */
function fmt(n) {
  if (n == null) return '—'
  return `$${Number(n).toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtDate(str) {
  if (!str) return '—'
  return new Date(str).toLocaleDateString('en-SG', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

/* ── Live countdown ── */
function useLiveCountdown(deadline) {
  const [parts, setParts] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0, ended: false })

  useEffect(() => {
    function calc() {
      if (!deadline) return
      const diff = new Date(deadline) - Date.now()
      if (diff <= 0) { setParts({ days: 0, hours: 0, minutes: 0, seconds: 0, ended: true }); return }
      setParts({
        days:    Math.floor(diff / 86400000),
        hours:   Math.floor((diff % 86400000) / 3600000),
        minutes: Math.floor((diff % 3600000) / 60000),
        seconds: Math.floor((diff % 60000) / 1000),
        ended:   false,
      })
    }
    calc()
    const id = setInterval(calc, 1000)
    return () => clearInterval(id)
  }, [deadline])

  return parts
}

function CountdownDisplay({ deadline }) {
  const { days, hours, minutes, seconds, ended } = useLiveCountdown(deadline)

  if (ended) return <span className="font-['Lato'] text-sm text-red-600 font-semibold">Auction ended</span>

  return (
    <div className="flex items-center gap-3">
      {[
        { val: days,    label: 'd' },
        { val: hours,   label: 'h' },
        { val: minutes, label: 'm' },
        { val: seconds, label: 's' },
      ].map(({ val, label }) => (
        <div key={label} className="text-center">
          <div className="bg-cream border border-ink/10 rounded-lg px-3 py-1.5 min-w-[44px]">
            <span className="font-['Lato'] font-semibold text-xl text-ink">{String(val).padStart(2, '0')}</span>
          </div>
          <span className="font-['Lato'] text-[10px] text-ink/50 mt-0.5 block">{label}</span>
        </div>
      ))}
    </div>
  )
}

/* ── Detail row ── */
function DetailRow({ label, value }) {
  return (
    <div className="flex justify-between items-start py-2.5 border-b border-ink/5 last:border-0">
      <span className="font-['Lato'] text-sm text-ink/60 flex-shrink-0 w-36">{label}</span>
      <span className="font-['Lato'] text-sm text-ink font-medium text-right">{value}</span>
    </div>
  )
}

function parseBidError(raw) {
  if (!raw || typeof raw !== 'string') return 'Failed to place bid. Please try again.'

  // Insufficient wallet balance (gRPC escrow error)
  const balanceMatch = raw.match(/have (\d+(?:\.\d+)?),\s*need (\d+(?:\.\d+)?)/i)
  if (balanceMatch) {
    const have = Number(balanceMatch[1])
    const need = Number(balanceMatch[2])
    return `Insufficient wallet balance. You have ${fmt(have)} but need ${fmt(need)} to place this bid. Please top up your wallet.`
  }

  // Auction already closed / outbid
  if (/auction.*closed|listing.*closed|expired/i.test(raw)) return 'This auction has already closed.'
  if (/already.*higher bid|outbid/i.test(raw)) return 'A higher bid already exists. Please increase your bid amount.'
  if (/below.*minimum|minimum.*bid/i.test(raw)) return 'Your bid is below the minimum required amount.'

  // Strip raw gRPC / AioRpcError noise
  if (/<AioRpcError|StatusCode\.|debug_error_string/i.test(raw)) {
    const details = raw.match(/details\s*=\s*"([^"]+)"/i)
    if (details) return details[1]
    return 'An error occurred while placing your bid. Please try again.'
  }

  return raw
}

export default function ListingDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [listing, setListing]   = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  const [bidAmount, setBidAmount] = useState('')
  const [bidLoading, setBidLoading] = useState(false)
  const [bidError, setBidError]   = useState('')
  const [bidSuccess, setBidSuccess] = useState('')
  const [showConfirm, setShowConfirm] = useState(false)

  const [visible, setVisible]   = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 60)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError('')
      try {
        const data = await fetchListing(id)
        if (!data) throw new Error('Listing not found.')
        setListing(data)
        setBidAmount(data.current_bid ? String(Number(data.current_bid) + 1) : String(data.minimum_bid || ''))
      } catch (e) {
        setError(e.message || 'Failed to load listing.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  const estimatedReturn = (() => {
    if (!listing || !bidAmount) return null
    const b = Number(bidAmount)
    const f = Number(listing.face_value)
    if (!b || !f || b <= 0 || b >= f) return null
    return ((f - b) / b * 100).toFixed(1)
  })()

  function handleBid(e) {
    e.preventDefault()
    setBidError('')
    setBidSuccess('')

    const amount = Number(bidAmount)
    if (!amount || amount <= 0) { setBidError('Please enter a valid bid amount.'); return }
    if (listing.minimum_bid && amount < Number(listing.minimum_bid)) {
      setBidError(`Bid must be at least ${fmt(listing.minimum_bid)}.`)
      return
    }
    if (listing.face_value && amount > Number(listing.face_value)) {
      setBidError(`Bid cannot exceed face value of ${fmt(listing.face_value)}.`)
      return
    }

    setShowConfirm(true)
  }

  async function confirmBid() {
    setShowConfirm(false)
    setBidLoading(true)
    const amount = Number(bidAmount)
    try {
      await api.post('/bids', {
        listing_id: listing.id,
        bid_amount: amount,
        invoice_token: listing.invoice_token,
        investor_id: user.sub,
      })
      setBidSuccess('Bid placed successfully!')
      const updated = await fetchListing(id)
      if (updated) setListing(updated)
    } catch (e) {
      const detail = e.response?.data?.detail
      const raw = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : (detail || e.response?.data?.message || e.message || '')
      setBidError(parseBidError(raw))
    } finally {
      setBidLoading(false)
    }
  }

  const isInvestor = user?.role === 'INVESTOR'

  const confirmAmount = Number(bidAmount)
  const confirmReturn = listing && confirmAmount && Number(listing.face_value)
    ? ((Number(listing.face_value) - confirmAmount) / confirmAmount * 100).toFixed(1)
    : null

  return (
    <AppLayout>
      <style>{`
        @keyframes detailFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* ── Bid confirmation modal ── */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={() => setShowConfirm(false)} />
          <div className="relative bg-white rounded-[20px] shadow-xl w-full max-w-sm p-7" style={{ animation: 'detailFadeUp 200ms ease both' }}>
            <h3 className="font-['Lato'] font-semibold text-xl text-ink mb-1">Confirm your bid</h3>
            <p className="font-['Lato'] text-sm text-ink/50 mb-6">Please review before submitting — bids cannot be withdrawn.</p>

            <div className="bg-cream rounded-[14px] p-4 space-y-2 mb-6">
              <div className="flex justify-between">
                <span className="font-['Lato'] text-sm text-ink/60">Bid amount</span>
                <span className="font-['Lato'] font-semibold text-ink">{fmt(confirmAmount)}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-['Lato'] text-sm text-ink/60">Face value</span>
                <span className="font-['Lato'] text-sm text-ink">{fmt(listing.face_value)}</span>
              </div>
              {confirmReturn && (
                <div className="flex justify-between pt-2 border-t border-ink/10">
                  <span className="font-['Lato'] text-sm text-ink/60">Estimated return</span>
                  <span className="font-['Lato'] font-semibold text-[#3e9b00]">+{confirmReturn}%</span>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 border border-ink/20 text-ink rounded-lg px-4 py-2.5 font-['Lato'] font-medium text-sm hover:border-ink/40 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmBid}
                className="flex-1 bg-teal text-white rounded-lg px-4 py-2.5 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity"
              >
                Confirm Bid
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header strip */}
      <div className="bg-teal px-8 py-6" style={fadeUp(visible, 0)}>
        <div className="max-w-6xl mx-auto">
          <button
            onClick={() => navigate(-1)}
            className="font-['Lato'] text-sm text-white/60 hover:text-white transition-colors flex items-center gap-1"
          >
            ← Back to Marketplace
          </button>
        </div>
      </div>

      <div className="px-8 py-8 max-w-6xl mx-auto">

        {loading ? (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3 bg-white border border-ink/10 rounded-[20px] p-8 space-y-4">
              {[80, 60, 100, 60, 80, 60].map((w, i) => (
                <div key={i} className="h-5 bg-ink/5 rounded animate-pulse" style={{ width: `${w}%` }} />
              ))}
            </div>
            <div className="lg:col-span-2 bg-white border border-ink/10 rounded-[20px] p-8 space-y-4">
              {[60, 80, 40, 60].map((w, i) => (
                <div key={i} className="h-5 bg-ink/5 rounded animate-pulse" style={{ width: `${w}%` }} />
              ))}
            </div>
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <AlertTriangle size={40} className="text-red-400 mx-auto mb-3" />
            <p className="font-['Lato'] text-ink/60">{error}</p>
          </div>
        ) : listing ? (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Left: listing details */}
            <div className="lg:col-span-3" style={fadeUp(visible, 80)}>
              <div className="bg-white border border-ink/10 rounded-[20px] overflow-hidden">
                {/* Header */}
                <div className="bg-cream px-8 py-6 flex items-start justify-between gap-4">
                  <div>
                    <p className="font-['Lato'] text-xs text-ink/40 mb-1">Invoice</p>
                    <h1 className="font-['Lato'] font-semibold text-[32px] text-ink leading-tight">{listing.invoice_token || listing.id}</h1>
                  </div>
                  <Badge status={listing.status} />
                </div>
                <div className="px-8 py-6">

                {/* Countdown */}
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <Clock size={15} className="text-ink/50" />
                    <span className="font-['Lato'] text-sm text-ink/60">Time remaining</span>
                  </div>
                  <CountdownDisplay deadline={listing.deadline} />
                </div>

                <div className="h-px bg-ink/10 mb-6" />

                {/* Details */}
                <div>
                  <DetailRow label="Face Value"    value={fmt(listing.face_value)} />
                  <DetailRow label="Minimum Bid"   value={fmt(listing.minimum_bid)} />
                  <DetailRow label="Current Bid"   value={fmt(listing.current_bid)} />
                  <DetailRow label="Bid Count"     value={listing.bid_count ?? '0'} />
                  <DetailRow label="Urgency"       value={<Badge status={listing.urgency_level} />} />
                  <DetailRow label="Deadline"      value={fmtDate(listing.deadline)} />
                  <DetailRow label="Listed"        value={fmtDate(listing.created_at)} />
                </div>

                <div className="h-px bg-ink/10 my-6" />

                {/* Debtor info */}
                <div>
                  <p className="font-['Lato'] font-semibold text-sm text-ink mb-3">Debtor Information</p>
                  <DetailRow label="Company"       value={listing.debtor_name || '—'} />
                  <DetailRow label="UEN"           value={listing.debtor_uen || '—'} />
                </div>
                </div>
              </div>
            </div>

            {/* Right: bid placement */}
            <div className="lg:col-span-2" style={fadeUp(visible, 160)}>
              <div className="bg-white border border-ink/10 rounded-[20px] p-8 sticky top-6">
                <h2 className="font-['Lato'] font-semibold text-xl text-ink mb-5">
                  {isInvestor ? 'Place a Bid' : 'Bid Information'}
                </h2>

                {/* Current highest bid */}
                <div className="bg-cream rounded-[14px] p-4 mb-5">
                  <p className="font-['Lato'] text-xs text-ink/50 mb-1">Current highest bid</p>
                  <p className="font-['Lato'] font-semibold text-3xl text-ink">
                    {fmt(listing.current_bid || listing.minimum_bid)}
                  </p>
                  {listing.current_bid && listing.face_value && (
                    <p className="font-['Lato'] text-sm text-[#3e9b00] mt-1">
                      +{((Number(listing.face_value) - Number(listing.current_bid)) / Number(listing.current_bid) * 100).toFixed(1)}% return
                    </p>
                  )}
                </div>

                {isInvestor ? (
                  <>
                    {bidSuccess && (
                      <div className="mb-4 px-4 py-3 rounded-lg bg-[#e8f5e0] border border-[#3e9b00]/30 text-[#3e9b00] font-['Lato'] text-sm">
                        {bidSuccess}
                      </div>
                    )}
                    {bidError && (
                      <div className="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 font-['Lato'] text-sm">
                        {bidError}
                      </div>
                    )}

                    <form onSubmit={handleBid} className="space-y-4">
                      <div>
                        <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                          Your bid amount (SGD)
                        </label>
                        <div className="relative">
                          <span className="absolute left-3 top-1/2 -translate-y-1/2 font-['Lato'] text-sm text-ink/50">$</span>
                          <input
                            type="number"
                            min={listing.minimum_bid}
                            max={listing.face_value}
                            step="0.01"
                            value={bidAmount}
                            onChange={(e) => setBidAmount(e.target.value)}
                            className="w-full border border-ink/30 rounded-lg pl-7 pr-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                          />
                        </div>
                        <p className="mt-1 font-['Lato'] text-xs text-ink/50">
                          Min: {fmt(listing.minimum_bid)}
                        </p>
                      </div>

                      {/* Estimated return */}
                      {estimatedReturn && (
                        <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-[#e8f5e0]">
                          <TrendingUp size={15} className="text-[#3e9b00]" />
                          <span className="font-['Lato'] text-sm text-[#3e9b00] font-medium">
                            Estimated return: +{estimatedReturn}%
                          </span>
                        </div>
                      )}

                      {/* Anti-snipe note */}
                      <div className="flex items-start gap-2 px-4 py-3 rounded-lg bg-[#fff3e0]">
                        <Shield size={14} className="text-[#ff9500] mt-0.5 flex-shrink-0" />
                        <p className="font-['Lato'] text-xs text-ink/70">
                          Bids in the last 5 minutes extend the auction by 5 minutes.
                        </p>
                      </div>

                      <button
                        type="submit"
                        disabled={bidLoading || listing.status !== 'LISTED' && listing.status !== 'ACTIVE'}
                        className="w-full bg-teal text-white rounded-lg px-6 py-2.5 font-['Lato'] font-semibold hover:opacity-90 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
                      >
                        {bidLoading ? 'Placing bid…' : 'Place Bid'}
                      </button>
                    </form>
                  </>
                ) : (
                  <div className="px-4 py-3 rounded-lg bg-[#fff3e0] border border-[#ff9500]/30">
                    <p className="font-['Lato'] text-sm text-ink/70">
                      Only investors can place bids on listings.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </AppLayout>
  )
}
