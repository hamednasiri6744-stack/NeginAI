import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useMemo, useState, type FormEvent } from 'react'
import { useLocation } from 'react-router'
import { neginApi } from '../api/neginApi'
import { useVisitorAuth } from '../state/VisitorAuthContext'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'
import { AiSparkIcon, CloseIcon, SendIcon } from './Icons'
import './FloatingNeginAi.css'

type LocalMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  text: string
}

type AssistantContext = {
  key: 'home' | 'route' | 'customer' | 'order' | 'report' | 'other'
  label: string
  customerId?: string | undefined
  visitId?: string | undefined
  draftId?: string | undefined
}

function resolveContext(pathname: string, search: string): AssistantContext {
  const params = new URLSearchParams(search)

  if (pathname.startsWith('/visitor/customers/')) {
    return {
      key: 'customer',
      label: 'مشتری',
      customerId: pathname.split('/').filter(Boolean).at(-1),
    }
  }

  if (pathname.startsWith('/visitor/route')) {
    return {
      key: 'route',
      label: 'مسیر و بازدید',
      customerId: params.get('customer') ?? undefined,
      visitId: params.get('visit') ?? undefined,
    }
  }

  if (pathname.startsWith('/visitor/orders')) {
    return {
      key: 'order',
      label: 'سفارش',
      customerId: params.get('customer') ?? undefined,
      visitId: params.get('visit') ?? undefined,
      draftId: params.get('draft') ?? undefined,
    }
  }

  if (pathname.startsWith('/visitor/reports')) {
    return { key: 'report', label: 'گزارش‌ها' }
  }

  if (pathname.startsWith('/visitor/home')) {
    return { key: 'home', label: 'خانه' }
  }

  return { key: 'other', label: 'اپلیکیشن' }
}

const QUICK_PROMPTS: Record<AssistantContext['key'], string[]> = {
  home: ['کارهای مهم امروز را بگو', 'بهترین فرصت فروش امروز', 'هشدارهای مهم امروز'],
  route: ['اولویت بازدیدهای باقی‌مانده', 'مسیر امروز را خلاصه کن', 'کدام مشتری اولویت بالاتری دارد؟'],
  customer: ['این مشتری را تحلیل کن', 'ریسک مالی این مشتری چیست؟', 'فرصت فروش این مشتری چیست؟'],
  order: ['سبد را بررسی کن', 'فرصت افزایش فروش چیست؟', 'ریسک سفارش را بررسی کن'],
  report: ['عملکرد را خلاصه کن', 'مهم‌ترین فرصت رشد چیست؟', 'هشدارهای عملکرد را بگو'],
  other: ['وضعیت فعلی را خلاصه کن', 'چه کاری اولویت دارد؟', 'هشدار مهمی وجود دارد؟'],
}

