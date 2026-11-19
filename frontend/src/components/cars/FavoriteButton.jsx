import { Heart } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { useFavorites } from '../../context/FavoritesContext.jsx'
import { useToast } from '../../context/ToastContext.jsx'
import { getErrorMessage } from '../../utils/errors.js'

export default function FavoriteButton({ car, className = '' }) {
  const { isAuthenticated, loading: authLoading } = useAuth()
  const {
    favoriteIds,
    loading: favoritesLoading,
    pendingFavoriteIds,
    toggleFavorite,
  } = useFavorites()
  const { notify } = useToast()
  const navigate = useNavigate()
  const active = favoriteIds.has(String(car.id))
  const pending = authLoading
    || favoritesLoading
    || pendingFavoriteIds.has(String(car.id))

  const handleClick = async (event) => {
    event.preventDefault()
    event.stopPropagation()
    if (!isAuthenticated) {
      notify('Войдите, чтобы сохранять объявления.', 'info')
      navigate('/login', { state: { from: { pathname: `/cars/${car.id}` } } })
      return
    }
    try {
      await toggleFavorite(car)
    } catch (error) {
      notify(getErrorMessage(error, 'Не удалось изменить избранное.'), 'error')
    }
  }

  // Публичной регистрации нет — гостям кнопка избранного не показывается
  if (!isAuthenticated) return null

  return (
    <button
      type="button"
      className={`favorite-button ${active ? 'favorite-button--active' : ''} ${className}`}
      onClick={handleClick}
      disabled={pending}
      aria-busy={pending}
      aria-label={pending
        ? 'Синхронизация избранного'
        : active
          ? 'Убрать из избранного'
          : 'Добавить в избранное'}
      aria-pressed={active}
    >
      <Heart size={19} fill={active ? 'currentColor' : 'none'} />
    </button>
  )
}
