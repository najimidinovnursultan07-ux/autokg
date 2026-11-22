import { API_BASE_URL, api } from './client.js'
import { downloadFile } from './download.js'

// ---- Сайт ----

// Все баннеры, которые показываются сегодня. Без кэша: новый или запущенный баннер виден сразу.
// Одновременные запросы с разных мест показа всё равно склеиваются в один (см. api.get в client.js).
export function getAds() {
  return api.get('/ads/')
    .then(({ data }) => (Array.isArray(data) ? data : []))
    .catch(() => [])
}

// Переход по баннеру идёт через API: там считается клик и делается редирект на сайт рекламодателя
export function adClickUrl(id) {
  return `${API_BASE_URL.replace(/\/$/, '')}/ads/${id}/click/`
}

// Показы копятся и отправляются пачкой
const pending = new Set()
let flushTimer = null

function flushImpressions() {
  clearTimeout(flushTimer)
  flushTimer = null
  if (!pending.size) return
  const ids = [...pending].slice(0, 10)
  ids.forEach((id) => pending.delete(id))
  api.post('/ads/impressions/', { ids }).catch(() => {})
  if (pending.size) flushImpressions()
}

export function trackAdImpression(id) {
  pending.add(id)
  if (!flushTimer) flushTimer = setTimeout(flushImpressions, 1500)
}

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flushImpressions()
  })
}

// ---- Админка ----

export const AD_PLACEMENTS = [
  { value: 'home_top', label: 'Главная — сверху', size: '1200×300 (телефон 800×400)' },
  { value: 'home_middle', label: 'Главная — между блоками', size: '1200×300 (телефон 800×400)' },
  { value: 'catalog_feed', label: 'Каталог — в списке объявлений', size: '1200×300 (телефон 800×400)' },
  { value: 'car_detail', label: 'Страница авто — рядом с контактами', size: '600×400' },
]

export async function getAdminAds(params = {}) {
  const { data } = await api.get('/admin/ads/', { params })
  return data
}

export async function createAdminAd(formData) {
  const { data } = await api.post('/admin/ads/', formData)
  return data
}

export async function updateAdminAd(id, payload) {
  const { data } = await api.patch(`/admin/ads/${id}/`, payload)
  return data
}

export async function deleteAdminAd(id) {
  await api.delete(`/admin/ads/${id}/`)
}

export async function getAdminAdStats(id, params = {}) {
  const { data } = await api.get(`/admin/ads/${id}/stats/`, { params })
  return data
}

export function downloadAdminAdStats(id, { from, to } = {}) {
  const query = new URLSearchParams(Object.entries({ from, to }).filter(([, v]) => v)).toString()
  return downloadFile(`/admin/ads/${id}/stats/export/${query ? `?${query}` : ''}`, `autobuy-ad-${id}.xlsx`)
}

// Прайс на рекламу: цена места показа за 7 и 30 дней
export async function getAdPrices() {
  const { data } = await api.get('/admin/ad-prices/')
  return data
}

export async function saveAdPrices(rows) {
  const { data } = await api.put('/admin/ad-prices/', rows)
  return data
}

// Сумма за период по прайсу: целые 30 дни — по месячной цене, остаток — неделями
// (но не дороже месяца). Пример: 45 дней = 1 месяц + 3 недели.
export function calcAdPrice(price, startsOn, endsOn) {
  if (!price || !startsOn || !endsOn) return null
  const days = Math.round((new Date(`${endsOn}T00:00:00`) - new Date(`${startsOn}T00:00:00`)) / 86400000) + 1
  if (!(days > 0)) return null
  const week = Number(price.price_week) || 0
  const month = Number(price.price_month) || 0
  const months = Math.floor(days / 30)
  const weeks = Math.ceil((days % 30) / 7)
  const rest = month ? Math.min(weeks * week, month) : weeks * week
  return { days, months, weeks, total: months * month + rest }
}
