import { Component, ErrorInfo } from 'react'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary gefangen:', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '2rem', maxWidth: '600px', margin: '4rem auto', textAlign: 'center' }}>
          <h2 style={{ color: 'var(--color-error, #c0392b)' }}>Es ist ein unerwarteter Fehler aufgetreten</h2>
          <p style={{ color: 'var(--color-text-muted)', marginBottom: '1rem' }}>
            {this.state.error?.message || 'Unbekannter Fehler'}
          </p>
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              this.setState({ hasError: false, error: null })
              window.location.href = '/'
            }}
          >
            Zur Startseite
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
