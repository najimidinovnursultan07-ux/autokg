import { useCallback, useEffect, useState } from 'react'
import { ArrowRight, CarFront, Eye, EyeOff, Heart, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getMyCars } from '../api/cars.js'
import { useAuth } from '../context/AuthContext.jsx'
import { useFavorites } from '../context/FavoritesContext.jsx'
import { EmptyState, ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { formatPrice, getCarTitle } from '../utils/format.js'

const listingStatuses = {
  draft: 'Черновик',
  pending: 'На модерации',
  published: 'Опубликовано',
  rejected: 'Отклонено',
  inactive: 'Снято с публикации',
  sold: 'Продано',
}

function getCount(response) {
  return response.count ?? response.length ?? 0
}

export default function DashboardPage() {
  const { user } = useAuth()
  const { favorites, loading: favoritesLoading, loadError: favoritesError } = useFavorites()
  const [summary, setSummary] = useState({ all: 0, active: 0, inactive: 0, recent: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [all, active, inactive] = await Promise.all([
        getMyCars({ ordering: '-created_at', page_size: 3 }),
        getMyCars({ status: 'published', page_size: 1 }),
        getMyCars({ status: 'inactive', page_size: 1 }),
      ])
      setSummary({
        all: getCount(all),
        active: getCount(active),
        inactive: getCount(inactive),
        recent: all.results || [],
      })
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось загрузить данные кабинета.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <section className="account-page">
      <PageTitle
        eyebrow="Личный кабинет"
        title={`Здравствуйте, ${user?.first_name || 'добро пожаловать'}!`}
        description="Здесь собраны ваши объявления, избранное и настройки профиля."
        action={<Link className="button button--primary" to="/cars/new"><Plus size={17} /> Продать автомобиль</Link>}
      />
      {error ? <ErrorState message={error} onRetry={load} /> : loading ? (
        <LoadingState compact label="Загружаем ваш кабинет…" />
      ) : (
        <>
          <div className="account-stats">
            <Link className="account-stat" to="/my-cars">
              <span className="account-stat-icon"><CarFront size={20} /></span>
              <span className="account-stat-copy"><strong>{summary.all}</strong><span>Все объявления</span></span>
              <ArrowRight size={17} />
            </Link>
            <Link className="account-stat" to="/my-cars?status=published">
              <span className="account-stat-icon account-stat-icon--blue"><Eye size={20} /></span>
              <span className="account-stat-copy"><strong>{summary.active}</strong><span>Активные</span></span>
              <ArrowRight size={17} />
            </Link>
            <Link className="account-stat" to="/my-cars?status=inactive">
              <span className="account-stat-icon account-stat-icon--muted"><EyeOff size={20} /></span>
              <span className="account-stat-copy"><strong>{summary.inactive}</strong><span>Неактивные</span></span>
              <ArrowRight size={17} />
            </Link>
            <Link className="account-stat" to="/favorites">
              <span className="account-stat-icon account-stat-icon--rose"><Heart size={20} /></span>
              <span className="account-stat-copy">
                <strong>{favoritesLoading ? '…' : favoritesError ? '—' : favorites.length}</strong><span>Избранное</span>
              </span>
              <ArrowRight size={17} />
            </Link>
          </div>

          <div className="account-section-heading">
            <div><h2>Последние объявления</h2><p>Недавно добавленные автомобили</p></div>
            <Link className="text-link" to="/my-cars">Все объявления <ArrowRight size={16} /></Link>
          </div>
          {summary.recent.length ? (
            <div className="dashboard-recent-list">
              {summary.recent.map((car) => (
                <Link className="dashboard-recent-row" to={`/cars/${car.id}/edit`} key={car.id}>
                  <span className={`status-dot status-dot--${car.status}`} />
                  <span className="dashboard-recent-copy">
                    <strong>{getCarTitle(car)}</strong>
                    <span>{listingStatuses[car.status] || car.status}</span>
                  </span>
                  <strong className="dashboard-recent-price">{formatPrice(car.price)}</strong>
                  <ArrowRight size={16} />
                </Link>
              ))}
            </div>
          ) : !error ? (
            <EmptyState title="Объявлений пока нет" action={<Link className="button button--primary" to="/cars/new"><Plus size={17} /> Добавить автомобиль</Link>}>
              Создайте первое объявление — оно появится в этом обзоре.
            </EmptyState>
          ) : null}
        </>
      )}
    </section>
  )
}
