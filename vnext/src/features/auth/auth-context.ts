import { createContext, useContext } from 'react'

export type AuthProfile = {
  username: string
  role?: string
  full_name?: string
  display_name?: string
  [key: string]: unknown
}

export type AuthValue = {
  profile: AuthProfile | null
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthValue | null>(null)

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthGate')
  return value
}
