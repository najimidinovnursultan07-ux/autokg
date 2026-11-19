import { useCallback, useEffect, useState } from 'react'
import { Edit3, EyeOff, Plus, Send, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getDealerCars } from '../api/dealers.js'
import { deactivateCar, deleteCar, submitCar } from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import { LoadingState, ErrorState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { formatPrice, getCarCover, getCarTitle } from '../utils/format.js'

const statuses = {
  draft: 'Черновик', pending: 'На модерации', published: 'Опубликовано',
  rejected: 'Отклонено', inactive: 'Снято', sold: 'Продано',
}

export default function DealerDashboardPage() {
  const { notify } = useToast()
  const [cars, setCars] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [workingId, setWorkingId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setCars(await getDealerCars())
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить объявления.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const act = async (car, action) => {
    setWorkingId(car.id)
    try {
      if (action === 'delete') {
        if (!window.confirm(`Удалить «${getCarTitle(car)}»?`)) return
        await deleteCar(car.id)
        notify('Удалено.', 'success')
      } else if (action === 'submit') {
        await submitCar(car.id)
        notify('Отправлено на модерацию.', 'success')
      } else if (action === 'deactivate') {
        await deactivateCar(car.id)
        notify('Снято с публикации.', 'success')
      }
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Ошибка.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  return (
    <section className="account-page">
      <PageTitle
        eyebrow="Кабинет"
        title="Мои объявления"
        description="Управляйте объявлениями своего автосалона."
        action={<Link className="button button--primary" to="/cars/new"><Plus size={17} /> Добавить</Link>}
      />
      {loading ? <LoadingState label="Загружаем…" /> : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <div className="my-cars-list">
          {cars.map((car) => {
            const image = getCarCover(car)
            return (
              <article className="my-car-row" key={car.id}>
                <Link to={`/cars/${car.id}/edit`} className="my-car-thumb">
                  {image ? <img src={resolveMediaUrl(image)} alt="" /> : null}
                </Link>
                <div className="my-car-info">
                  <span className={`status-pill status-pill--${car.status}`}>{statuses[car.status] || car.status}</span>
                  <Link className="my-car-title" to={`/cars/${car.id}/edit`}>{getCarTitle(car)}</Link>
                  <span className="my-car-price">{formatPrice(car.price)}</span>
                </div>
                <div className="my-car-actions">
                  <Link className="icon-action" to={`/cars/${car.id}/edit`}><Edit3 size={17} /></Link>
                  {['draft', 'rejected'].includes(car.status) && (
                    <button className="icon-action" type="button" disabled={workingId === car.id}
                      onClick={() => act(car, 'submit')}><Send size={17} /></button>
                  )}
                  {car.status === 'published' && (
                    <button className="icon-action" type="button" disabled={workingId === car.id}
                      onClick={() => act(car, 'deactivate')}><EyeOff size={17} /></button>
                  )}
                  <button className="icon-action icon-action--danger" type="button"
                    disabled={workingId === car.id} onClick={() => act(car, 'delete')}><Trash2 size={17} /></button>
                </div>
              </article>
            )
          })}
          {!cars.length && <p className="empty-inline">Объявлений пока нет. Добавьте первое!</p>}
        </div>
      )}
    </section>
  )
}
