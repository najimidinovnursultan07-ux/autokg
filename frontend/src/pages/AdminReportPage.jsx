import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowDown, ArrowUp, Building2, CarFront, Download, FileText, Inbox, MousePointerClick, Search, Wallet,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { downloadAdminReport, downloadAdminReportPdf, getAdminReport } from '../api/admin.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { formatDate, formatPrice } from '../utils/format.js'

const num = (value) => new Intl.NumberFormat('ru-RU').format(Number(value) || 0)
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

function presetRange(preset) {
  const today = new Date()
  const y = today.getFullYear()
  const m = today.getMonth()
  switch (preset) {
    case 'prev_month': return [iso(new Date(y, m - 1, 1)), iso(new Date(y, m, 0))]
    case '30d': return [iso(new Date(y, m, today.getDate() - 29)), iso(today)]
    case '90d': return [iso(new Date(y, m, today.getDate() - 89)), iso(today)]
    case 'year': return [iso(new Date(y, 0, 1)), iso(today)]
    case 'all': return ['2020-01-01', iso(today)]
    default: return [iso(new Date(y, m, 1)), iso(today)]
  }
}

const PRESETS = [
  ['month', 'Этот месяц'], ['prev_month', 'Прошлый месяц'], ['30d', '30 дней'],
  ['90d', '90 дней'], ['year', 'Этот год'], ['all', 'Всё время'], ['custom', 'Свой период'],
]

// Колонки таблицы: ключ сортировки, заголовок, подсказка
const COLUMNS = [
  ['name', 'Салон'],
  ['days_left', 'Тариф'],
  ['cars_on_site', 'На сайте', 'Видны покупателям / лимит тарифа'],
  ['cars_expired', 'Срок истёк'],
  ['cars_hidden', 'Скрыто'],
  ['cars_sold', 'Продано'],
  ['cars_added', 'Добавлено', 'Новые объявления за период'],
  ['views', 'Просмотры', 'За всё время'],
  ['phone_views', 'Номер', 'Открыли номер, за всё время'],
  ['whatsapp_clicks', 'WhatsApp', 'Нажали WhatsApp, за всё время'],
  ['contact_rate', 'Конверсия', '(номер + WhatsApp) / просмотры'],
  ['promotions', 'Продвижения', 'ТОП / выделение / «Срочно» за период'],
  ['revenue', 'Оплачено', 'Получено за тариф в периоде'],
  ['rating', 'Рейтинг'],
  ['new_requests', 'Заявки', 'Необработанные заявки на тариф'],
]

function sortValue(row, key) {
  if (key === 'name') return row.name.toLowerCase()
  if (key === 'revenue') return Number(row.revenue)
  if (key === 'promotions') return row.promo_top + row.promo_highlight + row.promo_urgent
  if (key === 'days_left') return row.days_left ?? -1
  return row[key] ?? -1
}

function KpiTile({ icon: Icon, label, value, note, tone, to }) {
  const content = (
    <>
      <span className={`admin-stat-icon ${tone ? `admin-stat-icon--${tone}` : ''}`}><Icon size={19} /></span>
      <span className="admin-stat-copy"><small>{label}</small><strong>{value}</strong>{note && <em>{note}</em>}</span>
    </>
  )
  return to ? <Link to={to} className="admin-stat-card">{content}</Link> : <div className="admin-stat-card">{content}</div>
}

