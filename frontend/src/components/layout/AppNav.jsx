import { Link, NavLink, useNavigate } from 'react-router-dom'
import {
  Home,
  PlusCircle,
  FileText,
  CreditCard,
  Bell,
  ShoppingCart,
  FileSpreadsheet,
  Wallet,
  Store,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { useNotifications } from '../../context/NotificationContext'

const SELLER_NAV = [
  { icon: Home,            label: 'Home',          path: '/dashboard' },
  { icon: PlusCircle,      label: 'List Invoice',  path: '/invoices/new' },
  { icon: FileText,        label: 'My Invoices',   path: '/invoices' },
  { icon: Store,           label: 'Marketplace',   path: '/marketplace' },
  { icon: CreditCard,      label: 'Loans',         path: '/loans' },
  { icon: Bell,            label: 'Notifications', path: '/notifications' },
]

const INVESTOR_NAV = [
  { icon: Home,            label: 'Home',          path: '/dashboard' },
  { icon: ShoppingCart,    label: 'Marketplace',   path: '/marketplace' },
  { icon: FileSpreadsheet, label: 'My Bids',       path: '/bids' },
  { icon: CreditCard,      label: 'Repayments',    path: '/repayments' },
  { icon: Wallet,          label: 'Wallet',        path: '/wallet' },
  { icon: Bell,            label: 'Notifications', path: '/notifications' },
]

export default function AppNav() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { unreadCount } = useNotifications()

  const navItems = user?.role === 'INVESTOR' ? INVESTOR_NAV : SELLER_NAV

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <nav className="flex items-center justify-between px-8 lg:px-10 bg-white border-b border-black/8 flex-shrink-0 h-[64px] sticky top-0 z-10">

      {/* Logo */}
      <div className="flex-1">
        <Link
          to="/dashboard"
          className="font-['Lato'] font-bold text-[20px] text-black hover:opacity-70 transition-opacity"
        >
          InvoiceFlow
        </Link>
      </div>

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
            {label === 'Notifications' && unreadCount > 0 && (
              <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] rounded-full bg-[#ff9500] text-white font-['Lato'] text-[10px] font-bold px-1 leading-none">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </NavLink>
        ))}
      </div>

      {/* Right: user + logout */}
      <div className="flex-1 flex items-center justify-end gap-4">
        {user && (
          <p className="font-['Lato'] text-sm font-semibold text-black">{user.full_name}</p>
        )}
        <button
          onClick={handleLogout}
          className="bg-teal text-white font-['Lato'] text-sm font-semibold px-4 py-2 rounded-[22px] hover:opacity-90 transition-opacity"
        >
          Log out
        </button>
      </div>
    </nav>
  )
}
