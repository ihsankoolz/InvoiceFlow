import AppNav from './AppNav'

export default function DashboardLayout({ children }) {
  return (
    <div className="min-h-screen flex flex-col font-['Lato'] bg-white">
      <AppNav />
      <main className="flex-1 bg-white overflow-auto">
        {children}
      </main>
    </div>
  )
}
