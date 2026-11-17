import { useCallback, useEffect, useState } from 'react'
import { ArrowRight, CarFront, CheckCircle2, Clock3, Users, UserX } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getAdminStats } from '../api/admin.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { getErrorMessage } from '../utils/errors.js'

export default function AdminDashboardPage() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setStats(await getAdminStats())
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось загрузить статистику.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <section className="admin-page">
      <PageTitle
        eyebrow="Администрирование"
        title="Обзор платформы"
        description="Ключевые показатели AutoKG и быстрый доступ к рабочим разделам."
      />
      {loading ? <LoadingState label="Загружаем статистику…" /> : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <>
          <div className="admin-stat-grid">
            <Link to="/admin/users" className="admin-stat-card">
              <span className="admin-stat-icon"><Users size={20} /></span>
              <span className="admin-stat-copy"><small>Пользователи</small><strong>{stats.users.total}</strong><em>{stats.users.active} активных</em></span>
              <ArrowRight size={17} />
            </Link>
            <Link to="/admin/users?is_active=false" className="admin-stat-card">
              <span className="admin-stat-icon admin-stat-icon--red"><UserX size={20} /></span>
              <span className="admin-stat-copy"><small>Заблокированы</small><strong>{stats.users.blocked}</strong><em>Аккаунты отключены</em></span>
              <ArrowRight size={17} />
            </Link>
            <Link to="/admin/cars" className="admin-stat-card">
              <span className="admin-stat-icon admin-stat-icon--blue"><CarFront size={20} /></span>
              <span className="admin-stat-copy"><small>Объявления</small><strong>{stats.cars.total}</strong><em>{stats.cars.published} опубликовано</em></span>
              <ArrowRight size={17} />
            </Link>
            <Link to="/admin/cars?status=pending" className="admin-stat-card">
              <span className="admin-stat-icon admin-stat-icon--amber"><Clock3 size={20} /></span>
              <span className="admin-stat-copy"><small>Ожидают проверки</small><strong>{stats.cars.pending}</strong><em>Очередь модерации</em></span>
              <ArrowRight size={17} />
            </Link>
          </div>
          <div className="admin-overview-card">
            <div className="admin-overview-heading">
              <span className="admin-stat-icon admin-stat-icon--green"><CheckCircle2 size={20} /></span>
              <div><h2>Рабочие разделы</h2><p>Управление пользователями, контентом и справочниками</p></div>
            </div>
            <div className="admin-overview-links">
              <Link to="/admin/users">Пользователи <ArrowRight size={16} /></Link>
              <Link to="/admin/cars">Все объявления <ArrowRight size={16} /></Link>
              <Link to="/admin/catalog">Марки, модели и города <ArrowRight size={16} /></Link>
            </div>
          </div>
        </>
      )}
    </section>
  )
}
