import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, BadgeCheck, CarFront, Eye, FileText, MousePointerClick, Plus, Rocket } from 'lucide-react'
import { Link } from 'react-router-dom'
import { downloadDealerReportPdf, getDealerReport } from '../api/report.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { formatDate, formatPrice } from '../utils/format.js'

const num = (value) => (value === null || value === undefined ? '—' : new Intl.NumberFormat('ru-RU').format(value))
const STATUS = { active: 'На сайте', hidden: 'Скрыто', sold: 'Продано', deleted: 'Удалено' }

function Delta({ current, previous }) {
  if (current === null || previous === null || current === previous) return null
  const diff = current - previous
  return <em className={`report-delta ${diff > 0 ? 'report-delta--up' : 'report-delta--down'}`}>{diff > 0 ? '+' : '−'}{num(Math.abs(diff))} к прошлому месяцу</em>
}

function Tile({ icon: Icon, label, value, children, tone }) {
  return (
    <div className="admin-stat-card">
      <span className={`admin-stat-icon ${tone ? `admin-stat-icon--${tone}` : ''}`}><Icon size={19} /></span>
      <span className="admin-stat-copy"><small>{label}</small><strong>{value}</strong>{children}</span>
    </div>
  )
}

export default function DealerReportPage() {
  const { notify } = useToast()
  const [month, setMonth] = useState('')
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setReport(await getDealerReport(month))
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить отчёт.'))
    } finally {
      setLoading(false)
    }
  }, [month])

  useEffect(() => { load() }, [load])

  const downloadPdf = async () => {
    const left = report.downloads.left
    const ok = window.confirm(
      `Скачать PDF за ${report.month_label.toLowerCase()}?\n\n`
      + `PDF можно скачать не больше ${report.downloads.limit} раз в месяц. `
      + `После этого скачивания останется: ${left - 1}.`,
    )
    if (!ok) return
    setDownloading(true)
    try {
      await downloadDealerReportPdf(report.month)
      notify('PDF скачан. Сохраните файл — отчёты хранятся 12 месяцев.', 'success')
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось скачать PDF.'), 'error')
    } finally {
      setDownloading(false)
      load()
    }
  }

  if (loading && !report) return <LoadingState label="Собираем отчёт…" />
  if (error) return <ErrorState message={error} onRetry={load} />

  const { current: cur, previous: prev, listings, promotions, downloads } = report
  const contacts = report.show_contacts ? cur.phone_views + cur.whatsapp_clicks : null
  const prevContacts = report.show_contacts ? prev.phone_views + prev.whatsapp_clicks : null

  return (
    <section className="account-page dealer-report-page">
      <PageTitle
        eyebrow="Кабинет салона"
        title="Отчёт"
        description="Продажи, объявления и интерес покупателей за месяц. С 1-го числа отчёт начинается заново."
        action={(
          <div className="page-title-actions">
            <label className="field-label report-month">
              <span className="visually-hidden">Месяц</span>
              <select value={report.month} onChange={(e) => setMonth(e.target.value)} aria-label="Месяц отчёта">
                {report.months.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </label>
            <button type="button" className="button button--primary" onClick={downloadPdf} disabled={downloading || downloads.left <= 0}>
              <FileText size={17} />
              {downloading ? 'Готовим PDF…' : downloads.left > 0 ? `Скачать PDF (осталось ${downloads.left} из ${downloads.limit})` : 'Лимит PDF исчерпан'}
            </button>
          </div>
        )}
      />

      <div className="form-alert form-alert--warning report-warning" role="note">
        <AlertTriangle size={18} />
        <div>
          <strong>Внимание!</strong>
          <ul>
            <li>Данные отчёта хранятся <b>{report.retention_months} месяцев</b>, затем удаляются навсегда. Отчёт за {report.month_label.toLowerCase()} будет удалён <b>{formatDate(report.deleted_after)}</b>.</li>
            <li>PDF можно скачать <b>не больше {downloads.limit} раз в месяц</b> (в этом месяце скачано: {downloads.used}). Лимит обновляется 1-го числа.</li>
            <li>Скачивайте и сохраняйте нужные отчёты заранее — восстановить удалённые данные нельзя.</li>
          </ul>
        </div>
      </div>

      <p className="report-period">
        {report.month_label}{report.is_current_month && ' · месяц ещё идёт, цифры обновляются'}
        {report.plan.name ? ` · тариф «${report.plan.name}»${report.plan.is_trial ? ' (пробный)' : ''} до ${formatDate(report.plan.expires_at)}` : ' · тариф не активен'}
        {loading && ' · обновляем…'}
      </p>

      <div className="admin-stat-grid report-kpis">
        <Tile icon={BadgeCheck} tone="green" label="Продано за месяц" value={num(cur.cars_sold)}>
          <Delta current={cur.cars_sold} previous={prev.cars_sold} />
        </Tile>
        <Tile icon={Plus} tone="blue" label="Добавлено объявлений" value={num(cur.cars_added)}>
          <Delta current={cur.cars_added} previous={prev.cars_added} />
        </Tile>
        <Tile icon={Eye} label="Просмотры" value={num(cur.views)}>
          <Delta current={cur.views} previous={prev.views} />
        </Tile>
        <Tile icon={MousePointerClick} label="Контакты (номер + WhatsApp)" value={num(contacts)}>
          {report.show_contacts
            ? <em>номер {num(cur.phone_views)} · WhatsApp {num(cur.whatsapp_clicks)}{cur.contact_rate !== null && ` · ${cur.contact_rate}% просмотров`}</em>
            : <em>доступно на «Бизнесе» и «Премиуме»</em>}
          {report.show_contacts && <Delta current={contacts} previous={prevContacts} />}
        </Tile>
        <Tile icon={CarFront} label="Объявления сейчас" value={`${num(listings.on_site)} / ${num(listings.limit)}`}>
          <em>всего {num(listings.total)} · скрыто {num(listings.hidden)} · срок истёк {num(listings.expired)} · продано {num(listings.sold)}</em>
        </Tile>
        <Tile icon={Rocket} tone="amber" label="Продвижения за месяц" value={num(promotions.top + promotions.highlight + promotions.urgent)}>
          <em>ТОП {promotions.top} · выделение {promotions.highlight} · срочно {promotions.urgent}</em>
        </Tile>
      </div>

      <h2 className="admin-section-title">Продано за месяц: {report.sold.length}</h2>
      {report.sold.length ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Автомобиль</th><th>Цена</th><th>Дата продажи</th><th>Дней на сайте</th></tr></thead>
            <tbody>
              {report.sold.map((car) => (
                <tr key={car.car_id}>
                  <td><Link to={`/dashboard/cars/${car.car_id}/edit`}><strong>{car.title}</strong></Link></td>
                  <td>{formatPrice(car.price, car.currency)}</td>
                  <td>{formatDate(car.sold_at)}</td>
                  <td>{car.days_on_site}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="empty-inline">В этом месяце продаж не отмечено. Проданную машину отмечайте кнопкой «Отметить проданным» в списке объявлений.</p>}

      <h2 className="admin-section-title">Объявления по просмотрам за месяц</h2>
      {report.top_cars.length ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr><th>Автомобиль</th><th>Статус</th><th>Цена</th><th>Просмотры</th>{report.show_contacts && <><th>Номер</th><th>WhatsApp</th></>}</tr>
            </thead>
            <tbody>
              {report.top_cars.map((car, index) => (
                <tr key={car.car_id || `deleted-${index}`}>
                  <td>{car.car_id ? <Link to={`/dashboard/cars/${car.car_id}/edit`}>{car.title}</Link> : car.title}</td>
                  <td><span className={`admin-status admin-status--${car.status === 'deleted' ? 'inactive' : car.status}`}>{STATUS[car.status] || car.status}</span></td>
                  <td>{car.price ? formatPrice(car.price, car.currency) : '—'}</td>
                  <td>{num(car.views)}</td>
                  {report.show_contacts && <><td>{num(car.phone_views)}</td><td>{num(car.whatsapp_clicks)}</td></>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="empty-inline">Просмотров за этот месяц пока нет.</p>}

      <p className="field-hint">
        Просмотры и контакты по месяцам считаются с ноября 2026 года. Свои просмотры (из кабинета салона) не учитываются.
      </p>
    </section>
  )
}
