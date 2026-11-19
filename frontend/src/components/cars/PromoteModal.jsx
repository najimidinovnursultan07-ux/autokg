import { useEffect, useState } from 'react'
import { ArrowRight, Loader2, Star, TrendingUp, X, Zap } from 'lucide-react'
import { createPayment, getServicePrices } from '../../api/payments.js'
import { useToast } from '../../context/ToastContext.jsx'
import { getErrorMessage } from '../../utils/errors.js'

const SERVICE_ICONS = {
  top: TrendingUp,
  highlight: Star,
  urgent: Zap,
}

const SERVICE_COLORS = {
  top: 'promote-card--top',
  highlight: 'promote-card--highlight',
  urgent: 'promote-card--urgent',
}

export default function PromoteModal({ car, onClose, onPaymentCreated }) {
  const { notify } = useToast()
  const [prices, setPrices] = useState([])
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(null)

  useEffect(() => {
    getServicePrices()
      .then(setPrices)
      .catch(() => notify('Не удалось загрузить тарифы.', 'error'))
      .finally(() => setLoading(false))
  }, [notify])

  const handlePromote = async (serviceType) => {
    setWorking(serviceType)
    try {
      const result = await createPayment(car.id, serviceType)
      onPaymentCreated(result)
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось создать платёж.'), 'error')
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
          <div className="promote-loading"><Loader2 size={24} className="spin" /> Загружаем тарифы…</div>
        ) : (
          <div className="promote-cards">
            {prices.map((price) => {
              const Icon = SERVICE_ICONS[price.service_type] || Star
              const isWorking = working === price.service_type
              const alreadyActive = (() => {
                if (!car.promotions) return false
                return car.promotions.some(
                  (p) => p.promotion_type === price.service_type &&
                    new Date(p.expires_at) > new Date()
                )
              })()

              return (
                <div
                  key={price.service_type}
                  className={`promote-card ${SERVICE_COLORS[price.service_type] || ''} ${alreadyActive ? 'promote-card--active' : ''}`}
                >
                  <div className="promote-card-icon">
                    <Icon size={22} />
                  </div>
                  <div className="promote-card-body">
                    <strong>{price.label}</strong>
                    <span>{price.duration_days} дней</span>
                  </div>
                  <div className="promote-card-price">
                    <strong>{price.amount} {price.currency}</strong>
                    {alreadyActive ? (
                      <span className="promote-active-label">Активно</span>
                    ) : (
                      <button
                        type="button"
                        className="button button--primary promote-btn"
                        disabled={isWorking}
                        onClick={() => handlePromote(price.service_type)}
                      >
                        {isWorking ? <Loader2 size={15} className="spin" /> : <ArrowRight size={15} />}
                        {isWorking ? 'Создаём…' : 'Выбрать'}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <p className="promote-note">
          Оплата через безопасный платёжный шлюз. Услуга активируется сразу после подтверждения оплаты.
        </p>
      </div>
    </div>
  )
}
