import { api } from './client.js'

export async function getServicePrices() {
  const { data } = await api.get('/payments/prices/')
  return data
}

export async function createPayment(carId, serviceType) {
  const { data } = await api.post('/payments/create/', {
    car_id: carId,
    service_type: serviceType,
  })
  return data
}

export async function mockPay(paymentId, action = 'pay') {
  const { data } = await api.post('/payments/mock/', {
    payment_id: paymentId,
    action,
  })
  return data
}

export async function getPaymentHistory() {
  const { data } = await api.get('/payments/history/')
  return data
}

export async function getCarPromotions(carId) {
  const { data } = await api.get(`/payments/car/${carId}/promotions/`)
  return data
}
