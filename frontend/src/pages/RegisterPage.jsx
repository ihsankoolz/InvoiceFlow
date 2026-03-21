import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import PublicNav from '../components/layout/PublicNav'

export default function RegisterPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [fullName, setFullName]   = useState('')
  const [email, setEmail]         = useState('')
  const [password, setPassword]   = useState('')
  const [showPw, setShowPw]       = useState(false)
  const [role, setRole]           = useState('SELLER')
  const [uen, setUen]             = useState('')
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const [success, setSuccess]     = useState('')
  const [visible, setVisible]     = useState(false)

  useEffect(() => {
    if (user) navigate('/dashboard', { replace: true })
  }, [user, navigate])

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 60)
    return () => clearTimeout(t)
  }, [])

  function validate() {
    if (!fullName.trim()) return 'Full name is required.'
    if (!email.trim()) return 'Email is required.'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Please enter a valid email.'
    if (password.length < 8) return 'Password must be at least 8 characters.'
    if (role === 'SELLER' && !uen.trim()) return 'UEN is required for seller accounts.'
    return null
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    const err = validate()
    if (err) { setError(err); return }

    setLoading(true)
    try {
      const payload = {
        email: email.trim(),
        password,
        full_name: fullName.trim(),
        role,
      }
      if (role === 'SELLER') payload.uen = uen.trim()

      await axios.post('/api/auth/register', payload)
      setSuccess('Account created! Please sign in.')
      setTimeout(() => navigate('/login'), 1500)
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.message || e.message || 'Registration failed. Please try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const fadeUpStyle = (delay = 0) =>
    visible
      ? { animation: `regFadeUp 600ms ease both`, animationDelay: `${delay}ms` }
      : { opacity: 0, transform: 'translateY(20px)' }

  return (
    <div className="relative min-h-screen bg-cream overflow-x-clip flex flex-col">
      <style>{`
        @keyframes regFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <PublicNav />

      {/* Main content */}
      <div className="relative flex-1 flex items-start justify-center px-4 pt-10 pb-16" style={{ zIndex: 1 }}>
        <div className="w-full max-w-md" style={fadeUpStyle(100)}>
          <div className="bg-white border border-ink/10 rounded-[20px] p-10">
            <h1 className="font-display font-semibold text-[32px] text-ink mb-2 leading-tight">
              Join InvoiceFlow
            </h1>
            <p className="font-['Lato'] text-sm text-ink/60 mb-8">
              Create your account and start financing invoices today.
            </p>

            {error && (
              <div className="mb-5 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 font-['Lato'] text-sm">
                {error}
              </div>
            )}
            {success && (
              <div className="mb-5 px-4 py-3 rounded-lg bg-[#e8f5e0] border border-[#3e9b00]/30 text-[#3e9b00] font-['Lato'] text-sm">
                {success}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              {/* Full name */}
              <div>
                <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                  Full name
                </label>
                <input
                  type="text"
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Jane Doe"
                  className="w-full border border-ink/30 rounded-lg px-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                />
              </div>

              {/* Email */}
              <div>
                <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                  Email address
                </label>
                <input
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="w-full border border-ink/30 rounded-lg px-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min. 8 characters"
                    className="w-full border border-ink/30 rounded-lg px-4 py-2.5 pr-11 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowPw((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-ink/40 hover:text-ink transition-colors"
                  >
                    {showPw ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>
              </div>

              {/* Role selector */}
              <div>
                <label className="block font-['Lato'] text-sm font-medium text-ink mb-2">
                  I am a…
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { value: 'SELLER',   label: 'Seller (Business)' },
                    { value: 'INVESTOR', label: 'Investor' },
                  ].map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setRole(value)}
                      className={`px-4 py-3 rounded-lg font-['Lato'] text-sm font-medium transition-colors duration-150 ${
                        role === value
                          ? 'bg-teal text-white'
                          : 'border border-teal text-teal hover:bg-teal/5'
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* UEN — only for SELLER */}
              {role === 'SELLER' && (
                <div>
                  <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                    Company UEN
                  </label>
                  <input
                    type="text"
                    value={uen}
                    onChange={(e) => setUen(e.target.value)}
                    placeholder="e.g. 202056789A"
                    className="w-full border border-ink/30 rounded-lg px-4 py-2.5 font-['Lato'] text-ink bg-white focus:outline-none focus:border-ink transition-colors"
                  />
                  <p className="mt-1 font-['Lato'] text-xs text-ink/50">
                    Your UEN will be validated against ACRA
                  </p>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-teal text-white rounded-lg px-6 py-2.5 font-['Lato'] font-semibold hover:opacity-90 transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed mt-2"
              >
                {loading ? 'Creating account…' : 'Create Account'}
              </button>
            </form>

            <p className="mt-6 text-center font-['Lato'] text-sm text-ink/60">
              Already have an account?{' '}
              <Link to="/login" className="text-ink font-semibold hover:underline">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>

      {/* Footer */}
    </div>
  )
}
