const ORDER_WORKSPACE_KEY = 'neginai.prototype.order-workspace.v1'

export type VisitorOrderWorkspace = {
  version: 1
  customerId: string
  visitId?: string | undefined
  draftId?: string | undefined
  cart: Record<number, number>
  payment: 'credit' | 'cash' | 'cheque'
  orderType: 'sale' | 'request'
  view: 'products' | 'catalog' | 'cart'
  updatedAt: number
}

export function readVisitorOrderWorkspace(): VisitorOrderWorkspace | null {
  try {
    const raw = sessionStorage.getItem(ORDER_WORKSPACE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as VisitorOrderWorkspace
    if (parsed?.version !== 1 || !parsed.customerId || !parsed.cart || typeof parsed.cart !== 'object') return null
    return parsed
  } catch {
    return null
  }
}

export function writeVisitorOrderWorkspace(workspace: VisitorOrderWorkspace) {
  try {
    sessionStorage.setItem(ORDER_WORKSPACE_KEY, JSON.stringify(workspace))
  } catch {
    // The UI remains usable if session storage is unavailable.
  }
}

export function clearVisitorOrderWorkspace() {
  try {
    sessionStorage.removeItem(ORDER_WORKSPACE_KEY)
  } catch {
    // No-op in restrictive browser modes.
  }
}
