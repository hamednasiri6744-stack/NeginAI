import { useMemo, useState, type FormEvent } from 'react'
import { neginApi } from '../api/neginApi'
import { useVisitorLiveData } from '../state/VisitorLiveDataContext'
import { useVisitorWorkflow } from '../state/VisitorWorkflowContext'
import {
  AiSparkIcon,
  CameraIcon,
  CartIcon,
  ChevronLeftIcon,
  HomeIcon,
  MapIcon,
  MicIcon,
  PaperclipIcon,
  SendIcon,
  StoreIcon,
} from './Icons'

type Props = {
  context?: string | undefined
  customerId?: string | undefined
  visitId?: string | undefined
  draftId?: string | undefined
  prompt?: string | undefined
  onBack: () => void
  onNavigate: (path: string) => void
}

type LocalMessage = { id: string; role: 'user' | 'assistant' | 'system'; text: string }

const contextLabels: Record<string, string> = {
  home: 'خانه و برنامه امروز',
  route: 'مسیر و بازدیدها',
  customer: 'پروفایل مشتری',
  order: 'سفارش و سبد',
  report: 'گزارش‌ها',
}

const promptPresets: Record<string, string> = {
  'sales-opportunity': 'بهترین فرصت فروش امروز را با تکیه بر داده‌های مجاز من بررسی کن',
  stock: 'هشدارهای موجودی مرتبط با برنامه امروز من را بررسی کن',
  performance: 'عملکرد امروز من را تحلیل کن',
}

