import { api } from './client.js'
import { downloadFile } from './download.js'

// ── Публичный каталог ──
export async function listCars(params = {}) {
  const { data } = await api.get('/cars/', { params })
  return data
}

export async function getCar(id) {
  const { data } = await api.get(`/cars/${id}/`)
  return data
}

export async function getLookups() {
  const [brands, models, cities] = await Promise.all([
    api.get('/brands/'),
    api.get('/models/'),
    api.get('/cities/'),
  ])
  return { brands: brands.data, models: models.data, cities: cities.data }
}

// ── Кабинет салона: /api/dashboard/cars/ ──
export async function listDashboardCars(params = {}) {
  const { data } = await api.get('/dashboard/cars/', { params })
  return data
}

export async function getDashboardCar(id) {
  const { data } = await api.get(`/dashboard/cars/${id}/`)
  return data
}

export async function saveDashboardCar(payload, id) {
  const response = id
    ? await api.patch(`/dashboard/cars/${id}/`, payload)
    : await api.post('/dashboard/cars/', payload)
  return response.data
}

export async function setDashboardCarStatus(id, status) {
  const { data } = await api.patch(`/dashboard/cars/${id}/`, { status })
  return data
}

export async function deleteDashboardCar(id) {
  await api.delete(`/dashboard/cars/${id}/`)
}

// ── Загрузка из Excel (тарифы «Бизнес» и «Премиум») ──
export function downloadImportTemplate() {
  return downloadFile('/dashboard/cars/import-template/', 'autobuy-import-template.xlsx')
}

export async function importDashboardCars(file, publish) {
  const form = new FormData()
  form.append('file', file)
  form.append('publish', publish ? '1' : '0')
  const { data } = await api.post('/dashboard/cars/import/', form)
  return data
}

// Загрузка фото пачками (до 15 фото на машину, до 5 МБ каждое)
export async function uploadCarPhotos(id, files, onBatchUploaded) {
  if (!files.length) return []
  const uploaded = []
  const batchLimit = 5
  for (let i = 0; i < files.length; i += batchLimit) {
    const batch = files.slice(i, i + batchLimit)
    const formData = new FormData()
    batch.forEach((file) => formData.append('images', file))
    const { data } = await api.post(`/dashboard/cars/${id}/photos/`, formData)
    uploaded.push(...data)
    if (onBatchUploaded) await onBatchUploaded(data, batch)
  }
  return uploaded
}

export async function deleteCarPhoto(carId, photoId) {
  await api.delete(`/dashboard/cars/${carId}/photos/${photoId}/`)
}

export async function setMainCarPhoto(carId, photoId) {
  const { data } = await api.post(`/dashboard/cars/${carId}/photos/${photoId}/main/`)
  return data
}

// «Показать номер» / «Написать в WhatsApp»: номер отдаётся только здесь, клик считается
export async function revealCarContacts(id, kind) {
  const { data } = await api.post(`/cars/${id}/contacts/`, { kind })
  return data
}
