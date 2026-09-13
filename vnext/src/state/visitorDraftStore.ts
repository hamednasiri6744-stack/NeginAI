const DRAFT_STORAGE_KEY = 'neginai.prototype.order-drafts.v1'

export type PrototypeOrderDraft = {
  id: string
  customerId: string
  customer: string
  area: string
  cart: Record<number, number>
  payment: 'credit' | 'cash' | 'cheque'
  orderType: 'sale' | 'request'
  amount: number
  updatedAt: number
  visitId?: string | undefined
}

function writeDrafts(drafts: PrototypeOrderDraft[]) {
  try {
    sessionStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(drafts))
  } catch {
    // The UI remains usable when session storage is unavailable.
  }
}

export function readPrototypeDrafts(): PrototypeOrderDraft[] {
  try {
    const raw = sessionStorage.getItem(DRAFT_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as PrototypeOrderDraft[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function findPrototypeDraft(id?: string) {
  if (!id) return undefined
  return readPrototypeDrafts().find((draft) => draft.id === id)
}

export function savePrototypeDraft(draft: PrototypeOrderDraft) {
  const current = readPrototypeDrafts()
  const next = [draft, ...current.filter((item) => item.id !== draft.id)]
  writeDrafts(next)
  return draft
}

export function removePrototypeDraft(id: string) {
  const next = readPrototypeDrafts().filter((draft) => draft.id !== id)
  writeDrafts(next)
  return next
}

export function clearPrototypeDrafts() {
  try {
    sessionStorage.removeItem(DRAFT_STORAGE_KEY)
  } catch {
    // No-op in restrictive browser modes.
  }
}

export function createPrototypeDraftId() {
  const suffix = Math.floor(Date.now() / 1000).toString().slice(-5)
  return `D-${suffix}`
}
