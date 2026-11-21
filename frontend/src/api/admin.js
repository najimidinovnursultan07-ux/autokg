import { api } from './client.js'
import { downloadFile } from './download.js'

// Сводный отчёт по салонам: params = { from, to } (ГГГГ-ММ-ДД)
export async function getAdminReport(params = {}) {
  const { data } = await api.get('/admin/report/', { params })
  return data
}

export function downloadAdminReport({ from, to }) {
  const query = new URLSearchParams({ from, to }).toString()
  return downloadFile(`/admin/report/export/?${query}`, `autobuy-report-${from}_${to}.xlsx`)
}

export function downloadAdminReportPdf({ from, to }) {
  const query = new URLSearchParams({ from, to }).toString()
  return downloadFile(`/admin/report/pdf/?${query}`, `autobuy-report-${from}_${to}.pdf`)
}

export async function getAdminStats() {
  const { data } = await api.get('/admin/stats/')
  return data
}

export async function getAdminUsers(params = {}) {
  const { data } = await api.get('/admin/users/', { params })
  return data
}

export async function blockAdminUser(id) {
  const { data } = await api.post(`/admin/users/${id}/block/`)
  return data
}

export async function unblockAdminUser(id) {
  const { data } = await api.post(`/admin/users/${id}/unblock/`)
  return data
}

export async function getAdminCars(params = {}) {
  const { data } = await api.get('/admin/cars/', { params })
  return data
}

export async function deleteAdminCar(id) {
  await api.delete(`/admin/cars/${id}/`)
}

// Модерация: { status: 'active'|'hidden'|'sold' } и/или { dealer: id } (перенос в салон)
export async function updateAdminCar(id, payload) {
  const { data } = await api.patch(`/admin/cars/${id}/`, payload)
  return data
}

const catalogPaths = {
  brands: '/admin/brands/',
  models: '/admin/models/',
  cities: '/admin/cities/',
}

export async function getAdminCatalog(kind, params = {}) {
  const { data } = await api.get(catalogPaths[kind], { params })
  return data
}

export async function createAdminCatalogItem(kind, payload) {
  const { data } = await api.post(catalogPaths[kind], payload)
  return data
}

export async function updateAdminCatalogItem(kind, id, payload) {
  const { data } = await api.patch(`${catalogPaths[kind]}${id}/`, payload)
  return data
}

export async function deleteAdminCatalogItem(kind, id) {
  await api.delete(`${catalogPaths[kind]}${id}/`)
}