export function FloatingNeginAi() {
  const location = useLocation()
  const reducedMotion = useReducedMotion()
  const { authenticated, restoringSession } = useVisitorAuth()
  const { activeRouteId, activeRouteTitle, customerById } = useVisitorLiveData()
  const { activeVisit, routeSummary } = useVisitorWorkflow()

  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [conversationId, setConversationId] = useState<string | undefined>(undefined)
  const [sending, setSending] = useState(false)

  const context = useMemo(
    () => resolveContext(location.pathname, location.search),
    [location.pathname, location.search],
  )

  const effectiveCustomerId = context.customerId ?? activeVisit?.customerId
  const customer = effectiveCustomerId ? customerById(effectiveCustomerId) : undefined
  const quickPrompts = QUICK_PROMPTS[context.key]

  const contextSummary = useMemo(() => {
    if (context.key === 'customer' && customer) {
      return customer.store_name || customer.name || 'مشتری فعال'
    }
    if (context.key === 'route') {
      return `${activeRouteTitle || 'مسیر روز'} · ${routeSummary.remaining} ایستگاه مانده`
    }
    if (context.key === 'order' && customer) {
      return `سفارش · ${customer.store_name || customer.name}`
    }
    if (context.key === 'report') return 'تحلیل داده‌های عملیاتی'
    if (context.key === 'home') return 'برنامه و عملکرد امروز'
    return 'زمینه فعلی اپ'
  }, [activeRouteTitle, context.key, customer, routeSummary.remaining])

  function buildContextAttachment() {
    const lines = [
      `screen=${context.key}`,
      `path=${location.pathname}`,
      activeRouteId ? `route_id=${activeRouteId}` : '',
      activeRouteTitle ? `route_title=${activeRouteTitle}` : '',
      effectiveCustomerId ? `customer_id=${effectiveCustomerId}` : '',
      customer ? `customer_name=${customer.store_name || customer.name}` : '',
      context.visitId ? `visit_id=${context.visitId}` : '',
      context.draftId ? `draft_id=${context.draftId}` : '',
    ].filter(Boolean)

    return lines.join('\n')
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    const value = text.trim()
    if (!value || sending) return

    setMessages((current) => [
      ...current,
      { id: `u-${Date.now()}`, role: 'user', text: value },
    ])
    setText('')
    setSending(true)

    try {
      const options: { dayRouteId?: string; attachmentContext?: string; attachmentName?: string } = {
        attachmentContext: buildContextAttachment(),
        attachmentName: 'visitor-floating-ai-context.txt',
      }
      if (context.key === 'route' && activeRouteId) options.dayRouteId = activeRouteId

      const response = await neginApi.chat(value, conversationId, options)
      setConversationId(response.conversation_id)
      setMessages((current) => [
        ...current,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: response.answer || 'پاسخی از سرویس دریافت نشد.',
        },
      ])
    } catch (caught) {
      setMessages((current) => [
        ...current,
        {
          id: `s-${Date.now()}`,
          role: 'system',
          text: caught instanceof Error ? caught.message : 'ارتباط با سرویس Negin AI ناموفق بود.',
        },
      ])
    } finally {
      setSending(false)
    }
  }

  if (!authenticated || restoringSession) return null

  return (
    <div className="fai-root" dir="rtl" data-open={open ? 'true' : 'false'}>
      <AnimatePresence initial={false}>
        {open ? (
          <motion.section
            key="floating-ai-panel"
            className="fai-panel"
            role="dialog"
            aria-modal="false"
            aria-label="گفتگو با Negin AI"
            initial={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.72, y: 34, x: 18 }}
            animate={{ opacity: 1, scale: 1, y: 0, x: 0 }}
            exit={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.78, y: 26, x: 14 }}
            transition={{ type: 'spring', stiffness: 360, damping: 30, mass: 0.72 }}
          >
            <header className="fai-header">
              <span className="fai-avatar"><AiSparkIcon /></span>
              <div>
                <strong>Negin AI</strong>
                <small>{sending ? 'در حال پاسخ…' : 'دستیار شناور · متصل'}</small>
              </div>
              <span className="fai-live"><i /> LIVE</span>
            </header>

            <div className="fai-context">
              <span>{context.label}</span>
              <strong>{contextSummary}</strong>
            </div>

            {messages.length === 0 ? (
              <div className="fai-welcome">
                <AiSparkIcon />
                <strong>چه کمکی لازم داری؟</strong>
                <span>گفتگو در تمام صفحات باز می‌ماند و زمینه صفحه فعلی را می‌شناسد.</span>
              </div>
            ) : (
              <div className="fai-thread" aria-live="polite">
                {messages.map((message) => (
                  <motion.article
                    layout
                    key={message.id}
                    className={`fai-message ${message.role}`}
                    initial={reducedMotion ? false : { opacity: 0, y: 8, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.22 }}
                  >
                    <small>{message.role === 'user' ? 'شما' : message.role === 'assistant' ? 'Negin AI' : 'وضعیت'}</small>
                    <p>{message.text}</p>
                  </motion.article>
                ))}
                {sending ? (
                  <motion.article
                    className="fai-message assistant pending"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    <small>Negin AI</small>
                    <p><i /><i /><i /></p>
                  </motion.article>
                ) : null}
              </div>
            )}

            <div className="fai-quick" aria-label="پیشنهادهای سریع">
              {quickPrompts.map((item) => (
                <button key={item} type="button" onClick={() => setText(item)}>
                  {item}
                </button>
              ))}
            </div>

            <form className="fai-composer" onSubmit={submit}>
              <textarea
                rows={1}
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder="پیام به Negin AI..."
                disabled={sending}
              />
              <button type="submit" disabled={!text.trim() || sending} aria-label="ارسال">
                <SendIcon />
              </button>
            </form>
          </motion.section>
        ) : null}
      </AnimatePresence>

      <motion.button
        type="button"
        className="fai-trigger"
        aria-label={open ? 'بستن Negin AI' : 'باز کردن Negin AI'}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        {...(reducedMotion ? {} : { whileTap: { scale: 0.9 } })}
        animate={open
          ? { scale: 1, rotate: 0 }
          : reducedMotion
            ? { scale: 1 }
            : { scale: [1, 1.04, 1] }}
        transition={open
          ? { type: 'spring', stiffness: 420, damping: 28 }
          : { duration: 3.8, repeat: Infinity, ease: 'easeInOut' }}
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={open ? 'close' : 'ai'}
            initial={reducedMotion ? false : { opacity: 0, rotate: -50, scale: 0.55 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={reducedMotion ? { opacity: 0 } : { opacity: 0, rotate: 50, scale: 0.55 }}
            transition={{ duration: 0.18 }}
          >
            {open ? <CloseIcon /> : <AiSparkIcon />}
          </motion.span>
        </AnimatePresence>
        <i className="fai-orbit" aria-hidden="true" />
      </motion.button>
    </div>
  )
}
