import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { FileText, ExternalLink } from 'lucide-react'
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
  if (visible) return { animation: 'invFadeUp 600ms ease both', animationDelay: `${delay}ms` }
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

const STATUS_TABS = ['ALL', 'DRAFT', 'LISTED', 'FINANCED', 'REPAID', 'DEFAULTED']

export default function MyInvoicesPage() {
  const { user } = useAuth()

  const [invoices, setInvoices]       = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState('')
  const [activeTab, setActiveTab]     = useState('ALL')

  const [headerRef, headerInView]     = useInView(0.05)
  const [tableRef, tableInView]       = useInView(0.05)

  useEffect(() => {
    if (!user) return
    async function load() {
      setLoading(true)
      setError('')
      try {
        const res = await api.get(`/invoices?seller_id=${user.sub}`)
        const data = res.data?.invoices || res.data || []
        setInvoices(Array.isArray(data) ? data : [])
      } catch (e) {
        setError(e.response?.data?.detail || e.message || 'Failed to load invoices.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user])

  const filtered = activeTab === 'ALL'
    ? invoices
    : invoices.filter((i) => i.status === activeTab)

  return (
    <AppLayout>
      <style>{`
        @keyframes invFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Header strip */}
      <div ref={headerRef} className="bg-teal px-8 py-10" style={fadeUp(headerInView, 0)}>
        <div className="max-w-6xl mx-auto flex items-end justify-between">
          <div>
            <h1 className="font-['Lato'] font-semibold text-[42px] text-white leading-tight">My Invoices</h1>
            <p className="font-['Lato'] text-white/60 text-sm mt-1">Track and manage all your listed invoices</p>
          </div>
          <Link
            to="/invoices/new"
            className="flex items-center gap-2 bg-[#fff8ec] text-teal rounded-[22px] px-6 py-3 font-['Lato'] font-semibold text-sm hover:opacity-90 transition-opacity"
          >
            + List Invoice
          </Link>
        </div>
      </div>

      <div className="px-8 py-8 max-w-6xl mx-auto">
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
                <FileText size={44} className="text-ink/20 mx-auto mb-3" />
                <p className="font-['Lato'] font-medium text-ink/40 mb-1">No invoices found</p>
                <p className="font-['Lato'] text-sm text-ink/30">
                  {activeTab === 'ALL' ? "You haven't listed any invoices yet." : `No invoices with status "${activeTab}".`}
                </p>
                {activeTab === 'ALL' && (
                  <Link
                    to="/invoices/new"
                    className="inline-block mt-4 bg-teal text-white rounded-lg px-5 py-2 font-['Lato'] text-sm font-semibold hover:opacity-90 transition-all"
                  >
                    List an Invoice
                  </Link>
                )}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm font-['Lato']">
                  <thead>
                    <tr className="border-b border-ink/10 bg-cream/50">
                      <th className="text-left px-6 py-3 font-medium text-ink/60">Invoice Token</th>
                      <th className="text-left px-4 py-3 font-medium text-ink/60">Debtor</th>
                      <th className="text-right px-4 py-3 font-medium text-ink/60">Face Value</th>
                      <th className="text-right px-4 py-3 font-medium text-ink/60">Current Bid</th>
                      <th className="text-center px-4 py-3 font-medium text-ink/60">Status</th>
                      <th className="text-left px-4 py-3 font-medium text-ink/60">Deadline</th>
                      <th className="text-center px-6 py-3 font-medium text-ink/60">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((inv, i) => (
                      <tr
                        key={inv.id}
                        className="border-b border-ink/5 hover:bg-cream transition-colors"
                        style={fadeUp(tableInView, i * 40)}
                      >
                        <td className="px-6 py-3 font-medium text-ink">{inv.invoice_token || inv.id}</td>
                        <td className="px-4 py-3 text-ink/70">{inv.debtor_name || '—'}</td>
                        <td className="px-4 py-3 text-right text-ink">{fmt(inv.face_value)}</td>
                        <td className="px-4 py-3 text-right text-ink">{fmt(inv.current_bid)}</td>
                        <td className="px-4 py-3 text-center">
                          <Badge status={inv.status} />
                        </td>
                        <td className="px-4 py-3 text-ink/60">{fmtDate(inv.deadline)}</td>
                        <td className="px-6 py-3 text-center">
                          {inv.status === 'LISTED' && inv.invoice_id ? (
                            <Link
                              to={`/marketplace/${inv.invoice_id}`}
                              className="inline-flex items-center gap-1 font-['Lato'] text-xs font-medium text-ink hover:text-[#ff9500] transition-colors"
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
