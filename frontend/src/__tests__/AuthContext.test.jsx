import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { AuthProvider, useAuth } from '../context/AuthContext'

// Build a minimal valid JWT with the given payload (not cryptographically signed — fine for tests)
function makeToken(payload) {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = btoa(JSON.stringify(payload))
  return `${header}.${body}.sig`
}

function Consumer() {
  const { user, loading } = useAuth()
  if (loading) return <div>loading</div>
  if (!user) return <div>logged-out</div>
  return <div>user:{user.role}</div>
}

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('starts in loading state then resolves to logged-out when no token stored', async () => {
    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    )
    // After effect runs it should not be loading
    expect(await screen.findByText('logged-out')).toBeInTheDocument()
  })

  it('restores user from a valid stored token', async () => {
    const exp = Math.floor(Date.now() / 1000) + 3600
    const token = makeToken({ sub: '42', role: 'SELLER', email: 'a@b.com', full_name: 'A', exp })
    localStorage.setItem('invoiceflow_token', token)

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    )
    expect(await screen.findByText('user:SELLER')).toBeInTheDocument()
  })

  it('ignores an expired stored token and shows logged-out', async () => {
    const exp = Math.floor(Date.now() / 1000) - 10 // already expired
    const token = makeToken({ sub: '1', role: 'INVESTOR', email: 'x@y.com', full_name: 'X', exp })
    localStorage.setItem('invoiceflow_token', token)

    render(
      <AuthProvider>
        <Consumer />
      </AuthProvider>,
    )
    expect(await screen.findByText('logged-out')).toBeInTheDocument()
  })
})

function LoginConsumer() {
  const { user, login, logout } = useAuth()
  return (
    <div>
      <div>{user ? `user:${user.role}` : 'logged-out'}</div>
      <button
        onClick={() => {
          const exp = Math.floor(Date.now() / 1000) + 3600
          login(makeToken({ sub: '1', role: 'INVESTOR', email: 'i@v.com', full_name: 'I', exp }))
        }}
      >
        login
      </button>
      <button onClick={logout}>logout</button>
    </div>
  )
}

describe('AuthContext login/logout', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => localStorage.clear())

  it('login sets user; logout clears it', async () => {
    const { getByText } = render(
      <AuthProvider>
        <LoginConsumer />
      </AuthProvider>,
    )

    expect(await screen.findByText('logged-out')).toBeInTheDocument()

    await act(async () => {
      getByText('login').click()
    })
    expect(screen.getByText('user:INVESTOR')).toBeInTheDocument()
    expect(localStorage.getItem('invoiceflow_token')).not.toBeNull()

    await act(async () => {
      getByText('logout').click()
    })
    expect(screen.getByText('logged-out')).toBeInTheDocument()
    expect(localStorage.getItem('invoiceflow_token')).toBeNull()
  })
})
