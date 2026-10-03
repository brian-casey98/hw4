import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { currentAccount, loginAccount, logoutAccount, registerAccount, type NewAccount } from './api.ts'
import type { Account } from './types.ts'

type AuthContextValue = {
  user: Account | null
  ready: boolean
  login: (email: string, password: string) => Promise<void>
  register: (account: NewAccount) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Account | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    currentAccount()
      .then((account) => {
        if (!cancelled) setUser(account)
      })
      .catch(() => {
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setReady(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function login(email: string, password: string) {
    setUser(await loginAccount(email, password))
  }

  async function register(account: NewAccount) {
    setUser(await registerAccount(account))
  }

  async function logout() {
    await logoutAccount()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return value
}
