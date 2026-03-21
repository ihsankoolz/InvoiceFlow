import { Link, useLocation } from 'react-router-dom'

export default function PublicNav({ style }) {
  const { pathname } = useLocation()
  const isLogin    = pathname === '/login'
  const isRegister = pathname === '/register'

  return (
    <nav
      className="relative flex items-center justify-between px-8 lg:px-16 py-5 bg-white whitespace-nowrap"
      style={{ zIndex: 2, ...style }}
    >
      <Link
        to="/"
        className="font-['Lato'] font-bold text-2xl text-black hover:opacity-80 transition-opacity"
      >
        InvoiceFlow
      </Link>

      <div className="flex items-center gap-8">
        {!isLogin && (
          <Link
            to="/login"
            className="font-['Lato'] font-bold text-base text-black hover:opacity-70 transition-opacity duration-200"
          >
            Log in
          </Link>
        )}
        {!isRegister && (
          <Link
            to="/register"
            className="bg-teal text-white font-['Lato'] font-semibold text-base px-7 py-2 rounded-[20px] hover:opacity-90 transition-opacity duration-200"
          >
            Sign up
          </Link>
        )}
      </div>
    </nav>
  )
}
