import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { neginApi, type AutomationNotification, type NotificationSeverity } from '../api/neginApi'
import { useVisitorAuth } from './VisitorAuthContext'

export type VisitorNotificationItem = AutomationNotification

type VisitorNotificationsValue = {
  items: VisitorNotificationItem[]
  unreadCount: number
  attentionCount: number
  highestSeverity: NotificationSeverity | null
  loading: boolean
  error: string | null
  reload: () => Promise<void>
  markRead: (id: number) => void
  markAcknowledged: (id: number) => void
  markAllRead: () => void
  resetNotifications: () => void
}

const VisitorNotificationsContext = createContext<VisitorNotificationsValue | null>(null)

export function VisitorNotificationsProvider({ children }: { children: ReactNode }) {
  const { authenticated, restoringSession } = useVisitorAuth()
  const [items, setItems] = useState<VisitorNotificationItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!authenticated) {
      setItems([])
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await neginApi.automationNotifications()
      setItems(response.notifications ?? [])
    } catch (caught) {
      setItems([])
      setError(caught instanceof Error ? caught.message : 'Unable to load notifications')
    } finally {
      setLoading(false)
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
    items, unreadCount, attentionCount, highestSeverity, loading, error, reload, markRead, markAcknowledged, markAllRead, resetNotifications,
  }), [items, unreadCount, attentionCount, highestSeverity, loading, error, reload, markRead, markAcknowledged, markAllRead, resetNotifications])

  return <VisitorNotificationsContext.Provider value={value}>{children}</VisitorNotificationsContext.Provider>
}

export function useVisitorNotifications() {
  const value = useContext(VisitorNotificationsContext)
  if (!value) throw new Error('useVisitorNotifications must be used inside VisitorNotificationsProvider')
  return value
}
