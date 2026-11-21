import { useEffect, useState } from 'react'
import { Check, Loader2, Star, TrendingUp, X, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getMySubscription, promoteCar } from '../../api/subscriptions.js'
import { useToast } from '../../context/ToastContext.jsx'
import { getErrorMessage } from '../../utils/errors.js'

const SERVICES = [
  { type: 'top', label: 'ТОП-объявление', hint: 'Всегда выше остальных в каталоге', icon: TrendingUp },
  { type: 'highlight', label: 'Выделить объявление', hint: 'Цветная рамка в списке', icon: Star },
  { type: 'urgent', label: 'Срочное объявление', hint: 'Отметка «Срочно»', icon: Zap },
]

export default function PromoteModal({ car, onClose, onPromoted }) {
  const { notify } = useToast()
  const [usage, setUsage] = useState(null)
  const [hasPlan, setHasPlan] = useState(true)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(null)
  const [activeTypes, setActiveTypes] = useState(
    () => new Set((car.promotions || []).filter((p) => new Date(p.expires_at) > new Date()).map((p) => p.promotion_type)),
  )

  useEffect(() => {
    getMySubscription()
      .then((data) => { setUsage(data.usage.promotions); setHasPlan(Boolean(data.subscription)) })
      .catch(() => notify('Не удалось загрузить бонусы тарифа.', 'error'))
      .finally(() => setLoading(false))
  }, [notify])

  const promote = async (type) => {
    setWorking(type)
    try {
      const result = await promoteCar(car.id, type)
      setUsage(result.usage.promotions)
      setActiveTypes((prev) => new Set(prev).add(type))
      notify(result.detail, 'success')
      onPromoted?.()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось включить продвижение.'), 'error')
    } finally {
      setWorking(null)
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="promote-title">
      <div className="modal-box promote-modal">
        <div className="modal-header">
          <h2 id="promote-title">Продвинуть объявление</h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Закрыть">
            <X size={20} />
          </button>
        </div>
        <p className="modal-subtitle">
          <strong>{car.brand} {car.model_name} {car.year}</strong>
        </p>

        {loading ? (
          <div className="promote-loading"><Loader2 size={24} className="spin" /> Загружаем бонусы…</div>
        ) : !hasPlan ? (
          <p className="promote-note">Тариф не активен. <Link to="/dashboard/subscription">Подключите тариф</Link>, чтобы продвигать объявления.</p>
        ) : (
          <div className="promote-cards">
            {SERVICES.map(({ type, label, hint, icon: Icon }) => {
              const quota = usage?.[type]
              const unlimited = quota?.left === null || quota?.left === undefined
              const left = unlimited ? Infinity : quota.left
              const isActive = activeTypes.has(type)
              return (
                <div key={type} className={`promote-card promote-card--${type} ${isActive ? 'promote-card--active' : ''}`}>
                  <div className="promote-card-icon"><Icon size={22} /></div>
                  <div className="promote-card-body">
                    <strong>{label}</strong>
                    <span>{hint} · 7 дней</span>
                  </div>
                  <div className="promote-card-price">
                    <strong>{unlimited ? 'без ограничений' : `осталось ${left} из ${quota.limit}`}</strong>
                    {isActive ? (
                      <span className="promote-active-label"><Check size={14} /> Активно</span>
                    ) : (
                      <button type="button" className="button button--primary promote-btn"
                        disabled={working !== null || left <= 0} onClick={() => promote(type)}>
                        {working === type ? <Loader2 size={15} className="spin" /> : null}
                        {working === type ? 'Включаем…' : left <= 0 ? 'Закончились' : 'Включить'}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <p className="promote-note">
          Продвижение входит в тариф: бонусы обновляются 1-го числа каждого месяца.
          Нужно больше — <Link to="/dashboard/subscription">перейдите на тариф выше</Link>.
        </p>
      </div>
    </div>
  )
}
