import { formatDate } from './format.js'

// Срок размещения объявления (дни); 0 — без срока. Совпадает с LISTING_DURATIONS на бэкенде.
export const LISTING_DURATIONS = [
  [7, '7 дней'],
  [14, '14 дней'],
  [30, '30 дней'],
  [60, '60 дней'],
  [90, '90 дней'],
  [0, 'Без срока'],
]
export const DEFAULT_LISTING_DAYS = 30

export function daysUntil(value) {
  if (!value) return null
  return Math.ceil((new Date(value).getTime() - Date.now()) / 86_400_000)
}

// Подпись срока для кабинета: { text, tone: 'expired' | 'soon' | 'ok' | 'none' }
export function listingExpiry(car) {
  if (!car?.expires_at) return { text: 'Без срока', tone: 'none' }
  if (car.is_expired) return { text: 'Срок истёк', tone: 'expired' }
  const days = daysUntil(car.expires_at)
  return {
    text: `до ${formatDate(car.expires_at)} · ${days} дн.`,
    tone: days <= 3 ? 'soon' : 'ok',
  }
}
