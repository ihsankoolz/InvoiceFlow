import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary] Uncaught error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-cream flex flex-col items-center justify-center gap-4 p-8">
          <h1 className="font-['Lato'] text-2xl font-bold text-ink">Something went wrong</h1>
          <p className="font-['Lato'] text-ink/70 text-center max-w-md">
            An unexpected error occurred. Please refresh the page or contact support if the problem
            persists.
          </p>
          <button
            className="px-4 py-2 bg-ink text-cream rounded font-['Lato'] text-sm"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
