import type { Role } from '../types'
import { currentDemoUserId, demoAccounts } from '../data/seed'

const key = 'alas.demo.session.v1'

// This adapter only selects predefined browser-local demo accounts.
export const demoAuth = {
  current(): string | null {
    try {
      const id = currentDemoUserId(localStorage.getItem(key) ?? '')
      return Object.values(demoAccounts).some(account => account.id === id) ? id : null
    } catch { return null }
  },
  signIn(role: Role): string {
    const id = demoAccounts[role].id
    try { localStorage.setItem(key, id) } catch { /* Use the in-memory session. */ }
    return id
  },
  signOut() {
    try { localStorage.removeItem(key) } catch { /* The in-memory session is cleared by the store. */ }
  },
}
