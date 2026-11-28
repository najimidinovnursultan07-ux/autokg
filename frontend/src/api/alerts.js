import { api } from './client.js'

// Подписка на новые объявления по фильтрам каталога → ссылка на Telegram-бота
export async function createSearchAlert(filters, title) {
  const { data } = await api.post('/alerts/searches/', { filters, title })
  return data
}

// Слежение за ценой объявления → ссылка на Telegram-бота
export async function createPriceWatch(carId) {
  const { data } = await api.post('/alerts/watches/', { car: carId })
  return data
}
