import { useEffect, useState } from 'react'

export function NetworkStatus() {
  const [online, setOnline] = useState(() => navigator.onLine)

  useEffect(() => {
    const sync = () => setOnline(navigator.onLine)
    window.addEventListener('online', sync)
    window.addEventListener('offline', sync)
    return () => {
      window.removeEventListener('online', sync)
      window.removeEventListener('offline', sync)
    }
  }, [])

  if (online) return null
  return (
    <div className="ng-network-banner" role="status" data-trace-id="ST-G-OFFLINE">
      اتصال شبکه قطع است؛ داده‌های عملیاتی جدید تا بازگشت اتصال دریافت نمی‌شوند.
    </div>
  )
}
