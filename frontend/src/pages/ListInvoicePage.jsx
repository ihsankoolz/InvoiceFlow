import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { UploadCloud, FileText, CheckCircle, AlertTriangle } from 'lucide-react'
import AppLayout from '../components/layout/AppLayout'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'

/* ── Animation ── */
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
  if (visible) return { animation: 'listFadeUp 600ms ease both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(20px)' }
}

const URGENCY_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

export default function ListInvoicePage() {
  const { user } = useAuth()
  const navigate  = useNavigate()

  const [file, setFile]                 = useState(null)
  const [dragOver, setDragOver]         = useState(false)
  const fileInputRef                    = useRef(null)

  const [debtorName, setDebtorName]     = useState('')
  const [debtorUen, setDebtorUen]       = useState('')
  const [faceValue, setFaceValue]       = useState('')
  const [minimumBid, setMinimumBid]     = useState('')
  const [dueDate, setDueDate]           = useState('')
  const [urgency, setUrgency]           = useState('MEDIUM')
  const [bidPeriod, setBidPeriod]       = useState('24')

  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState('')
  const [success, setSuccess]           = useState(false)

  const [headerRef, headerInView]       = useInView(0.05)
  const [formRef, formInView]           = useInView(0.05)

  function handleFileChange(e) {
    const f = e.target.files?.[0]
    if (f && f.type === 'application/pdf') setFile(f)
    else if (f) setError('Please upload a PDF file.')
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f && f.type === 'application/pdf') { setFile(f); setError('') }
    else setError('Please drop a PDF file.')
  }

  function validate() {
    if (!file) return 'Please upload the invoice PDF.'
    if (!debtorName.trim()) return 'Debtor company name is required.'
    if (!debtorUen.trim()) return 'Debtor UEN is required.'
    if (!faceValue || Number(faceValue) <= 0) return 'Face value must be a positive number.'
    if (!minimumBid || Number(minimumBid) <= 0) return 'Minimum bid must be a positive number.'
    if (Number(minimumBid) > Number(faceValue)) return 'Minimum bid cannot exceed face value.'
    if (!dueDate) return 'Invoice due date is required.'
    if (new Date(dueDate) <= new Date()) return 'Due date must be in the future.'
    if (!bidPeriod || Number(bidPeriod) < 1) return 'Bid period must be at least 1 hour.'
    return null
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    const err = validate()
    if (err) { setError(err); return }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('pdf', file)
      formData.append('seller_id', user.sub)
      formData.append('debtor_name', debtorName.trim())
      formData.append('debtor_uen', debtorUen.trim())
      formData.append('face_value', faceValue)
      formData.append('minimum_bid', minimumBid)
      formData.append('due_date', dueDate)
      formData.append('bid_period_hours', bidPeriod)

      await api.post('/invoices', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      setSuccess(true)
      setTimeout(() => navigate('/invoices'), 2000)
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.message || e.message || 'Failed to list invoice.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-full px-6 py-16">
          <div className="text-center">
            <CheckCircle size={56} className="text-[#3e9b00] mx-auto mb-4" />
            <h2 className="font-['Lato'] font-semibold text-2xl text-ink mb-2">Invoice Listed!</h2>
            <p className="font-['Lato'] text-sm text-ink/60">Redirecting to your invoices…</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <style>{`
        @keyframes listFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Header strip */}
      <div ref={headerRef} className="bg-teal px-8 py-10" style={fadeUp(headerInView, 0)}>
        <div className="max-w-5xl mx-auto">
          <h1 className="font-['Lato'] font-semibold text-[42px] text-white leading-tight">List an Invoice</h1>
          <p className="font-['Lato'] text-white/60 text-sm mt-1">Upload your invoice PDF and fill in the details</p>
        </div>
      </div>

      <div className="px-8 py-8 max-w-5xl mx-auto">

        {error && (
          <div style={fadeUp(headerInView, 60)} className="mb-6 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 font-['Lato'] text-sm flex items-start gap-2">
            <AlertTriangle size={15} className="mt-0.5 flex-shrink-0" />
            {error}
          </div>
        )}

        <form ref={formRef} onSubmit={handleSubmit} noValidate>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: PDF upload */}
            <div style={fadeUp(formInView, 0)}>
              <div className="bg-white border border-ink/10 rounded-[20px] p-6 h-full">
                <h2 className="font-['Lato'] font-semibold text-base text-ink mb-4">Invoice PDF</h2>

                {/* Drop zone */}
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-[20px] p-12 flex flex-col items-center justify-center cursor-pointer transition-colors duration-200 ${
                    dragOver
                      ? 'border-ink bg-ink/5'
                      : file
                        ? 'border-[#3e9b00] bg-[#e8f5e0]/50'
                        : 'border-ink/30 hover:border-ink/60'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={handleFileChange}
                  />

                  {file ? (
                    <>
                      <FileText size={40} className="text-[#3e9b00] mb-3" />
                      <p className="font-['Lato'] font-medium text-sm text-ink text-center break-all px-2">{file.name}</p>
                      <p className="font-['Lato'] text-xs text-ink/50 mt-1">
                        {(file.size / 1024).toFixed(1)} KB
                      </p>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); setFile(null) }}
                        className="mt-3 font-['Lato'] text-xs text-ink/50 hover:text-ink underline"
                      >
                        Remove
                      </button>
                    </>
                  ) : (
                    <>
                      <UploadCloud size={40} className="text-ink/30 mb-3" />
                      <p className="font-['Lato'] font-medium text-sm text-ink text-center">
                        Click to upload or drag & drop
                      </p>
                      <p className="font-['Lato'] text-xs text-ink/50 mt-1">PDF only</p>
                    </>
                  )}
                </div>

                <p className="font-['Lato'] text-xs text-ink/40 mt-3 text-center">
                  PDF fields will be extracted automatically
                </p>
              </div>
            </div>

            {/* Right: Invoice details form */}
            <div style={fadeUp(formInView, 80)}>
              <div className="bg-white border border-ink/10 rounded-[20px] p-6">
                <h2 className="font-['Lato'] font-semibold text-base text-ink mb-5">Invoice Details</h2>

                <div className="space-y-4">
                  {/* Debtor name */}
                  <div>
                    <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                      Debtor company name
                    </label>
                    <input
                      type="text"
                      value={debtorName}
                      onChange={(e) => setDebtorName(e.target.value)}
                      placeholder="e.g. Meridian Tech Solutions"
                      className="w-full border border-ink/30 rounded-lg px-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                    />
                  </div>

                  {/* Debtor UEN */}
                  <div>
                    <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                      Debtor UEN
                    </label>
                    <input
                      type="text"
                      value={debtorUen}
                      onChange={(e) => setDebtorUen(e.target.value)}
                      placeholder="e.g. 202056789A"
                      className="w-full border border-ink/30 rounded-lg px-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                    />
                    <p className="mt-0.5 font-['Lato'] text-xs text-ink/40">Validated against ACRA</p>
                  </div>

                  {/* Face value */}
                  <div>
                    <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                      Face value (SGD)
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 font-['Lato'] text-sm text-ink/50">$</span>
                      <input
                        type="number"
                        min="1"
                        step="0.01"
                        value={faceValue}
                        onChange={(e) => setFaceValue(e.target.value)}
                        placeholder="10000.00"
                        className="w-full border border-ink/30 rounded-lg pl-7 pr-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                      />
                    </div>
                  </div>

                  {/* Minimum bid */}
                  <div>
                    <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                      Minimum bid (SGD)
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 font-['Lato'] text-sm text-ink/50">$</span>
                      <input
                        type="number"
                        min="1"
                        step="0.01"
                        value={minimumBid}
                        onChange={(e) => setMinimumBid(e.target.value)}
                        placeholder="8500.00"
                        className="w-full border border-ink/30 rounded-lg pl-7 pr-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                      />
                    </div>
                  </div>

                  {/* Invoice due date */}
                  <div>
                    <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                      Invoice due date
                    </label>
                    <input
                      type="date"
                      value={dueDate}
                      onChange={(e) => setDueDate(e.target.value)}
                      min={new Date().toISOString().split('T')[0]}
                      className="w-full border border-ink/30 rounded-lg px-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                    />
                  </div>

                  {/* Urgency level */}
                  <div>
                    <label className="block font-['Lato'] text-sm font-medium text-ink mb-2">
                      Urgency level
                    </label>
                    <div className="grid grid-cols-4 gap-2">
                      {URGENCY_LEVELS.map((level) => (
                        <button
                          key={level}
                          type="button"
                          onClick={() => setUrgency(level)}
                          className={`px-2 py-2 rounded-lg font-['Lato'] text-xs font-semibold transition-colors duration-150 ${
                            urgency === level
                              ? 'bg-teal text-white'
                              : 'border border-ink/20 text-ink/70 hover:border-ink/40'
                          }`}
                        >
                          {level}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Bid period */}
                  <div>
                    <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                      Bid period (hours)
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="720"
                      value={bidPeriod}
                      onChange={(e) => setBidPeriod(e.target.value)}
                      className="w-full border border-ink/30 rounded-lg px-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Submit */}
          <div style={fadeUp(formInView, 160)} className="mt-6">
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-teal text-white rounded-lg px-6 py-3 font-['Lato'] font-semibold text-base hover:opacity-90 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? 'Listing Invoice…' : 'List Invoice'}
            </button>
          </div>
        </form>
      </div>
    </AppLayout>
  )
}