export function VisitorAiScreen({ context = 'home', customerId, visitId, draftId, prompt, onBack, onNavigate }: Props) {
  const [text, setText] = useState(() => prompt ? (promptPresets[prompt] ?? prompt) : '')
  const [messages, setMessages] = useState<LocalMessage[]>([])
  const [conversationId, setConversationId] = useState<string | undefined>(undefined)
  const [sending, setSending] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const { routeSummary, activeVisit } = useVisitorWorkflow()
  const { activeRouteId, activeRouteTitle, customerById } = useVisitorLiveData()
  const effectiveCustomerId = customerId ?? activeVisit?.customerId
  const customer = effectiveCustomerId ? customerById(effectiveCustomerId) : undefined

  const contextSummary = useMemo(() => {
    if (context === 'customer' && customer) return `${customer.store_name || customer.name} · ${customer.code || 'بدون کد'}`
    if (context === 'route') return `${activeRouteTitle || 'مسیر روز'} · ${routeSummary.remaining} ایستگاه باقی‌مانده`
    if (context === 'order') {
      const state = [visitId ? 'بازدید فعال' : '', draftId ? 'پیش‌نویس فعال' : ''].filter(Boolean).join(' · ')
      return customer ? `سفارش ${customer.store_name || customer.name}${state ? ` · ${state}` : ''}` : `سفارش فعال${state ? ` · ${state}` : ''}`
    }
    if (context === 'report') return 'تحلیل عملکرد و فروش ویزیتور'
    return `${routeSummary.visited} بازدید تعیین‌تکلیف‌شده از ${routeSummary.total}`
  }, [activeRouteTitle, context, customer, draftId, routeSummary, visitId])

  const quickPrompts = context === 'customer' && customer
    ? ['برای این مشتری چه پیشنهادی داری؟', 'ریسک مالی مشتری را خلاصه کن', 'فرصت‌های فروش این مشتری چیست؟']
    : context === 'route'
      ? ['اولویت بازدیدهای باقی‌مانده', 'کدام مشتری پتانسیل فروش بیشتری دارد؟', 'مسیر امروز را خلاصه کن']
      : context === 'order'
        ? ['سبد را از نظر ریسک بررسی کن', 'فرصت افزایش فروش چیست؟', 'خلاصه سفارش را آماده کن']
        : context === 'report'
          ? ['عملکرد امروز را خلاصه کن', 'مهم‌ترین فرصت رشد چیست؟', 'هشدارهای عملکرد را بگو']
          : ['کارهای مهم امروز را بگو', 'بهترین فرصت فروش امروز', 'هشدارهای مهم مسیر']

  function flash(message: string) {
    setNotice(message)
    window.setTimeout(() => setNotice(null), 2400)
  }

  function uiContextAttachment() {
    const lines = [
      `screen=${context}`,
      activeRouteId ? `route_id=${activeRouteId}` : '',
      activeRouteTitle ? `route_title=${activeRouteTitle}` : '',
      effectiveCustomerId ? `customer_id=${effectiveCustomerId}` : '',
      customer ? `customer_name=${customer.store_name || customer.name}` : '',
      visitId ? `visit_id=${visitId}` : '',
      draftId ? `draft_id=${draftId}` : '',
    ].filter(Boolean)
    return lines.length ? lines.join('\n') : undefined
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    const value = text.trim()
    if (!value || sending) return

    const userMessage: LocalMessage = { id: `u-${Date.now()}`, role: 'user', text: value }
    setMessages((current) => [...current, userMessage])
    setText('')
    setSending(true)

    try {
      const attachmentContext = uiContextAttachment()
      const options: { dayRouteId?: string; attachmentContext?: string; attachmentName?: string } = {}
      if (context === 'route' && activeRouteId) options.dayRouteId = activeRouteId
      if (attachmentContext) {
        options.attachmentContext = attachmentContext
        options.attachmentName = 'visitor-ui-context.txt'
      }
      const response = await neginApi.chat(value, conversationId, options)
      setConversationId(response.conversation_id)
      setMessages((current) => [...current, {
        id: `a-${Date.now()}`,
        role: 'assistant',
        text: response.answer || 'پاسخی از سرویس دریافت نشد.',
      }])
    } catch (caught) {
      setMessages((current) => [...current, {
        id: `s-${Date.now()}`,
        role: 'system',
        text: caught instanceof Error ? caught.message : 'ارتباط با سرویس Negin AI ناموفق بود.',
      }])
    } finally {
      setSending(false)
    }
  }

  return (
    <main className="vai-page" dir="rtl">
      <div className="vai-shell">
        <header className="vai-header">
          <button type="button" className="vai-back" onClick={onBack} aria-label="بازگشت"><ChevronLeftIcon /></button>
          <div className="vai-title"><span><AiSparkIcon /></span><div><strong>Negin AI</strong><small>دستیار ویزیتور</small></div></div>
          <span className="vai-status"><i /> {sending ? 'در حال پاسخ…' : 'متصل'}</span>
        </header>

        <section className="vai-context">
          <div><small>زمینه فعال</small><strong>{contextLabels[context] ?? 'ویزیتور'}</strong><span>{contextSummary}</span></div>
          <span className="vai-context-icon">{context === 'customer' ? <StoreIcon /> : context === 'route' ? <MapIcon /> : context === 'order' ? <CartIcon /> : <AiSparkIcon />}</span>
        </section>

        <section className="vai-integrity" role="status">
          <strong>سرویس واقعی NeginAI</strong>
          <span>پیام‌ها از مسیر احراز هویت‌شده Backend ارسال می‌شوند و پاسخ ساختگی در Frontend تولید نمی‌شود.</span>
        </section>

        <section className="vai-quick" aria-label="پیشنهادهای سریع">
          {quickPrompts.map((item) => <button key={item} type="button" onClick={() => setText(item)}>{item}</button>)}
        </section>

        <section className="vai-thread" aria-live="polite">
          {messages.length === 0 ? (
            <div className="vai-empty"><AiSparkIcon /><strong>چه کمکی لازم داری؟</strong><span>پیام بنویس یا یکی از پیشنهادهای بالا را انتخاب کن.</span></div>
          ) : messages.map((message) => (
            <article key={message.id} className={`vai-message ${message.role}`}>
              <small>{message.role === 'user' ? 'شما' : message.role === 'assistant' ? 'Negin AI' : 'وضعیت سرویس'}</small>
              <p>{message.text}</p>
            </article>
          ))}
          {sending ? <article className="vai-message assistant pending"><small>Negin AI</small><p>در حال پردازش…</p></article> : null}
        </section>

        <form className="vai-composer" onSubmit={submit}>
          <div className="vai-tools">
            <button type="button" onClick={() => flash('پیوست در این Slice هنوز به Attachment API متصل نشده است')} aria-label="پیوست"><PaperclipIcon /></button>
            <button type="button" onClick={() => flash('دوربین در این Slice هنوز به Attachment API متصل نشده است')} aria-label="دوربین"><CameraIcon /></button>
            <button type="button" onClick={() => flash('ورودی صوتی در این Slice هنوز به Audio API متصل نشده است')} aria-label="صدا"><MicIcon /></button>
          </div>
          <label><textarea value={text} onChange={(event) => setText(event.target.value)} rows={1} placeholder="پیام به Negin AI..." disabled={sending} /></label>
          <button type="submit" className="vai-send" disabled={!text.trim() || sending} aria-label="ارسال"><SendIcon /></button>
        </form>

        <div className="vai-links" aria-label="میانبرهای دستیار">
          {effectiveCustomerId ? <button className="vai-link-button" type="button" onClick={() => onNavigate(`/visitor/customers/${effectiveCustomerId}`)}><StoreIcon /><span>مشتری</span></button> : null}
          <button className="vai-link-button home" type="button" onClick={() => onNavigate('/visitor/home')}><HomeIcon /><span>خانه</span></button>
        </div>
        {notice ? <div className="vh-toast" role="status">{notice}</div> : null}
      </div>
    </main>
  )
}
