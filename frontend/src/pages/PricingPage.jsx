import { useEffect, useState } from 'react'
import { Check, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getPlans } from '../api/subscriptions.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { SUPPORT_PHONE, whatsappLink } from '../utils/contacts.js'
import { getErrorMessage } from '../utils/errors.js'
import { formatPrice } from '../utils/format.js'
import { PERIODS, PLAN_ROWS, planPrice, yearSavings } from '../utils/plans.js'

export default function PricingPage() {
  const { user } = useAuth()
  const isDealer = user?.role === 'dealer'
  const [plans, setPlans] = useState([])
  const [months, setMonths] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    setError('')
    getPlans()
      .then(setPlans)
      .catch((err) => setError(getErrorMessage(err, 'Не удалось загрузить тарифы.')))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const popular = 'business'

  return (
    <section className="container page-section pricing-page">
      <PageTitle
        eyebrow="Автосалонам"
        title="Тарифы"
        description="На любом тарифе у салона своя страница и кабинет — объявления публикуете сами. Оплата не на сайте: оставьте заявку, менеджер свяжется с вами."
      />

      <div className="period-switch" role="tablist" aria-label="Срок оплаты">
        {PERIODS.map((p) => (
          <button key={p.months} type="button" role="tab" aria-selected={months === p.months}
            className={`period-switch-btn ${months === p.months ? 'period-switch-btn--active' : ''}`}
            onClick={() => setMonths(p.months)}>
            {p.label}{p.months === 3 && <small>−10%</small>}{p.months === 12 && <small>2 мес. в подарок</small>}
          </button>
        ))}
      </div>

      {loading ? <LoadingState label="Загружаем тарифы…" /> : error ? <ErrorState message={error} onRetry={load} /> : (
        <>
          <div className="plan-cards">
            {plans.map((plan) => {
              const total = planPrice(plan, months)
              const savings = months === 12 ? yearSavings(plan) : 0
              return (
                <article key={plan.id} className={`plan-card ${plan.code === popular ? 'plan-card--popular' : ''}`}>
                  {plan.code === popular && <span className="plan-card-tag">Популярный</span>}
                  <h2>{plan.name}</h2>
                  <p className="plan-card-price">
                    <strong>{formatPrice(total / months, 'KGS')}</strong><span>/ мес.</span>
                  </p>
                  <p className="plan-card-total">
                    {months === 1 ? 'Оплата помесячно' : `${formatPrice(total, 'KGS')} за ${months} мес.`}
                    {savings > 0 && <> · экономия {formatPrice(savings, 'KGS')}</>}
                  </p>
                  <ul className="plan-card-features">
                    <li><Check size={15} /> До {plan.max_active_cars} объявлений одновременно</li>
                    <li><Check size={15} /> {plan.top_per_month} ТОП и {plan.highlight_per_month} выделений в месяц</li>
                    <li><Check size={15} /> «Срочно»: {plan.urgent_per_month ?? 'без ограничений'}</li>
                    {plan.has_badge && <li><Check size={15} /> Бейдж «Проверенный дилер»</li>}
                    <li><Check size={15} /> Статистика: {plan.stats_level_label.toLowerCase()}</li>
                  </ul>
                  {isDealer ? (
                    <Link to={`/dashboard/subscription?plan=${plan.id}&months=${months}`}
                      className={`button ${plan.code === popular ? 'button--primary' : 'button--outline'} button--wide`}>
                      Подключить <ChevronRight size={16} />
                    </Link>
                  ) : (
                    <a href={whatsappLink(SUPPORT_PHONE, `Здравствуйте! Хочу подключить автосалон на тариф «${plan.name}» (${months} мес.).`)}
                      target="_blank" rel="noreferrer"
                      className={`button ${plan.code === popular ? 'button--primary' : 'button--outline'} button--wide`}>
                      Оставить заявку <ChevronRight size={16} />
                    </a>
                  )}
                </article>
              )
            })}
          </div>

          <div className="admin-table-wrap plan-compare">
            <table className="admin-table">
              <thead>
                <tr><th>Сравнение тарифов</th>{plans.map((p) => <th key={p.id}>{p.name}</th>)}</tr>
              </thead>
              <tbody>
                {PLAN_ROWS.map((row) => (
                  <tr key={row.label}>
                    <td>{row.label}</td>
                    {plans.map((p) => <td key={p.id}>{row.value(p)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pricing-notes">
            <p><strong>Новым салонам — 14 дней «Бизнеса» бесплатно.</strong> Можно сразу выложить машины и посмотреть, как всё работает.</p>
            <p>Лимит объявлений — сколько машин может быть на сайте одновременно. Проданные и скрытые не считаются.</p>
            <p>Бонусы продвижения (ТОП, выделение, «Срочно» — по 7 дней) обновляются 1-го числа и не накапливаются.</p>
            <p>Если тариф закончился, объявления скрываются с сайта, но не удаляются — после продления всё вернётся.</p>
          </div>
        </>
      )}
    </section>
  )
}
