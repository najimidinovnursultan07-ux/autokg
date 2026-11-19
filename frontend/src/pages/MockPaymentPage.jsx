import { useEffect, useState } from 'react'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { mockPay } from '../api/payments.js'
import { useToast } from '../context/ToastContext.jsx'

export default function MockPaymentPage() {
  const [searchParams] = useSearchParams()
  const paymentId = searchParams.get('payment_id')
  const navigate = useNavigate()
  const { notify } = useToast()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const pay = async (action) => {
    setLoading(true)
    try {
      const data = await mockPay(paymentId, action)
      setResult({ success: action === 'pay', message: data.detail })
      if (action === 'pay') {
        notify('Оплата прошла успешно!', 'success')
        setTimeout(() => navigate('/my-cars'), 2000)
      }
    } catch (err) {
      setResult({ success: false, message: err?.response?.data?.detail || 'Ошибка оплаты.' })
    } finally {
      setLoading(false)
    }
  }

  if (!paymentId) {
    return (
      <section className="container page-section">
        <div className="mock-payment-card">
          <XCircle size={48} color="#ef4444" />
          <h2>Неверная ссылка</h2>
          <p>Идентификатор платежа не найден.</p>
          <button className="button button--primary" onClick={() => navigate('/my-cars')}>
            Мои объявления
          </button>
        </div>
      </section>
    )
  }

  return (
    <section className="container page-section">
      <div className="mock-payment-card">
        {result ? (
          <>
            {result.success
              ? <CheckCircle2 size={56} color="#22c55e" />
              : <XCircle size={56} color="#ef4444" />
            }
            <h2>{result.success ? 'Оплата прошла!' : 'Оплата не прошла'}</h2>
            <p>{result.message}</p>
            <button className="button button--primary" onClick={() => navigate('/my-cars')}>
              Мои объявления
            </button>
          </>
        ) : (
          <>
            <div className="mock-payment-badge">TEST</div>
            <h2>Тестовая оплата</h2>
            <p className="mock-payment-desc">
              Это тестовый платёжный шлюз. Реальные деньги не списываются.
            </p>
            <div className="mock-payment-actions">
              <button
                className="button button--primary"
                disabled={loading}
                onClick={() => pay('pay')}
              >
                {loading ? <Loader2 size={17} className="spin" /> : <CheckCircle2 size={17} />}
                Оплатить (тест)
              </button>
              <button
                className="button button--outline"
                disabled={loading}
                onClick={() => pay('cancel')}
              >
                <XCircle size={17} /> Отменить
              </button>
            </div>
          </>
        )}
      </div>
    </section>
  )
}
