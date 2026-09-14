import { useEffect } from 'react'

const DIALOG_SELECTOR = '.vp-modal-backdrop [role=dialog][aria-modal=true]'
const FOCUSABLE_SELECTOR = 'input:not([disabled]), button:not([disabled]), [href], [tabindex]:not([tabindex=-1])'

export function ProfileModalA11yBridge() {
  useEffect(() => {
    let activeDialog: HTMLElement | null = null
    let previousFocus: HTMLElement | null = null

    const focusables = (dialog: HTMLElement) =>
      Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
        .filter((element) => element.getClientRects().length > 0)

    const syncDialog = () => {
      const nextDialog = document.querySelector<HTMLElement>(DIALOG_SELECTOR)
      if (nextDialog === activeDialog) return

      if (!nextDialog && activeDialog) {
        activeDialog = null
        const restoreTarget = previousFocus
        previousFocus = null
        window.requestAnimationFrame(() => restoreTarget?.focus())
        return
      }

      if (nextDialog) {
        previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
        activeDialog = nextDialog
        nextDialog.tabIndex = -1
        window.requestAnimationFrame(() => nextDialog.focus())
      }
    }

    const observer = new MutationObserver(syncDialog)
    observer.observe(document.body, { childList: true, subtree: true })
    syncDialog()

    const handleKeyDown = (event: KeyboardEvent) => {
      const dialog = activeDialog
      if (!dialog) return

      if (event.key === 'Escape') {
        event.preventDefault()
        const backdrop = dialog.closest<HTMLElement>('.vp-modal-backdrop')
        backdrop?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
        return
      }

      if (event.key !== 'Tab') return
      const controls = focusables(dialog)
      if (!controls.length) {
        event.preventDefault()
        return
      }

      const first = controls[0]!
      const last = controls[controls.length - 1]!
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown, true)
    return () => {
      document.removeEventListener('keydown', handleKeyDown, true)
      observer.disconnect()
    }
  }, [])

  return null
}

