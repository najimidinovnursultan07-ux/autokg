import { formatPrice } from './format.js'

export const PERIODS = [
  { months: 1, label: '1 месяц', field: 'price_month' },
  { months: 3, label: '3 месяца', field: 'price_3_months' },
  { months: 12, label: '12 месяцев', field: 'price_12_months' },
]

export function planPrice(plan, months) {
  const period = PERIODS.find((p) => p.months === Number(months)) || PERIODS[0]
  return Number(plan?.[period.field] || 0)
}

const count = (value) => (value === null || value === undefined ? 'без ограничений' : value || '—')
const yes = (value) => (value ? '✓' : '—')

const PRIORITY = ['обычное', 'выше «Старта»', 'первыми + на главной']

// Строки сравнительной таблицы тарифов
export const PLAN_ROWS = [
  { label: 'Своя страница и кабинет, сам публикует', value: () => '✓' },
  { label: 'Активных объявлений одновременно', value: (p) => p.max_active_cars },
  { label: 'ТОП-поднятий в месяц', value: (p) => count(p.top_per_month) },
  { label: 'Выделений в месяц', value: (p) => count(p.highlight_per_month) },
  { label: '«Срочно» в месяц', value: (p) => count(p.urgent_per_month) },
  { label: 'Бейдж «Проверенный дилер»', value: (p) => yes(p.has_badge) },
  { label: 'Статистика объявлений', value: (p) => p.stats_level_label },
  { label: 'Загрузка объявлений из Excel', value: (p) => yes(p.has_excel_import) },
  { label: 'Место в списке дилеров', value: (p) => PRIORITY[p.list_priority] || PRIORITY[0] },
  { label: 'Поддержка', value: (p) => (p.priority_support ? 'приоритетная (ответ в течение часа)' : 'обычная') },
]

export function formatPlanPrice(plan, months = 1) {
  return formatPrice(planPrice(plan, months), 'KGS')
}

export function yearSavings(plan) {
  const full = Number(plan.price_month) * 12
  const year = Number(plan.price_12_months)
  return full > year ? full - year : 0
}
