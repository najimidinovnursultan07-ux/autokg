import { useCallback, useEffect, useMemo, useState } from 'react'
import { Ban, Check, MessageCircle, Plus, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  activateSubscription,
  deactivateSubscription,
  getAdminPlans,
  getAdminSubscriptions,
  getPlanRequests,
  getSubscriptionsOverview,
  updatePlanRequest,
} from '../api/subscriptions.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { whatsappLink } from '../utils/contacts.js'
import { getErrorMessage } from '../utils/errors.js'
import { formatDate, formatPrice } from '../utils/format.js'
import { PERIODS, planPrice } from '../utils/plans.js'

const TABS = [['requests', 'Заявки'], ['dealers', 'Салоны'], ['history', 'История оплат']]
const METHODS = [['', 'Не указан'], ['cash', 'Наличные'], ['transfer', 'Перевод'], ['invoice', 'Счёт'], ['other', 'Другое']]

function ActivateModal({ initial, plans, dealers, onClose, onDone }) {
  const { notify } = useToast()
  const [form, setForm] = useState(() => {
    const plan = plans.find((p) => p.id === initial.plan) || plans[0]
    const months = initial.months || 1
    return {
      dealer: initial.dealer || '',
      plan: plan?.id || '',
      months,
      amount: plan ? String(planPrice(plan, months)) : '',
      payment_method: '',
      note: '',
    }
  })
  const [saving, setSaving] = useState(false)
  const set = (key) => (e) => setForm((f) => {
    const next = { ...f, [key]: e.target.value }
    if (key === 'plan' || key === 'months') {
      const plan = plans.find((p) => String(p.id) === String(next.plan))
      if (plan) next.amount = String(planPrice(plan, next.months))
    }
    return next
  })

  const current = dealers.find((d) => String(d.dealer) === String(form.dealer))?.subscription
  const samePlan = current && String(current.plan.id) === String(form.plan)

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await activateSubscription({
        dealer: Number(form.dealer),
        plan: Number(form.plan),
        months: Number(form.months),
        amount: form.amount === '' ? null : form.amount,
        payment_method: form.payment_method,
        note: form.note.trim(),
        request_id: initial.requestId || null,
      })
      notify('Тариф включён.', 'success')
      onDone()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось включить тариф.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="admin-modal-backdrop" role="presentation">
      <form className="admin-modal admin-modal--wide" role="dialog" aria-modal="true" aria-labelledby="activate-title" onSubmit={submit}>
        <h2 id="activate-title">Включить тариф</h2>
        <p className="field-hint">Отметьте, что оплата получена. На сайте деньги не принимаются — сумма и способ нужны только для учёта.</p>
        <div className="form-grid">
          <label className="field-label">Автосалон *
            <select required value={form.dealer} onChange={set('dealer')} disabled={Boolean(initial.dealer)}>
              <option value="">Выберите салон</option>
              {dealers.map((d) => <option key={d.dealer} value={d.dealer}>{d.dealer_name}</option>)}
            </select>
          </label>
          <label className="field-label">Тариф *
            <select required value={form.plan} onChange={set('plan')}>
              {plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
          <label className="field-label">Срок *
            <select value={form.months} onChange={set('months')}>
              {PERIODS.map((p) => <option key={p.months} value={p.months}>{p.label}</option>)}
            </select>
          </label>
          <label className="field-label">Получено, сом
            <input type="number" min="0" step="1" value={form.amount} onChange={set('amount')} />
          </label>
          <label className="field-label">Способ оплаты
            <select value={form.payment_method} onChange={set('payment_method')}>
              {METHODS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="field-label">Комментарий
            <input maxLength="500" value={form.note} onChange={set('note')} placeholder="№ перевода, кто принял…" />
          </label>
        </div>
        {current && (
          <p className="field-hint">
            Сейчас: {current.plan.name}{current.is_trial ? ' (пробный)' : ''} до {formatDate(current.expires_at)}.{' '}
            {samePlan ? 'Тот же тариф — новый срок добавится после окончания текущего.' : 'Другой тариф — текущий закончится сейчас, новый начнётся сразу.'}
          </p>
        )}
        <div className="admin-modal-actions">
          <button type="button" className="button button--secondary" onClick={onClose}>Отмена</button>
          <button type="submit" className="button button--primary" disabled={saving}>{saving ? 'Включаем…' : 'Включить тариф'}</button>
        </div>
      </form>
    </div>
  )
}

export default function AdminSubscriptionsPage() {
  const { notify } = useToast()
  const [tab, setTab] = useState('requests')
  const [plans, setPlans] = useState([])
  const [dealers, setDealers] = useState([])
  const [requests, setRequests] = useState([])
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)
  const [workingId, setWorkingId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [p, d, r, h] = await Promise.all([
        getAdminPlans(), getSubscriptionsOverview(), getPlanRequests({ status: 'new', page_size: 100 }), getAdminSubscriptions(),
      ])
      setPlans(p)
      setDealers(d)
      setRequests(r.results || r)
      setHistory(h)
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить тарифы.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const sortedDealers = useMemo(() => [...dealers].sort((a, b) => {
    // Сначала без тарифа, затем у кого раньше заканчивается
    const ea = a.subscription ? new Date(a.subscription.expires_at).getTime() : 0
    const eb = b.subscription ? new Date(b.subscription.expires_at).getTime() : 0
    return ea - eb
  }), [dealers])

  const reject = async (req) => {
    setWorkingId(`r${req.id}`)
    try {
      await updatePlanRequest(req.id, { status: 'rejected' })
      notify('Заявка отклонена.', 'success')
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось изменить заявку.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const deactivate = async (row) => {
    if (!window.confirm(`Отключить тариф салона «${row.dealer_name}»? Объявления сразу скроются с сайта.`)) return
    setWorkingId(`d${row.dealer}`)
    try {
      const result = await deactivateSubscription(row.dealer)
      notify(result.detail, 'success')
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось отключить тариф.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const done = () => { setModal(null); load() }

  return (
    <section className="admin-page">
      <PageTitle
        eyebrow="Администрирование"
        title="Тарифы салонов"
        description="Заявки на подключение, текущие тарифы и учёт оплат. Оплата принимается вне сайта, тариф включает администратор."
        action={<button type="button" className="button button--primary" onClick={() => setModal({})}><Plus size={17} /> Включить тариф</button>}
      />
      <div className="admin-tabs" role="tablist">
        {TABS.map(([value, label]) => (
          <button key={value} type="button" role="tab" aria-selected={tab === value}
            className={`admin-tab ${tab === value ? 'admin-tab--active' : ''}`} onClick={() => setTab(value)}>
            {label}{value === 'requests' && requests.length > 0 && <span className="tab-count">{requests.length}</span>}
          </button>
        ))}
      </div>

      {loading ? <LoadingState label="Загружаем…" /> : error ? <ErrorState message={error} onRetry={load} /> : (
        <>
          {tab === 'requests' && (requests.length ? (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead><tr><th>Салон</th><th>Тариф</th><th>Срок</th><th>К оплате</th><th>Комментарий</th><th>Дата</th><th>Действия</th></tr></thead>
                <tbody>
                  {requests.map((req) => {
                    const plan = plans.find((p) => p.id === req.plan)
                    const phone = req.dealer_whatsapp || req.dealer_phone
                    return (
                      <tr key={req.id}>
                        <td><strong>{req.dealer_name}</strong><br /><small>{req.dealer_phone || req.created_by_email}</small></td>
                        <td>{req.plan_name}</td>
                        <td>{req.months} мес.</td>
                        <td>{plan ? formatPrice(planPrice(plan, req.months), 'KGS') : '—'}</td>
                        <td>{req.comment || '—'}</td>
                        <td>{formatDate(req.created_at)}</td>
                        <td>
                          <div className="table-actions">
                            {phone && (
                              <a className="icon-action" href={whatsappLink(phone, `Здравствуйте! По заявке на тариф «${req.plan_name}» на AutoBuy.`)}
                                target="_blank" rel="noreferrer" title="Написать в WhatsApp" aria-label="Написать в WhatsApp"><MessageCircle size={16} /></a>
                            )}
                            <button type="button" className="button button--primary" disabled={workingId !== null}
                              onClick={() => setModal({ dealer: req.dealer, plan: req.plan, months: req.months, requestId: req.id })}>
                              <Check size={16} /> Оплачено — включить
                            </button>
                            <button type="button" className="icon-action icon-action--danger" disabled={workingId !== null}
                              onClick={() => reject(req)} title="Отклонить" aria-label="Отклонить"><X size={16} /></button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : <p className="empty-inline">Новых заявок нет.</p>)}

          {tab === 'dealers' && (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead><tr><th>Салон</th><th>Тариф</th><th>Действует до</th><th>Оплачено до</th><th>Действия</th></tr></thead>
                <tbody>
                  {sortedDealers.map((row) => {
                    const sub = row.subscription
                    const soon = sub && sub.days_left <= 3
                    return (
                      <tr key={row.dealer}>
                        <td>
                          <Link to={`/dealers/${row.dealer_slug}`} target="_blank"><strong>{row.dealer_name}</strong></Link>
                          {!row.dealer_is_active && <><br /><small>салон отключён</small></>}
                          {row.has_new_request && <><br /><span className="admin-status admin-status--pending">есть заявка</span></>}
                        </td>
                        <td>
                          {sub
                            ? <span className="admin-status admin-status--active">{sub.plan.name}{sub.is_trial ? ' · пробный' : ''}</span>
                            : <span className="admin-status admin-status--rejected">Нет тарифа</span>}
                        </td>
                        <td className={soon ? 'days-left--soon' : ''}>{sub ? `${formatDate(sub.expires_at)} (${sub.days_left} дн.)` : '—'}</td>
                        <td>{row.paid_until ? formatDate(row.paid_until) : '—'}</td>
                        <td>
                          <div className="table-actions">
                            <button type="button" className="button button--outline" disabled={workingId !== null}
                              onClick={() => setModal({ dealer: row.dealer, plan: sub?.plan.id })}>
                              {sub ? 'Продлить / сменить' : 'Включить'}
                            </button>
                            {sub && (
                              <button type="button" className="icon-action icon-action--danger" disabled={workingId !== null}
                                onClick={() => deactivate(row)} title="Отключить тариф" aria-label="Отключить тариф"><Ban size={16} /></button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {tab === 'history' && (history.length ? (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead><tr><th>Салон</th><th>Тариф</th><th>Период</th><th>Получено</th><th>Способ</th><th>Комментарий</th><th>Кто включил</th></tr></thead>
                <tbody>
                  {history.map((s) => (
                    <tr key={s.id}>
                      <td>{s.dealer_name}</td>
                      <td>{s.plan.name}{s.is_trial ? ' · пробный' : ''}</td>
                      <td>{formatDate(s.starts_at)} — {formatDate(s.expires_at)}</td>
                      <td>{s.amount !== null ? formatPrice(s.amount, 'KGS') : '—'}</td>
                      <td>{s.payment_method_label || '—'}</td>
                      <td>{s.note || '—'}</td>
                      <td>{s.created_by_email || 'система'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="empty-inline">Записей пока нет.</p>)}
        </>
      )}

      {modal && <ActivateModal initial={modal} plans={plans} dealers={dealers} onClose={() => setModal(null)} onDone={done} />}
    </section>
  )
}
