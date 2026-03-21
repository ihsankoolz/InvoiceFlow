import { Link, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  PlusCircle,
  FileText,
  CreditCard,
  Bell,
  ShoppingCart,
  FileSpreadsheet,
  Wallet,
  LogOut,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'

const SELLER_NAV = [
  { icon: LayoutDashboard, label: 'Dashboard',    path: '/dashboard' },
  { icon: PlusCircle,      label: 'List Invoice', path: '/invoices/new' },
  { icon: FileText,        label: 'My Invoices',  path: '/invoices' },
  { icon: CreditCard,      label: 'Loans',        path: '/loans' },
  { icon: Bell,            label: 'Notifications',path: '/notifications' },
]

const INVESTOR_NAV = [
  { icon: LayoutDashboard, label: 'Dashboard',    path: '/dashboard' },
  { icon: ShoppingCart,    label: 'Marketplace',  path: '/marketplace' },
  { icon: FileSpreadsheet, label: 'My Bids',      path: '/bids' },
  { icon: Wallet,          label: 'Wallet',       path: '/wallet' },
  { icon: Bell,            label: 'Notifications',path: '/notifications' },
]

export default function AppLayout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const navItems = user?.role === 'INVESTOR' ? INVESTOR_NAV : SELLER_NAV

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen flex flex-col font-['Lato']">

      {/* ── Top Navbar ── */}
      <nav className="flex items-center justify-between px-4 sm:px-8 lg:px-10 py-4 bg-teal flex-shrink-0">
        <Link
          to="/dashboard"
          className="font-['Lato'] font-bold text-[22px] text-[#fff8ec] hover:opacity-80 transition-opacity"
        >
          InvoiceFlow
        </Link>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 font-['Lato'] font-semibold text-base text-[#fff8ec]/80 hover:text-[#fff8ec] transition-colors duration-200"
        >
          <LogOut size={17} strokeWidth={1.8} />
          Log Out
        </button>
      </nav>

      {/* ── Body: sidebar + content ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Sidebar ── */}
        <aside className="w-56 bg-teal flex flex-col flex-shrink-0">
          {user && (
            <div className="px-5 py-4 border-b border-white/10">
              <p className="font-['Lato'] text-sm font-semibold text-[#fff8ec] leading-tight truncate">
                {user.full_name}
              </p>
              <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-[11px] font-['Lato'] font-semibold bg-white/10 text-[#fff8ec]">
                {user.role}
              </span>
            </div>
          )}
          <nav className="flex-1 py-4 overflow-y-auto">
            {navItems.map(({ icon: Icon, label, path }) => (
              <NavLink
                key={path}
                to={path}
                className={({ isActive }) =>
                  `flex items-center gap-3 mx-3 my-0.5 px-4 py-2.5 rounded-lg font-['Lato'] text-sm font-medium transition-colors duration-150 ${
                    isActive
                      ? 'bg-white/10 text-[#fff8ec]'
                      : 'text-[#fff8ec]/70 hover:bg-white/5 hover:text-[#fff8ec]'
                  }`
                }
              >
                <Icon size={17} strokeWidth={1.8} />
                {label}
              </NavLink>
            ))}
          </nav>
        </aside>

        {/* ── Main content ── */}
        <main className="flex-1 bg-cream overflow-auto">
          {children}
        </main>

      </div>
    </div>
  )
}
