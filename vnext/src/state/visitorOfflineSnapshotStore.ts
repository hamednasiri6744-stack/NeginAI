import type {
  RouteCustomersResponse,
  SellerRoutesResponse,
  SellerTargetPulse,
} from '../api/neginApi'

const DB_NAME = 'neginai-offline-v1'
const DB_VERSION = 1
const STORE_NAME = 'snapshots'

export type VisitorOfflineSnapshot = {
  version: 1
  username: string
  savedAt: string
  routesData: SellerRoutesResponse
  customersData: RouteCustomersResponse | null
  targetPulse: SellerTargetPulse | null
}

function snapshotKey(username: string) {
  return `visitor-live:${username.trim().toLowerCase()}`
}
function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME)
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error('IndexedDB unavailable'))
  })
}

async function withStore<T>(
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await openDb()
  try {
    return await new Promise<T>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, mode)
      const request = operation(tx.objectStore(STORE_NAME))
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error ?? new Error('IndexedDB request failed'))
      tx.onabort = () => reject(tx.error ?? new Error('IndexedDB transaction aborted'))
    })
  } finally {
    db.close()
  }
}
export async function saveVisitorOfflineSnapshot(snapshot: VisitorOfflineSnapshot) {
  if (typeof indexedDB === 'undefined') return
  await withStore('readwrite', (store) => store.put(snapshot, snapshotKey(snapshot.username)))
}

export async function loadVisitorOfflineSnapshot(username: string): Promise<VisitorOfflineSnapshot | null> {
  if (typeof indexedDB === 'undefined') return null
  const result = await withStore<VisitorOfflineSnapshot | undefined>(
    'readonly',
    (store) => store.get(snapshotKey(username)),
  )
  if (!result || result.version !== 1 || result.username !== username) return null
  return result
}

export async function clearVisitorOfflineSnapshot(username: string) {
  if (typeof indexedDB === 'undefined' || !username.trim()) return
  await withStore('readwrite', (store) => store.delete(snapshotKey(username)))
}
