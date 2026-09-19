import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { NeginApiError, neginApi, type AutomationNotification, type NotificationSeverity } from '../api/neginApi'
import { useVisitorAuth } from './VisitorAuthContext'

export type VisitorNotificationItem = AutomationNotification

type VisitorNotificationsValue = {
  items: VisitorNotificationItem[]
  unreadCount: number
  attentionCount: number
  highestSeverity: NotificationSeverity | null
  loading: boolean
  error: string | null
  liveConnected: boolean
  reload: () => Promise<void>
  markRead: (id: number) => void
  markAcknowledged: (id: number) => void
  markAllRead: () => void
  resetNotifications: () => void
}

type VisitorNotificationBadgeValue = {
  unreadCount: number
  attentionCount: number
  highestSeverity: NotificationSeverity | null
}

type VisitorNotificationsControlValue = {
  resetNotifications: () => void
}

const VisitorNotificationsContext = createContext<VisitorNotificationsValue | null>(null)
const VisitorNotificationBadgeContext = createContext<VisitorNotificationBadgeValue | null>(null)
const VisitorNotificationsControlContext = createContext<VisitorNotificationsControlValue | null>(null)

export function VisitorNotificationsProvider({ children }: { children: ReactNode }) {
  const { authenticated, restoringSession } = useVisitorAuth()
  const [items, setItems] = useState<VisitorNotificationItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [liveConnected, setLiveConnected] = useState(false)
  const reloadPromiseRef = useRef<Promise<void> | null>(null)

  const reload = useCallback(async () => {
    if (!authenticated) {
      setItems([])
      setError(null)
      return
    }
    if (reloadPromiseRef.current) return reloadPromiseRef.current

    const task = (async () => {
      setLoading(true)
      setError(null)
      try {
        let response
        try {
          response = await neginApi.automationNotifications()
        } catch (caught) {
          if (!(caught instanceof NeginApiError) || caught.status !== 0) throw caught
          await new Promise((resolve) => window.setTimeout(resolve, 450))
          response = await neginApi.automationNotifications()
        }
        setItems(response.notifications ?? [])
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Unable to load notifications')
      } finally {
        setLoading(false)
      }
    })()

    reloadPromiseRef.current = task
    try {
      await task
    } finally {
      if (reloadPromiseRef.current === task) reloadPromiseRef.current = null
    }
  }, [authenticated])

  useEffect(() => {
    if (restoringSession) return
    if (!authenticated) {
      setItems([])
      setError(null)
      return
    }
    void reload()
  }, [authenticated, reload, restoringSession])

  useEffect(() => {
    if (restoringSession || !authenticated) return
    const refreshVisible = () => {
      if (document.visibilityState === 'visible' && !liveConnected) void reload()
    }
    const timer = window.setInterval(refreshVisible, 90_000)
    window.addEventListener('focus', refreshVisible)
    document.addEventListener('visibilitychange', refreshVisible)
    return () => {
      window.clearInterval(timer)
      window.removeEventListener('focus', refreshVisible)
      document.removeEventListener('visibilitychange', refreshVisible)
    }
  }, [authenticated, liveConnected, reload, restoringSession])

  useEffect(() => {
    if (restoringSession || !authenticated || typeof EventSource === 'undefined') {
      setLiveConnected(false)
      return
    }
    const stream = new EventSource('/seller-workspace/live-events')
    const connected = () => setLiveConnected(true)
    const notificationsChanged = () => {
      setLiveConnected(true)
      if (document.visibilityState === 'visible') void reload()
    }
    stream.addEventListener('connected', connected)
    stream.addEventListener('notifications', notificationsChanged)
    stream.onerror = () => setLiveConnected(false)
    return () => {
      stream.removeEventListener('connected', connected)
      stream.removeEventListener('notifications', notificationsChanged)
      stream.close()
      setLiveConnected(false)
    }
  }, [authenticated, reload, restoringSession])

  const markRead = useCallback((id: number) => {
    const target = items.find((item) => item.id === id)
    if (!target || target.read) return
    setItems((current) => current.map((item) => item.id === id ? { ...item, read: true } : item))
    void neginApi.markAutomationNotificationsRead([id]).catch(() => void reload())
  }, [items, reload])

  const markAcknowledged = useCallback((id: number) => {
    const target = items.find((item) => item.id === id)
    if (!target || !target.requires_ack || target.acknowledged) return
    setItems((current) => current.map((item) => item.id === id ? { ...item, acknowledged: true, read: true } : item))
    void neginApi.acknowledgeAutomationNotifications([id]).catch(() => void reload())
  }, [items, reload])

  const markAllRead = useCallback(() => {
    const ids = items.filter((item) => !item.read).map((item) => item.id)
    if (!ids.length) return
    setItems((current) => current.map((item) => ({ ...item, read: true })))
    void neginApi.markAutomationNotificationsRead(ids).catch(() => void reload())
  }, [items, reload])

  const resetNotifications = useCallback(() => {
    setItems([])
    setError(null)
  }, [])

  const unreadCount = useMemo(() => items.filter((item) => !item.read).length, [items])
  const attentionCount = useMemo(
    () => items.filter((item) => !item.read || (item.requires_ack && !item.acknowledged)).length,
    [items],
  )
  const highestSeverity = useMemo<NotificationSeverity | null>(() => {
    const active = items.filter((item) => !item.read || (item.requires_ack && !item.acknowledged))
    for (const level of ['critical', 'high', 'medium', 'info'] as NotificationSeverity[]) {
      if (active.some((item) => item.severity === level)) return level
    }
    return null
  }, [items])
  const value = useMemo<VisitorNotificationsValue>(() => ({
    items, unreadCount, attentionCount, highestSeverity, loading, error, liveConnected, reload, markRead, markAcknowledged, markAllRead, resetNotifications,
  }), [items, unreadCount, attentionCount, highestSeverity, loading, error, liveConnected, reload, markRead, markAcknowledged, markAllRead, resetNotifications])
  const badgeValue = useMemo<VisitorNotificationBadgeValue>(() => ({
    unreadCount,
    attentionCount,
    highestSeverity,
  }), [attentionCount, highestSeverity, unreadCount])
  const controlValue = useMemo<VisitorNotificationsControlValue>(() => ({
    resetNotifications,
  }), [resetNotifications])

  return (
    <VisitorNotificationsControlContext.Provider value={controlValue}>
      <VisitorNotificationBadgeContext.Provider value={badgeValue}>
        <VisitorNotificationsContext.Provider value={value}>{children}</VisitorNotificationsContext.Provider>
      </VisitorNotificationBadgeContext.Provider>
    </VisitorNotificationsControlContext.Provider>
  )
}

export function useVisitorNotifications() {
  const value = useContext(VisitorNotificationsContext)
  if (!value) throw new Error('useVisitorNotifications must be used inside VisitorNotificationsProvider')
  return value
}

export function useVisitorNotificationBadge() {
  const value = useContext(VisitorNotificationBadgeContext)
  if (!value) throw new Error('useVisitorNotificationBadge must be used inside VisitorNotificationsProvider')
  return value
}

export function useVisitorNotificationsControl() {
  const value = useContext(VisitorNotificationsControlContext)
  if (!value) throw new Error('useVisitorNotificationsControl must be used inside VisitorNotificationsProvider')
  return value
}
