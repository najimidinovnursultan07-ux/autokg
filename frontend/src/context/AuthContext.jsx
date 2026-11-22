import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { api, ensureCsrfCookie, setAccessToken } from '../api/client.js'
import * as authApi from '../api/auth.js'
import { useToast } from './ToastContext.jsx'

const AuthContext = createContext(null)
let sessionBootstrapPromise = null

function restoreSession() {
  if (!sessionBootstrapPromise) {
    sessionBootstrapPromise = (async () => {
      await ensureCsrfCookie()
      const { data } = await api.post('/auth/refresh/')
      setAccessToken(data.access)
      const user = await authApi.getCurrentUser()
      return { user, access: data.access }
    })().finally(() => {
      sessionBootstrapPromise = null
    })
  }
  return sessionBootstrapPromise
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const { notify } = useToast()

  const acceptSession = useCallback((data) => {
    setAccessToken(data.access)
    setUser(data.user)
  }, [])

  useEffect(() => {
    let active = true
    const bootstrap = async () => {
      try {
        const session = await restoreSession()
        if (active) setUser(session.user)
      } catch (error) {
        if (active) setAccessToken(null)
        if (active && error.response?.status !== 401) {
          notify(
            'Не удалось восстановить сессию. Проверьте соединение с сервером.',
            'error',
          )
        }
      } finally {
        if (active) setLoading(false)
      }
    }
    bootstrap()
    return () => {
      active = false
    }
  }, [notify])

  useEffect(() => {
    const expireSession = () => {
      setAccessToken(null)
      setUser(null)
    }
    window.addEventListener('autobuy:session-expired', expireSession)
    return () => window.removeEventListener('autobuy:session-expired', expireSession)
  }, [])

  const finishSignIn = useCallback(
    async (data) => {
      setAccessToken(data.access)
      try {
        const currentUser = await authApi.getCurrentUser()
        acceptSession({ access: data.access, user: currentUser })
        return currentUser
      } catch (error) {
        setAccessToken(null)
        throw error
      }
    },
    [acceptSession],
  )

  // Админу сервер вместо токенов отвечает two_factor_required — нужен код из Telegram
  const verifyLoginCode = useCallback(
    async (challengeId, code) => finishSignIn(await authApi.verifyLoginCode(challengeId, code)),
    [finishSignIn],
  )

  const signIn = useCallback(
    async (credentials) => {
      const data = await authApi.login(credentials)
      if (data.two_factor_required) {
        return { twoFactor: { challengeId: data.challenge_id, expiresIn: data.expires_in } }
      }
      return finishSignIn(data)
    },
    [finishSignIn],
  )

  const signOut = useCallback(async () => {
    try {
      if (user) await authApi.logout()
    } catch {
      notify(
        'Не удалось подтвердить выход на сервере. Локальная сессия завершена.',
        'error',
      )
    } finally {
      setAccessToken(null)
      setUser(null)
    }
  }, [notify, user])

  const refreshUser = useCallback(async () => {
    const currentUser = await authApi.getCurrentUser()
    setUser(currentUser)
    return currentUser
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      signIn,
      verifyLoginCode,
      signOut,
      refreshUser,
      setUser,
    }),
    [user, loading, signIn, verifyLoginCode, signOut, refreshUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
