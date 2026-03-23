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
  { icon: LayoutDashboard, label: 'Home',          path: '/dashboard' },
  { icon: PlusCircle,      label: 'List Invoice', path: '/invoices/new' },
  { icon: FileText,        label: 'My Invoices',  path: '/invoices' },
  { icon: CreditCard,      label: 'Loans',        path: '/loans' },
  { icon: Bell,            label: 'Notifications',path: '/notifications' },
]

const INVESTOR_NAV = [
  { icon: LayoutDashboard, label: 'Home',          path: '/dashboard' },
  { icon: ShoppingCart,    label: 'Marketplace',  path: '/marketplace' },
  { icon: FileSpreadsheet, label: 'My Bids',      path: '/bids' },
  { icon: Wallet,          label: 'Wallet',       path: '/wallet' },
  { icon: Bell,            label: 'Notifications',path: '/notifications' },
]

export default function DashboardLayout({ children }) {
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
      <nav className="bg-white border-b border-black/8 flex items-center justify-between px-8 lg:px-10 h-[64px] flex-shrink-0 sticky top-0 z-10">

        {/* Logo */}
        <Link
          to="/dashboard"
          className="font-['Lato'] font-bold text-[20px] text-black hover:opacity-70 transition-opacity flex-shrink-0"
        >
          InvoiceFlow
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-1">
          {navItems.map(({ icon: Icon, label, path }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `flex items-center gap-2 px-4 py-2 rounded-lg font-['Lato'] text-sm font-medium transition-colors duration-150 ${
                  isActive
                    ? 'bg-black/6 text-black'
                    : 'text-black/50 hover:bg-black/4 hover:text-black'
                }`
              }
            >
              <Icon size={15} strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </div>

        {/* Right: user + logout */}
        <div className="flex items-center gap-4 flex-shrink-0">
          {user && (
            <p className="font-['Lato'] text-sm font-semibold text-black">{user.full_name}</p>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 font-['Lato'] text-sm text-black/50 hover:text-black transition-colors duration-200"
          >
            <LogOut size={15} strokeWidth={1.8} />
            Log out
          </button>
        </div>
      </nav>

      {/* ── Main content ── */}
      <main className="flex-1 bg-white overflow-auto">
        {children}
      </main>

    </div>
  )
}
