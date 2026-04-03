import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'

const LandingPage        = lazy(() => import('./pages/LandingPage'))
const LoginPage          = lazy(() => import('./pages/LoginPage'))
const RegisterPage       = lazy(() => import('./pages/RegisterPage'))
const DashboardPage      = lazy(() => import('./pages/DashboardPage'))
const MarketplacePage    = lazy(() => import('./pages/MarketplacePage'))
const ListingDetailPage  = lazy(() => import('./pages/ListingDetailPage'))
const ListInvoicePage    = lazy(() => import('./pages/ListInvoicePage'))
const MyInvoicesPage     = lazy(() => import('./pages/MyInvoicesPage'))
const MyBidsPage         = lazy(() => import('./pages/MyBidsPage'))
const WalletPage         = lazy(() => import('./pages/WalletPage'))
const LoansPage          = lazy(() => import('./pages/LoansPage'))
const NotificationsPage  = lazy(() => import('./pages/NotificationsPage'))
const PaymentSuccessPage = lazy(() => import('./pages/PaymentSuccessPage'))

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <div className="font-['Lato'] text-ink">Loading...</div>
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return children
}

function AppRoutes() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-cream flex items-center justify-center">
        <div className="font-['Lato'] text-ink">Loading...</div>
      </div>
    }>
      <Routes>
      {/* Public routes */}
      <Route path="/"         element={<LandingPage />} />
      <Route path="/login"    element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Protected routes */}
      <Route path="/dashboard" element={
        <ProtectedRoute><DashboardPage /></ProtectedRoute>
      } />
      <Route path="/marketplace" element={
        <ProtectedRoute><MarketplacePage /></ProtectedRoute>
      } />
      <Route path="/marketplace/:id" element={
        <ProtectedRoute><ListingDetailPage /></ProtectedRoute>
      } />
      <Route path="/invoices/new" element={
        <ProtectedRoute><ListInvoicePage /></ProtectedRoute>
      } />
      <Route path="/invoices" element={
        <ProtectedRoute><MyInvoicesPage /></ProtectedRoute>
      } />
      <Route path="/bids" element={
        <ProtectedRoute><MyBidsPage /></ProtectedRoute>
      } />
      <Route path="/wallet" element={
        <ProtectedRoute><WalletPage /></ProtectedRoute>
      } />
      <Route path="/loans" element={
        <ProtectedRoute><LoansPage /></ProtectedRoute>
      } />
      <Route path="/notifications" element={
        <ProtectedRoute><NotificationsPage /></ProtectedRoute>
      } />

      {/* Stripe payment return routes */}
      <Route path="/payment/success" element={<PaymentSuccessPage />} />
      <Route path="/payment/cancel"  element={<Navigate to="/wallet" replace />} />

      {/* Catch-all: redirect to landing */}
      <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
