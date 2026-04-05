import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { NotificationProvider } from './context/NotificationContext'
import ToastContainer from './components/notifications/ToastContainer'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import MarketplacePage from './pages/MarketplacePage'
import ListingDetailPage from './pages/ListingDetailPage'
import ListInvoicePage from './pages/ListInvoicePage'
import MyInvoicesPage from './pages/MyInvoicesPage'
import MyBidsPage from './pages/MyBidsPage'
import WalletPage from './pages/WalletPage'
import LoansPage from './pages/LoansPage'
import RepaymentsPage from './pages/RepaymentsPage'
import NotificationsPage from './pages/NotificationsPage'
import PaymentSuccessPage from './pages/PaymentSuccessPage'

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
      <Route path="/repayments" element={
        <ProtectedRoute><RepaymentsPage /></ProtectedRoute>
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
  )
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <NotificationProvider>
          <AppRoutes />
          <ToastContainer />
        </NotificationProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
