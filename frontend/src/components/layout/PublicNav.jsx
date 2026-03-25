import { Link, useLocation } from 'react-router-dom'

export default function PublicNav() {
  const { pathname } = useLocation()
  const isLogin    = pathname === '/login'
  const isRegister = pathname === '/register'
  const isLanding  = pathname === '/'

  return (
    <nav className={`flex items-center justify-between px-8 lg:px-10 bg-white flex-shrink-0 h-[64px] ${isLanding ? '' : 'sticky top-0 z-10'}`}>
      <Link
        to="/"
        className="font-['Lato'] font-bold text-[20px] text-black hover:opacity-70 transition-opacity"
      >
        InvoiceFlow
      </Link>

      <div className="flex items-center gap-4">
        {!isLogin && (
          <Link
            to="/login"
            className="font-['Lato'] font-medium text-sm text-black/60 hover:text-black transition-colors duration-150"
          >
            Log in
          </Link>
        )}
        {!isRegister && (
          <Link
            to="/register"
            className="bg-teal text-white font-['Lato'] font-semibold text-sm px-4 py-2 rounded-[22px] hover:opacity-90 transition-opacity duration-200"
          >
            Sign up
          </Link>
        )}
      </div>
    </nav>
  )
}
