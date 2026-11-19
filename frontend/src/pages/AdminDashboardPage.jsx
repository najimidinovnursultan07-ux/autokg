import { useCallback, useEffect, useState } from 'react'
import { ArrowRight, Building2, CarFront, EyeOff, UserCheck } from 'lucide-react'
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
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить статистику.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Обзор платформы" description="Автосалоны, менеджеры и объявления AutoKG." />
      {loading ? <LoadingState label="Загружаем статистику…" /> : error ? <ErrorState message={error} onRetry={load} /> : (
        <>
          <div className="admin-stat-grid">
            <Link to="/admin/dealers" className="admin-stat-card">
              <span className="admin-stat-icon admin-stat-icon--blue"><Building2 size={19} /></span>
              <span className="admin-stat-copy"><small>Автосалоны</small><strong>{stats.dealers.total}</strong><em>активных: {stats.dealers.active}</em></span>
            </Link>
            <Link to="/admin/cars" className="admin-stat-card">
              <span className="admin-stat-icon admin-stat-icon--green"><CarFront size={19} /></span>
              <span className="admin-stat-copy"><small>Объявления</small><strong>{stats.cars.total}</strong><em>активных: {stats.cars.active}</em></span>
            </Link>
            <Link to="/admin/cars?status=hidden" className="admin-stat-card">
              <span className="admin-stat-icon admin-stat-icon--amber"><EyeOff size={19} /></span>
              <span className="admin-stat-copy"><small>Скрыто / продано</small><strong>{stats.cars.hidden} / {stats.cars.sold}</strong><em>не видны на сайте</em></span>
            </Link>
            <Link to="/admin/managers" className="admin-stat-card">
              <span className="admin-stat-icon"><UserCheck size={19} /></span>
              <span className="admin-stat-copy"><small>Менеджеры</small><strong>{stats.managers.total}</strong><em>активных: {stats.managers.active}</em></span>
            </Link>
          </div>

          <h2 className="admin-section-title">Объявления по салонам</h2>
          {stats.cars_by_dealer.length ? (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead><tr><th>Салон</th><th>Всего</th><th>Активных</th><th>Статус салона</th><th /></tr></thead>
                <tbody>
                  {stats.cars_by_dealer.map((d) => (
                    <tr key={d.id}>
                      <td><strong>{d.name}</strong><br /><small>{d.slug}</small></td>
                      <td>{d.total}</td>
                      <td>{d.active}</td>
                      <td><span className={`admin-status ${d.is_active ? 'admin-status--active' : 'admin-status--blocked'}`}>{d.is_active ? 'Активен' : 'Отключён'}</span></td>
                      <td><Link className="text-link" to={`/admin/cars?dealer=${encodeURIComponent(d.slug)}`}>Объявления <ArrowRight size={14} /></Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="admin-empty">Салонов пока нет. <Link to="/admin/dealers">Добавьте первый</Link>.</div>}
        </>
      )}
    </section>
  )
}
