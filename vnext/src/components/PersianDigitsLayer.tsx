import { useEffect } from 'react'

const latinDigits = /[0-9]/g
const digitMap: Record<string, string> = {
  '0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴',
  '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹',
}

export function toPersianDigits(value: string | number) {
  return String(value).replace(latinDigits, (digit) => digitMap[digit] ?? digit)
}

function shouldSkip(node: Text) {
  const parent = node.parentElement
  if (!parent) return true
  if (parent.closest('script,style,input,textarea,[contenteditable="true"]')) return true
  return false
}

function normalizeTextNode(node: Text) {
  if (shouldSkip(node)) return
  const current = node.nodeValue ?? ''
  const normalized = toPersianDigits(current)
  if (normalized !== current) node.nodeValue = normalized
}

function normalizeTree(root: Node) {
  if (root.nodeType === Node.TEXT_NODE) {
    normalizeTextNode(root as Text)
    return
  }

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let current = walker.nextNode()
  while (current) {
    normalizeTextNode(current as Text)
    current = walker.nextNode()
  }
}

export function PersianDigitsLayer() {
  useEffect(() => {
    const root = document.getElementById('root')
    if (!root) return

    normalizeTree(root)

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'characterData') {
          normalizeTextNode(mutation.target as Text)
          continue
        }
        mutation.addedNodes.forEach((node) => normalizeTree(node))
      }
    })

    observer.observe(root, { subtree: true, childList: true, characterData: true })
    return () => observer.disconnect()
  }, [])

  return null
}
