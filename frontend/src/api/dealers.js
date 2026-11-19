import { api } from './client.js'

// ── Публичные ──
export async function getDealers() {
  const { data } = await api.get('/dealers/')
  return data
}

export async function getDealerBySlug(slug) {
  const { data } = await api.get(`/dealers/${encodeURIComponent(slug)}/`)
  return data
}

// ── Кабинет салона ──
export async function getDealerProfile() {
  const { data } = await api.get('/dashboard/dealer/')
  return data
}

// payload: объект или FormData (если меняется логотип)
export async function updateDealerProfile(payload) {
  const { data } = await api.patch('/dashboard/dealer/', payload)
  return data
}

// ── Админ: салоны ──
export async function getAdminDealers(params = {}) {
  const { data } = await api.get('/admin/dealers/', { params })
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

// ── Админ: менеджеры ──
export async function getAdminManagers(params = {}) {
  const { data } = await api.get('/admin/managers/', { params })
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

export async function resetManagerPassword(id, password) {
  const { data } = await api.post(`/admin/managers/${id}/reset-password/`, { password })
  return data
}

export async function deleteAdminManager(id) {
  await api.delete(`/admin/managers/${id}/`)
}