export default function AdminReportPage() {
  const { notify } = useToast()
  const [preset, setPreset] = useState('month')
  const [range, setRange] = useState(() => presetRange('month'))
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState('')
  const [search, setSearch] = useState('')
  const [planFilter, setPlanFilter] = useState('')
  const [sort, setSort] = useState({ key: 'revenue', dir: 'desc' })

  const [from, to] = range

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setReport(await getAdminReport({ from, to }))
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить отчёт.'))
    } finally {
      setLoading(false)
    }
  }, [from, to])

  useEffect(() => { load() }, [load])

  const choosePreset = (value) => {
    setPreset(value)
    if (value !== 'custom') setRange(presetRange(value))
  }

  // exporting: '' | 'xlsx' | 'pdf'
  const exportReport = async (format) => {
    setExporting(format)
    try {
      await (format === 'pdf' ? downloadAdminReportPdf : downloadAdminReport)({ from, to })
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось выгрузить отчёт.'), 'error')
    } finally {
      setExporting('')
    }
  }

  const rows = useMemo(() => {
    if (!report) return []
    const q = search.trim().toLowerCase()
    const filtered = report.rows.filter((r) => {
      if (q && !`${r.name} ${r.city}`.toLowerCase().includes(q)) return false
      if (planFilter === 'none') return r.plan === null
      if (planFilter === 'trial') return r.is_trial
      if (planFilter) return r.plan_code === planFilter && !r.is_trial
      return true
    })
    const factor = sort.dir === 'asc' ? 1 : -1
    return [...filtered].sort((a, b) => {
      const va = sortValue(a, sort.key)
      const vb = sortValue(b, sort.key)
      return (va > vb ? 1 : va < vb ? -1 : 0) * factor || a.name.localeCompare(b.name)
    })
  }, [report, search, planFilter, sort])

  const totals = useMemo(() => {
    const sum = (key) => rows.reduce((acc, r) => acc + (Number(r[key]) || 0), 0)
    const views = sum('views')
    return {
      cars_on_site: sum('cars_on_site'), cars_expired: sum('cars_expired'), cars_hidden: sum('cars_hidden'),
      cars_sold: sum('cars_sold'), cars_added: sum('cars_added'), views, phone_views: sum('phone_views'),
      whatsapp_clicks: sum('whatsapp_clicks'),
      contact_rate: views ? Math.round(((sum('phone_views') + sum('whatsapp_clicks')) / views) * 1000) / 10 : null,
      promo_top: sum('promo_top'), promo_highlight: sum('promo_highlight'), promo_urgent: sum('promo_urgent'),
      revenue: sum('revenue'), new_requests: sum('new_requests'),
    }
  }, [rows])

  const toggleSort = (key) => setSort((s) => (
    s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: key === 'name' ? 'asc' : 'desc' }
  ))

  const s = report?.summary

  return (
    <section className="admin-page report-page">
      <PageTitle
        eyebrow="Администрирование"
        title="Отчёт по автосалонам"
        description="Тарифы, объявления, интерес покупателей и оплаты по всем салонам."
        action={(
          <div className="page-title-actions">
            <button type="button" className="button button--outline" onClick={() => exportReport('pdf')} disabled={Boolean(exporting) || !report}>
              <FileText size={17} /> {exporting === 'pdf' ? 'Готовим PDF…' : 'Скачать PDF'}
            </button>
            <button type="button" className="button button--primary" onClick={() => exportReport('xlsx')} disabled={Boolean(exporting) || !report}>
              <Download size={17} /> {exporting === 'xlsx' ? 'Готовим файл…' : 'Скачать Excel'}
            </button>
          </div>
        )}
      />

      <div className="report-filters">
        <label className="field-label">Период
          <select value={preset} onChange={(e) => choosePreset(e.target.value)}>
            {PRESETS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="field-label">С
          <input type="date" value={from} max={to} onChange={(e) => { setPreset('custom'); setRange([e.target.value, to]) }} />
        </label>
        <label className="field-label">По
          <input type="date" value={to} min={from} onChange={(e) => { setPreset('custom'); setRange([from, e.target.value]) }} />
        </label>
      </div>

      {loading && !report ? <LoadingState label="Собираем отчёт…" /> : error ? <ErrorState message={error} onRetry={load} /> : report && (
        <>
          <p className="report-period">
            За период {formatDate(report.period.from)} — {formatDate(report.period.to)}
            {loading && ' · обновляем…'}
          </p>

          <div className="admin-stat-grid report-kpis">
            <KpiTile icon={Wallet} tone="green" label="Оплачено за период" value={formatPrice(s.revenue, 'KGS')} note={`оплат: ${s.payments}`} to="/admin/subscriptions" />
            <KpiTile icon={Building2} tone="blue" label="Автосалоны" value={s.dealers}
              note={`платных ${s.dealers_paid} · пробных ${s.dealers_trial} · без тарифа ${s.dealers_without_plan}`} to="/admin/dealers" />
            <KpiTile icon={CarFront} label="Объявлений на сайте" value={num(s.cars_on_site)}
              note={`+${num(s.cars_added)} за период · продано ${num(s.cars_sold)}`} to="/admin/cars" />
            <KpiTile icon={MousePointerClick} label="Контакты покупателей" value={num(s.phone_views + s.whatsapp_clicks)}
              note={`из ${num(s.views)} просмотров · за всё время`} />
            <KpiTile icon={AlertTriangle} tone="amber" label="Тариф кончается ≤ 7 дн." value={s.expiring_soon}
              note={s.dealers_without_plan ? `без тарифа: ${s.dealers_without_plan}` : 'все с тарифом'} to="/admin/subscriptions" />
            <KpiTile icon={Inbox} label="Ждут обработки" value={s.new_requests + s.reviews_pending}
              note={`заявок ${s.new_requests} · отзывов ${s.reviews_pending}`} to={s.new_requests ? '/admin/subscriptions' : '/admin/reviews'} />
          </div>

          <div className="report-plans" aria-label="Салоны по тарифам">
            <span>Салоны по тарифам:</span>
            {Object.entries(report.plans).map(([label, count]) => (
              <span key={label} className="report-plan-chip">{label} <strong>{count}</strong></span>
            ))}
          </div>

          <div className="admin-toolbar report-toolbar">
            <label className="admin-search-form">
              <Search size={18} />
              <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Салон или город" aria-label="Поиск салона" />
            </label>
            <select className="report-plan-filter" value={planFilter} onChange={(e) => setPlanFilter(e.target.value)} aria-label="Фильтр по тарифу">
              <option value="">Все тарифы</option>
              <option value="premium">Премиум</option>
              <option value="business">Бизнес</option>
              <option value="start">Старт</option>
              <option value="trial">Пробный период</option>
              <option value="none">Без тарифа</option>
            </select>
          </div>

          <div className="admin-table-wrap report-table-wrap">
            <table className="admin-table report-table">
              <thead>
                <tr>
                  {COLUMNS.map(([key, label, hint]) => (
                    <th key={key} title={hint} aria-sort={sort.key === key ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                      <button type="button" className="report-sort" onClick={() => toggleSort(key)}>
                        {label}
                        {sort.key === key && (sort.dir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.dealer}>
                    <td>
                      <Link to={`/dealers/${r.slug}`} target="_blank"><strong>{r.name}</strong></Link>
                      <br /><small>{[r.city, r.phone].filter(Boolean).join(' · ') || '—'}</small>
                      {!r.is_active && <><br /><span className="admin-status admin-status--blocked">отключён</span></>}
                    </td>
                    <td>
                      {r.plan
                        ? <>
                            <span className="admin-status admin-status--active">{r.plan}{r.is_trial ? ' · пробный' : ''}</span>
                            <br /><small className={r.days_left <= 7 ? 'days-left--soon' : ''}>до {formatDate(r.expires_at)} · {r.days_left} дн.</small>
                          </>
                        : <span className="admin-status admin-status--rejected">Нет тарифа</span>}
                    </td>
                    <td>{r.cars_on_site}{r.max_cars ? <small> / {r.max_cars}</small> : null}</td>
                    <td>{r.cars_expired || '—'}</td>
                    <td>{r.cars_hidden || '—'}</td>
                    <td>{r.cars_sold || '—'}</td>
                    <td>{r.cars_added || '—'}</td>
                    <td>{num(r.views)}</td>
                    <td>{num(r.phone_views)}</td>
                    <td>{num(r.whatsapp_clicks)}</td>
                    <td>{r.contact_rate === null ? '—' : `${r.contact_rate}%`}</td>
                    <td>{r.promo_top + r.promo_highlight + r.promo_urgent ? `${r.promo_top} / ${r.promo_highlight} / ${r.promo_urgent}` : '—'}</td>
                    <td>{Number(r.revenue) ? formatPrice(r.revenue, 'KGS') : '—'}</td>
                    <td>{r.rating ? `★ ${r.rating.toFixed(1)}` : '—'}<br /><small>{r.reviews} отз.{r.reviews_pending ? ` · ${r.reviews_pending} на проверке` : ''}</small></td>
                    <td>{r.new_requests ? <Link to="/admin/subscriptions" className="admin-status admin-status--pending">{r.new_requests}</Link> : '—'}</td>
                  </tr>
                ))}
              </tbody>
              {rows.length > 1 && (
                <tfoot>
                  <tr>
                    <td><strong>Итого ({rows.length})</strong></td>
                    <td />
                    <td>{num(totals.cars_on_site)}</td>
                    <td>{num(totals.cars_expired)}</td>
                    <td>{num(totals.cars_hidden)}</td>
                    <td>{num(totals.cars_sold)}</td>
                    <td>{num(totals.cars_added)}</td>
                    <td>{num(totals.views)}</td>
                    <td>{num(totals.phone_views)}</td>
                    <td>{num(totals.whatsapp_clicks)}</td>
                    <td>{totals.contact_rate === null ? '—' : `${totals.contact_rate}%`}</td>
                    <td>{totals.promo_top} / {totals.promo_highlight} / {totals.promo_urgent}</td>
                    <td>{formatPrice(totals.revenue, 'KGS')}</td>
                    <td />
                    <td>{totals.new_requests || '—'}</td>
                  </tr>
                </tfoot>
              )}
            </table>
            {!rows.length && <p className="empty-inline">Под фильтр не попал ни один салон.</p>}
          </div>
          <p className="field-hint">
            Просмотры, открытия номера и WhatsApp — за всё время (сайт пока не хранит их по дням).
            Добавленные объявления, продвижения, оплаты и отзывы — за выбранный период.
          </p>
        </>
      )}
    </section>
  )
}
