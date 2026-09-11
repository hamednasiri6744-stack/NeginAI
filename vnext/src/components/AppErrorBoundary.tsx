import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { error: Error | null }

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('NeginAI render boundary caught an error', error, info)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <main className="ng-auth-shell" dir="rtl" data-trace-id="ST-G-ERROR-BOUNDARY">
        <section className="ng-login-card ng-login-card--status" role="alert">
          <strong>خطای غیرمنتظره در رابط کاربری</strong>
          <span>این خطا در لایه نمایش مهار شد و هیچ منطق کسب‌وکار یا داده‌ای تغییر نکرد.</span>
          <button className="ng-primary-button" type="button" onClick={() => window.location.reload()}>
            بارگذاری دوباره
          </button>
        </section>
      </main>
    )
  }
}
