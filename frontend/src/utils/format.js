export function formatPrice(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return 'Цена не указана'
  return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(amount)} сом`
}

export function formatMileage(value) {
  return `${new Intl.NumberFormat('ru-RU').format(Number(value) || 0)} км`
}

export function getCarTitle(car) {
  return [car.brand, car.model_name, car.year].filter(Boolean).join(' ')
}

export function getCarCover(car) {
  const image = car.images?.find((item) => item.is_cover) || car.images?.[0]
  return image?.image || ''
}
