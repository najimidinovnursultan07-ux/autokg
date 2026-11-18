import { useCallback, useEffect, useState } from 'react'
import { GitCompareArrows, Trash2, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getCar } from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import { LoadingState } from '../components/common/States.jsx'
import { clearCompare, getCompareList, removeFromCompare } from '../utils/compare.js'
import { formatMileage, formatPrice, getCarTitle } from '../utils/format.js'

const labels = {
  engine_type: { petrol: 'Бензин', diesel: 'Дизель', hybrid: 'Гибрид', electric: 'Электро', lpg: 'Газ', other: 'Другое' },
  transmission: { manual: 'Механика', automatic: 'Автомат', cvt: 'Вариатор', robotic: 'Робот' },
  drive_type: { fwd: 'Передний', rwd: 'Задний', awd: 'Полный' },
  body_type: { sedan: 'Седан', hatchback: 'Хэтчбек', suv: 'Внедорожник', wagon: 'Универсал', coupe: 'Купе', minivan: 'Минивэн', pickup: 'Пикап', other: 'Другое' },
  condition: { new: 'Новый', used: 'С пробегом', damaged: 'Требует ремонта' },
}

const rows = [
  { key: 'price', label: 'Цена', format: (v) => formatPrice(v) },
  { key: 'year', label: 'Год выпуска' },
  { key: 'mileage', label: 'Пробег', format: (v) => formatMileage(v) },
  { key: 'engine_type', label: 'Двигатель', format: (v) => labels.engine_type[v] || v },
  { key: 'engine_volume', label: 'Объём', format: (v) => v ? `${v} л` : '—' },
  { key: 'transmission', label: 'Коробка', format: (v) => labels.transmission[v] || v },
  { key: 'drive_type', label: 'Привод', format: (v) => labels.drive_type[v] || v },
  { key: 'body_type', label: 'Кузов', format: (v) => labels.body_type[v] || v },
  { key: 'condition', label: 'Состояние', format: (v) => labels.condition[v] || v },
  { key: 'city_name', label: 'Город' },
  { key: 'views_count', label: 'Просмотры' },
]

export default function ComparePage() {
  const [compareList, setCompareList] = useState(() => getCompareList())
  const [cars, setCars] = useState([])
  const [loading, setLoading] = useState(false)

  const loadCars = useCallback(async () => {
    if (!compareList.length) { setCars([]); return }
    setLoading(true)
    try {
      const results = await Promise.all(compareList.map((item) => getCar(item.id)))
      setCars(results)
    } catch {
      setCars([])
    } finally {
      setLoading(false)
    }
  }, [compareList])

  useEffect(() => { loadCars() }, [loadCars])

  useEffect(() => {
    const update = () => setCompareList(getCompareList())
    window.addEventListener('autokg:compare-updated', update)
    return () => window.removeEventListener('autokg:compare-updated', update)
  }, [])

  const remove = (id) => {
    removeFromCompare(id)
    setCompareList(getCompareList())
    setCars((prev) => prev.filter((c) => c.id !== id))
  }

  const clear = () => {
    clearCompare()
    setCompareList([])
    setCars([])
  }

  return (
    <section className="container page-section">
      <div className="compare-heading">
        <div>
          <span className="eyebrow">AutoKG</span>
          <h1><GitCompareArrows size={28} /> Сравнение автомобилей</h1>
        </div>
        {cars.length > 0 && (
          <button type="button" className="button button--outline" onClick={clear}>
            <Trash2 size={16} /> Очистить всё
          </button>
        )}
      </div>

      {loading ? <LoadingState label="Загружаем данные…" /> : !cars.length ? (
        <div className="compare-empty">
          <GitCompareArrows size={48} />
          <h2>Список сравнения пуст</h2>
          <p>Перейдите в каталог и нажмите «Сравнить» на странице автомобиля.</p>
          <Link to="/catalog" className="button button--primary">Перейти в каталог</Link>
        </div>
      ) : (
        <div className="compare-table-wrap">
          <table className="compare-table">
            <thead>
              <tr>
                <th className="compare-label-col"></th>
                {cars.map((car) => (
                  <th key={car.id} className="compare-car-col">
                    <div className="compare-car-header">
                      <button type="button" className="compare-remove" onClick={() => remove(car.id)} aria-label="Удалить"><X size={15} /></button>
                      <Link to={`/cars/${car.id}`}>
                        {car.images?.[0]?.image
                          ? <img src={resolveMediaUrl(car.images[0].image)} alt={getCarTitle(car)} className="compare-car-img" />
                          : <div className="compare-car-img compare-car-img--placeholder">AutoKG</div>
                        }
                        <strong>{getCarTitle(car)}</strong>
                      </Link>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(({ key, label, format }) => {
                const values = cars.map((car) => (format ? format(car[key]) : car[key]) ?? '—')
                const allSame = values.every((v) => v === values[0])
                return (
                  <tr key={key} className="compare-row">
                    <td className="compare-row-label">{label}</td>
                    {values.map((value, i) => (
                      <td key={cars[i].id} className={`compare-row-value ${!allSame && cars.length > 1 ? 'compare-row-value--diff' : ''}`}>
                        {value}
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
