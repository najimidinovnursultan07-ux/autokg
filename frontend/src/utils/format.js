export function formatPrice(value, currency = 'KGS') {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return 'Цена не указана'
  const formatted = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(amount)
  return currency === 'USD' ? `$${formatted}` : `${formatted} сом`
}

export function formatMileage(value) {
  return `${new Intl.NumberFormat('ru-RU').format(Number(value) || 0)} км`
}

export function getCarTitle(car) {
  return [car.brand, car.model_name, car.year].filter(Boolean).join(' ')
}

// variant: 'thumb' (w_400, карточки), 'url' (w_1600, галерея), 'image' (оригинал)
export function getCarCover(car, variant = 'thumb') {
  const image = car.images?.find((item) => item.is_cover) || car.images?.[0]
  return image?.[variant] || image?.image || ''
}

export const CAR_STATUS_LABELS = {
  active: 'Активно',
  hidden: 'Скрыто',
  sold: 'Продано',
}

// Пересчёт по курсу НБКР: USD → сом и сом → USD (для подписи «≈ …» под ценой)
export function convertPrice(value, currency, rates) {
  const amount = Number(value)
  const usd = Number(rates?.rates?.USD)
  if (!Number.isFinite(amount) || !usd) return null
  if (currency === 'USD') return { amount: amount * usd, currency: 'KGS' }
  if (currency === 'KGS') return { amount: amount / usd, currency: 'USD' }
  return null
}

export function formatConvertedPrice(value, currency, rates) {
  const converted = convertPrice(value, currency, rates)
  if (!converted) return ''
  const rounded = converted.currency === 'KGS'
    ? Math.round(converted.amount / 1000) * 1000
    : Math.round(converted.amount / 10) * 10
  return `≈ ${formatPrice(rounded, converted.currency)}`
}

export function formatDate(value) {
  if (!value) return ''
  return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(value))
}

// Объём двигателя без лишних нулей: «2.500» → «2.5 л», «0.050» → «0.05 л»
export function formatEngineVolume(value) {
  const amount = Number(value)
  return value && Number.isFinite(amount) && amount > 0 ? `${amount} л` : '—'
}
