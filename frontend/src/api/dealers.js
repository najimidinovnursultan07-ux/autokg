import { api } from './client.js'

// Публичные
export async function getDealers() {
  const { data } = await api.get('/dealers/')
  return data
}

export async function getDealerBySlug(slug) {
  const { data } = await api.get(`/dealers/${slug}/`)
  return data
}

// Дилер — кабинет
export async function getDealerProfile() {
  const { data } = await api.get('/dashboard/dealer/')
  return data
}

export async function updateDealerProfile(payload) {
  const { data } = await api.patch('/dashboard/dealer/', payload)
  return data
}

export async function getDealerCars() {
  const { data } = await api.get('/dashboard/cars/')
  return data
}

// Админ
export async function getAdminDealers() {
  const { data } = await api.get('/admin/dealers/')
  return data
}

export async function createAdminDealer(payload) {
  const { data } = await api.post('/admin/dealers/', payload)
  return data
}

export async function updateAdminDealer(id, payload) {
  const { data } = await api.patch(`/admin/dealers/${id}/`, payload)
  return data
}

export async function deleteAdminDealer(id) {
  await api.delete(`/admin/dealers/${id}/`)
}

export async function toggleDealerActive(id) {
  const { data } = await api.post(`/admin/dealers/${id}/toggle_active/`)
  return data
}

export async function getAdminManagers() {
  const { data } = await api.get('/admin/managers/')
  return data
}

export async function createAdminManager(payload) {
  const { data } = await api.post('/admin/managers/', payload)
  return data
}

export async function updateAdminManager(id, payload) {
  const { data } = await api.patch(`/admin/managers/${id}/`, payload)
  return data
}

export async function getDealerStats() {
  const { data } = await api.get('/admin/dealer-stats/')
  return data
}
