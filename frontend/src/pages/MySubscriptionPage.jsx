import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, Download, Send } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { createPlanRequest, downloadStatsExport, getMySubscription, getPlans } from '../api/subscriptions.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { formatDate, formatPrice } from '../utils/format.js'
import { PERIODS, planPrice } from '../utils/plans.js'

const REQUEST_STATUS_CLASS = { new: 'pending', done: 'published', rejected: 'rejected' }

function UsageBar({ label, used, limit }) {
  const unlimited = limit === null || limit === undefined
  const percent = unlimited || !limit ? 0 : Math.min(100, Math.round((used / limit) * 100))
  return (
    <div className="usage-item">
      <div className="usage-item-top">
        <span>{label}</span>
        <strong>{unlimited ? `${used} · без ограничений` : `${used} из ${limit}`}</strong>
      </div>
      <div className="usage-bar"><span style={{ width: `${percent}%` }} className={percent >= 100 ? 'usage-bar-full' : ''} /></div>
    </div>
  )
}

export default function MySubscriptionPage() {
  const { notify } = useToast()
  const [searchParams] = useSearchParams()
  const [data, setData] = useState(null)
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    plan: searchParams.get('plan') || '',
    months: Number(searchParams.get('months')) || 1,
    comment: '',
  })
  const [sending, setSending] = useState(false)
  const [exporting, setExporting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [mine, allPlans] = await Promise.all([getMySubscription(), getPlans()])
      setData(mine)
      setPlans(allPlans)
      setForm((f) => ({ ...f, plan: f.plan || String(mine.subscription?.plan.id || allPlans[1]?.id || allPlans[0]?.id || '') }))
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить тариф.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const send = async (e) => {
    e.preventDefault()
    setSending(true)
    try {
      const result = await createPlanRequest({ plan: Number(form.plan), months: Number(form.months), comment: form.comment.trim() })
      notify(result.detail, 'success')
      setForm((f) => ({ ...f, comment: '' }))
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось отправить заявку.'), 'error')
    } finally {
      setSending(false)
    }
  }

  const exportStats = async () => {
    setExporting(true)
    try {
      await downloadStatsExport()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось выгрузить статистику.'), 'error')
    } finally {
      setExporting(false)
    }
  }

  if (loading && !data) return <LoadingState label="Загружаем тариф…" />
  if (error) return <ErrorState message={error} onRetry={load} />

  const { subscription, usage, upcoming, requests } = data
  const plan = subscription?.plan
  const selectedPlan = plans.find((p) => String(p.id) === String(form.plan))
  const pendingRequest = requests.find((r) => r.status === 'new')
  const promotions = Object.entries(usage.promotions)

  return (
    <section className="account-page">
      <PageTitle
        eyebrow="Кабинет салона"
        title="Мой тариф"
        description="Лимиты, бонусы продвижения и продление. Оплата — напрямую менеджеру, не на сайте."
        action={<Link className="button button--outline" to="/pricing">Сравнить тарифы</Link>}
      />

      {!subscription && (
        <div className="form-alert dealer-blocked-alert" role="alert">
          <AlertTriangle size={17} />
          <span>Тариф не активен: объявления скрыты с сайта, публиковать новые нельзя. Оставьте заявку ниже — после оплаты всё вернётся.</span>
        </div>
      )}

      {subscription && (
        <div className="subscription-summary">
          <div>
            <span className="eyebrow">{subscription.is_trial ? 'Пробный период' : 'Текущий тариф'}</span>
            <h2>{plan.name}</h2>
            <p>
              Действует до <strong>{formatDate(subscription.expires_at)}</strong>
              {' · '}
              <span className={subscription.days_left <= 3 ? 'days-left--soon' : ''}>
                осталось {subscription.days_left} дн.
              </span>
            </p>
            {upcoming.length > 0 && (
              <p className="field-hint">
                Оплачено продление: {upcoming.map((u) => `${u.plan.name} до ${formatDate(u.expires_at)}`).join(', ')}
              </p>
            )}
          </div>
          {plan.stats_level === 'export' && (
            <button type="button" className="button button--outline" onClick={exportStats} disabled={exporting}>
              <Download size={16} /> {exporting ? 'Готовим файл…' : 'Статистика в Excel'}
            </button>
          )}
        </div>
      )}

      <div className="usage-grid">
        <UsageBar label="Активные объявления" used={usage.active_cars} limit={usage.max_active_cars} />
        {promotions.map(([type, p]) => (
          <UsageBar key={type} label={`${p.label} в этом месяце`} used={p.used} limit={p.limit} />
        ))}
      </div>
      <p className="field-hint">Бонусы продвижения обновляются 1-го числа каждого месяца. Продвинуть объявление — кнопка с ракетой в списке объявлений.</p>

      <form className="subscription-request" onSubmit={send}>
        <h2>{subscription ? 'Продлить или сменить тариф' : 'Подключить тариф'}</h2>
        {pendingRequest && (
          <p className="field-hint">
            Заявка от {formatDate(pendingRequest.created_at)} ({pendingRequest.plan_name}, {pendingRequest.months} мес.) ждёт обработки. Новая заявка заменит её.
          </p>
        )}
        <div className="form-grid">
          <label className="field-label">Тариф
            <select value={form.plan} onChange={(e) => setForm({ ...form, plan: e.target.value })} required>
              {plans.map((p) => <option key={p.id} value={p.id}>{p.name} — до {p.max_active_cars} объявлений</option>)}
            </select>
          </label>
          <label className="field-label">Срок
            <select value={form.months} onChange={(e) => setForm({ ...form, months: Number(e.target.value) })}>
              {PERIODS.map((p) => <option key={p.months} value={p.months}>{p.label}</option>)}
            </select>
          </label>
        </div>
        <label className="field-label">Комментарий (необязательно)
          <input maxLength="500" value={form.comment} onChange={(e) => setForm({ ...form, comment: e.target.value })} placeholder="Удобное время для звонка, способ оплаты…" />
        </label>
        <div className="subscription-request-footer">
          {selectedPlan && <span>К оплате: <strong>{formatPrice(planPrice(selectedPlan, form.months), 'KGS')}</strong></span>}
          <button type="submit" className="button button--primary" disabled={sending || !form.plan}>
            <Send size={16} /> {sending ? 'Отправляем…' : 'Отправить заявку'}
          </button>
        </div>
        <p className="field-hint">
          {plan && selectedPlan && String(selectedPlan.id) === String(plan.id)
            ? 'Тот же тариф — продление начнётся после окончания текущего срока.'
            : 'Другой тариф включится сразу после оплаты.'}
        </p>
      </form>

      {requests.length > 0 && (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Заявка</th><th>Срок</th><th>Дата</th><th>Статус</th></tr></thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id}>
                  <td>{r.plan_name}</td>
                  <td>{r.months} мес.</td>
                  <td>{formatDate(r.created_at)}</td>
                  <td><span className={`admin-status admin-status--${REQUEST_STATUS_CLASS[r.status]}`}>{r.status_label}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
