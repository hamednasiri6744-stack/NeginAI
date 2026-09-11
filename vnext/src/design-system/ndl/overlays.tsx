import { X } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'
import { Button, IconButton } from './components'
import './ndl.css'

type OverlayProps = {
  open: boolean
  title: string
  description?: string
  children: ReactNode
  onClose: () => void
  primaryAction?: { label: string; onClick: () => void }
}

function useNativeDialog(open: boolean) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])
  return ref
}

function OverlayBody({ title, description, children, onClose, primaryAction }: Omit<OverlayProps, 'open'>) {
  return (
    <>
      <header className="ndl-overlay__header"><div><h2>{title}</h2>{description && <p>{description}</p>}</div><IconButton label="بستن" onClick={onClose}><X size={20} /></IconButton></header>
      <div className="ndl-overlay__body">{children}</div>
      <footer className="ndl-overlay__footer"><Button variant="secondary" onClick={onClose}>انصراف</Button>{primaryAction && <Button onClick={primaryAction.onClick}>{primaryAction.label}</Button>}</footer>
    </>
  )
}

export function Dialog({ open, onClose, ...props }: OverlayProps) {
  const ref = useNativeDialog(open)
  return <dialog ref={ref} className="ndl-dialog" onCancel={(event) => { event.preventDefault(); onClose() }} onClick={(event) => { if (event.target === event.currentTarget) onClose() }}><div className="ndl-dialog__panel"><OverlayBody {...props} onClose={onClose} /></div></dialog>
}

export function BottomSheet({ open, onClose, ...props }: OverlayProps) {
  const ref = useNativeDialog(open)
  return <dialog ref={ref} className="ndl-bottom-sheet" onCancel={(event) => { event.preventDefault(); onClose() }} onClick={(event) => { if (event.target === event.currentTarget) onClose() }}><div className="ndl-bottom-sheet__panel"><span className="ndl-bottom-sheet__handle" aria-hidden="true" /><OverlayBody {...props} onClose={onClose} /></div></dialog>
}

export function Toast({ open, message, tone = 'neutral', action, onDismiss }: { open: boolean; message: string; tone?: 'neutral' | 'success' | 'warning' | 'danger'; action?: { label: string; onClick: () => void }; onDismiss?: () => void }) {
  if (!open) return null
  return <div className={`ndl-toast ndl-toast--${tone}`} role={tone === 'danger' ? 'alert' : 'status'} aria-live={tone === 'danger' ? 'assertive' : 'polite'}><span>{message}</span>{action && <button type="button" onClick={action.onClick}>{action.label}</button>}{onDismiss && <IconButton label="بستن پیام" onClick={onDismiss}><X size={18} /></IconButton>}</div>
}
