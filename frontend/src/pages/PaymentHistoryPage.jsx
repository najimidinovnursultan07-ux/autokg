import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Clock3, RefreshCw, XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getPaymentHistory } from '../api/payments.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { getErrorMessage } from '../utils/errors.js'

const STATUS_CONFIG = {
  pending:   { label: 'Ожидает оплаты',   icon: Clock3,       color: '#f59e0b' },
  paid:      { label: 'Оплачено',          icon: CheckCircle2, color: '#22c55e' },
  failed:    { label: 'Ошибка оплаты',     icon: XCircle,      color: '#ef4444' },
  cancelled: { label: 'Отменено',          icon: XCircle,      color: '#94a3b8' },
  refunded:  { label: 'Возврат средств',   icon: RefreshCw,    color: '#3b82f6' },
}

const dateFormatter = new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' })

export default function PaymentHistoryPage() {
  const [payments, setPayments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getPaymentHistory()
      setPayments(data)
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить историю платежей.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <section className="account-page">
      <PageTitle
        eyebrow="Личный кабинет"
        title="История платежей"
        description="Все ваши транзакции по продвижению объявлений."
      />

      {loading ? <LoadingState label="Загружаем историю…" /> : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !payments.length ? (
        <div className="payment-empty">
          <Clock3 size={40} />
          <h3>История пуста</h3>
          <p>Здесь появятся платежи после первой оплаты продвижения.</p>
          <Link to="/dashboard" className="button button--primary">К объявлениям</Link>
        </div>
      ) : (
        <div className="payment-list">
          {payments.map((payment) => {
            const cfg = STATUS_CONFIG[payment.status] || STATUS_CONFIG.pending
            const Icon = cfg.icon
            return (
              <article className="payment-row" key={payment.id}>
                <span className="payment-status-icon" style={{ color: cfg.color }}>
                  <Icon size={20} />
                </span>
                <div className="payment-info">
                  <strong>{payment.service_type_label}</strong>
                  <span className="payment-car">
                    <Link to={`/cars/${payment.car}`}>{payment.car_title}</Link>
                  </span>
                  <span className="payment-date">
                    {dateFormatter.format(new Date(payment.created_at))}
                  </span>
                </div>
                <div className="payment-right">
                  <strong className="payment-amount">{payment.amount} {payment.currency}</strong>
                  <span className="payment-status-label" style={{ color: cfg.color }}>
                    {cfg.label}
                  </span>
                  {payment.promotion?.is_active && !payment.promotion?.is_expired && (
                    <span className="payment-expires">
                      до {dateFormatter.format(new Date(payment.promotion.expires_at))}
                    </span>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
