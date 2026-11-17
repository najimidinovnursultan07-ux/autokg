import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { addFavorite, listFavorites, removeFavorite } from '../api/favorites.js'
import { useAuth } from './AuthContext.jsx'
import { useToast } from './ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'

const FavoritesContext = createContext(null)

export function FavoritesProvider({ children }) {
  const { user } = useAuth()
  const userId = user?.id ?? user?.email ?? null
  const { notify } = useToast()
  const [favorites, setFavorites] = useState([])
  const [loading, setLoading] = useState(false)
  const [loadedUserId, setLoadedUserId] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [pendingFavoriteIds, setPendingFavoriteIds] = useState(() => new Set())
  const loadRequestId = useRef(0)
  const pendingIdsRef = useRef(new Set())
  const currentUserIdRef = useRef(userId)

  const loadFavorites = useCallback(async () => {
    const requestId = ++loadRequestId.current
    if (!userId) {
      setFavorites([])
      setLoadedUserId(null)
      setLoadError('')
      setLoading(false)
      return
    }
    setLoading(true)
    setLoadError('')
    try {
      const result = await listFavorites()
      if (requestId !== loadRequestId.current) return
      setFavorites(result)
      setLoadedUserId(userId)
    } catch (error) {
      if (requestId !== loadRequestId.current) return
      const message = getErrorMessage(error, 'Не удалось загрузить избранное.')
      setFavorites([])
      setLoadedUserId(userId)
      setLoadError(message)
      notify(message, 'error')
    } finally {
      if (requestId === loadRequestId.current) setLoading(false)
    }
  }, [userId, notify])

  useEffect(() => {
    currentUserIdRef.current = userId
    loadFavorites()
    return () => {
      loadRequestId.current += 1
    }
  }, [loadFavorites, userId])

  const toggleFavorite = useCallback(
    async (car) => {
      if (!userId) throw new Error('Войдите, чтобы сохранять объявления.')
      if (loadedUserId !== userId) throw new Error('Избранное ещё загружается.')

      const carId = String(car.id)
      if (pendingIdsRef.current.has(carId)) return

      const current = favorites.find((item) => String(item.car) === carId)
      pendingIdsRef.current.add(carId)
      setPendingFavoriteIds((items) => new Set(items).add(carId))
      try {
        if (current) {
          await removeFavorite(current.id)
          if (currentUserIdRef.current === userId) {
            setFavorites((items) => items.filter((item) => item.id !== current.id))
            notify('Удалено из избранного.', 'success')
          }
        } else {
          const created = await addFavorite(car.id)
          if (currentUserIdRef.current === userId) {
            setFavorites((items) => (
              items.some((item) => String(item.car) === carId)
                ? items
                : [created, ...items]
            ))
            setLoadedUserId(userId)
            notify('Добавлено в избранное.', 'success')
          }
        }
      } finally {
        pendingIdsRef.current.delete(carId)
        setPendingFavoriteIds((items) => {
          const next = new Set(items)
          next.delete(carId)
          return next
        })
      }
    },
    [favorites, loadedUserId, notify, userId],
  )

  const visibleFavorites = useMemo(
    () => loadedUserId === userId ? favorites : [],
    [favorites, loadedUserId, userId],
  )
  const isLoading = Boolean(userId) && (loading || loadedUserId !== userId)

  const value = useMemo(
    () => ({
      favorites: visibleFavorites,
      loading: isLoading,
      loadError: loadedUserId === userId ? loadError : '',
      pendingFavoriteIds,
      favoriteIds: new Set(visibleFavorites.map((item) => String(item.car))),
      toggleFavorite,
      reloadFavorites: loadFavorites,
    }),
    [
      visibleFavorites,
      isLoading,
      loadedUserId,
      userId,
      loadError,
      pendingFavoriteIds,
      toggleFavorite,
      loadFavorites,
    ],
  )

  return <FavoritesContext.Provider value={value}>{children}</FavoritesContext.Provider>
}

export function useFavorites() {
  const context = useContext(FavoritesContext)
  if (!context) throw new Error('useFavorites must be used within FavoritesProvider')
  return context
}
