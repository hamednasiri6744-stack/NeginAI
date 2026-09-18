import { lazy, Suspense, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { AiSparkIcon, CloseIcon } from './Icons'
import './FloatingNeginAiLauncher.css'

const FloatingNeginAiPanel = lazy(() =>
  import('./FloatingNeginAiPanel').then((module) => ({ default: module.FloatingNeginAiPanel })),
)

export type FloatingAiMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  text: string
}

export function FloatingNeginAi() {
  const reducedMotion = useReducedMotion()
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [messages, setMessages] = useState<FloatingAiMessage[]>([])
  const [conversationId, setConversationId] = useState<string | undefined>(undefined)
  const [sending, setSending] = useState(false)

  return (
    <div className="fai-root" dir="rtl" data-open={open ? 'true' : 'false'}>
      <Suspense fallback={null}>
        <AnimatePresence initial={false}>
          {open ? (
            <FloatingNeginAiPanel
              key="floating-ai-panel"
              reducedMotion={reducedMotion}
              text={text}
              setText={setText}
              messages={messages}
              setMessages={setMessages}
              conversationId={conversationId}
              setConversationId={setConversationId}
              sending={sending}
              setSending={setSending}
            />
          ) : null}
        </AnimatePresence>
      </Suspense>

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
