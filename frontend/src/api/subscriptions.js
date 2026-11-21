import { api } from './client.js'
import { downloadFile } from './download.js'

// ── Публичные ──
export async function getPlans() {
  const { data } = await api.get('/plans/')
  return data
}

// ── Кабинет салона ──
export async function getMySubscription() {
  const { data } = await api.get('/dashboard/subscription/')
  return data
}

export async function createPlanRequest(payload) {
  const { data } = await api.post('/dashboard/subscription/requests/', payload)
  return data
}

export async function promoteCar(carId, promotionType) {
  const { data } = await api.post('/dashboard/promote/', { car_id: carId, promotion_type: promotionType })
  return data
}

export function downloadStatsExport() {
  return downloadFile('/dashboard/stats-export/', 'stats.csv')
}

// ── Админ ──
export async function getAdminPlans() {
  const { data } = await api.get('/admin/plans/')
  return data
}

export async function getSubscriptionsOverview() {
  const { data } = await api.get('/admin/subscriptions/overview/')
  return data
}

export async function getAdminSubscriptions(params = {}) {
  const { data } = await api.get('/admin/subscriptions/', { params })
  return data
}

export async function activateSubscription(payload) {
  const { data } = await api.post('/admin/subscriptions/', payload)
  return data
}

export async function deactivateSubscription(dealerId) {
  const { data } = await api.post('/admin/subscriptions/deactivate/', { dealer: dealerId })
  return data
}

export async function getPlanRequests(params = {}) {
  const { data } = await api.get('/admin/plan-requests/', { params })
  return data
}

export async function updatePlanRequest(id, payload) {
  const { data } = await api.patch(`/admin/plan-requests/${id}/`, payload)
  return data
}
