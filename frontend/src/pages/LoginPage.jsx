import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'
import PublicNav from '../components/layout/PublicNav'

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [visible, setVisible]   = useState(false)

  useEffect(() => {
    if (user) navigate('/dashboard', { replace: true })
  }, [user, navigate])

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 60)
    return () => clearTimeout(t)
  }, [])

  function validate() {
    if (!email.trim()) return 'Email is required.'
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Please enter a valid email.'
    if (!password) return 'Password is required.'
    return null
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    const err = validate()
    if (err) { setError(err); return }

    setLoading(true)
    try {
      const res = await axios.post('/api/auth/login', { email: email.trim(), password })
      const token = res.data?.access_token || res.data?.token
      if (!token) throw new Error('No token received from server.')
      login(token)
      navigate('/dashboard', { replace: true })
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.message || e.message || 'Login failed. Please try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const fadeUpStyle = (delay = 0) =>
    visible
      ? { animation: `loginFadeUp 600ms ease both`, animationDelay: `${delay}ms` }
      : { opacity: 0, transform: 'translateY(20px)' }

  return (
    <div className="min-h-screen flex flex-col bg-cream">
      <style>{`
        @keyframes loginFadeUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <PublicNav />

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md" style={fadeUpStyle(100)}>
          <div className="bg-white border border-ink/10 rounded-[20px] p-10">
            <h1 className="font-display font-semibold text-[32px] text-ink mb-2 leading-tight">
              Welcome back
            </h1>
            <p className="font-['Lato'] text-sm text-ink/60 mb-8">
              Sign in to your InvoiceFlow account to continue.
            </p>

            {error && (
              <div className="mb-5 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 font-['Lato'] text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
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
                  style={{ background: 'rgba(255,252,247,0.7)' }}
                  className="w-full border border-ink/20 rounded-lg px-4 py-2.5 font-['Lato'] text-ink focus:outline-none focus:border-ink/60 focus:ring-2 focus:ring-ink/8 transition-all"
                />
              </div>

              <div>
                <label className="block font-['Lato'] text-sm font-medium text-ink mb-1">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    style={{ background: 'rgba(255,252,247,0.7)' }}
                    className="w-full border border-ink/20 rounded-lg px-4 py-2.5 pr-11 font-['Lato'] text-ink focus:outline-none focus:border-ink/60 focus:ring-2 focus:ring-ink/8 transition-all"
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

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-teal text-white rounded-lg px-6 py-3 font-['Lato'] font-semibold hover:opacity-90 active:scale-[0.98] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
              >
                {loading ? 'Signing in…' : 'Sign In'}
              </button>
            </form>

            <p className="mt-6 text-center font-['Lato'] text-sm text-ink/60">
              Don&apos;t have an account?{' '}
              <Link to="/register" className="text-ink font-semibold hover:underline">
                Get Started
              </Link>
            </p>
          </div>
        </div>
      </div>

    </div>
  )
}
