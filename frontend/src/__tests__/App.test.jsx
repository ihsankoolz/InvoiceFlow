import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ErrorBoundary from '../components/ErrorBoundary'

// ── ErrorBoundary ────────────────────────────────────────────────────────────

function Bomb({ shouldThrow }) {
  if (shouldThrow) throw new Error('test explosion')
  return <div>safe</div>
}

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <Bomb shouldThrow={false} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('safe')).toBeInTheDocument()
  })

  it('renders fallback UI when a child throws', () => {
    // Suppress the expected console.error from React's error boundary
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Bomb shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    spy.mockRestore()
  })

  it('resets state and re-renders children when "Try again" is clicked', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    let shouldThrow = true
    const { rerender } = render(
      <ErrorBoundary>
        <Bomb shouldThrow={shouldThrow} />
      </ErrorBoundary>,
    )

    expect(screen.getByText('Something went wrong')).toBeInTheDocument()

    // Click "Try again" — resets boundary state
    shouldThrow = false
    screen.getByText('Try again').click()

    rerender(
      <ErrorBoundary>
        <Bomb shouldThrow={shouldThrow} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('safe')).toBeInTheDocument()
    spy.mockRestore()
  })
})

// ── ProtectedRoute redirect ──────────────────────────────────────────────────

// Minimal stub: protected route redirects unauthenticated users to /login
import { AuthProvider } from '../context/AuthContext'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div>loading</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

describe('ProtectedRoute', () => {
  it('redirects to /login when unauthenticated', async () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <Routes>
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <div>dashboard</div>
                </ProtectedRoute>
              }
            />
            <Route path="/login" element={<div>login page</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )
    expect(await screen.findByText('login page')).toBeInTheDocument()
  })
})
