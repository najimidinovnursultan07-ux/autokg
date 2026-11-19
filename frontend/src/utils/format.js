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
