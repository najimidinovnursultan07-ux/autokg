import { api } from './client.js'

export async function getPaymentHistory() {
  const { data } = await api.get('/payments/history/')
  return data
}

export async function getCarPromotions(carId) {
  const { data } = await api.get(`/payments/car/${carId}/promotions/`)
  return data
}
