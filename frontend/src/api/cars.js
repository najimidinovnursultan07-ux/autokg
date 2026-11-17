import { api } from './client.js'

export async function listCars(params = {}) {
  const { data } = await api.get('/cars/', { params })
  return data
}

export async function getCar(id) {
  const { data } = await api.get(`/cars/${id}/`)
  return data
}

export async function getMyCars(params = {}) {
  const { data } = await api.get('/my-cars/', { params })
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

export async function saveCar(payload, id) {
  const response = id
    ? await api.patch(`/cars/${id}/`, payload)
    : await api.post('/cars/', payload)
  return response.data
}

export async function uploadCarImages(id, files, onBatchUploaded) {
  if (!files.length) return []
  const uploaded = []
  let batch = []
  let batchSize = 0
  const uploadBatch = async () => {
    if (!batch.length) return
    const formData = new FormData()
    batch.forEach((file) => formData.append('images', file))
    const { data } = await api.post(`/cars/${id}/images/`, formData)
    uploaded.push(...data)
    if (onBatchUploaded) await onBatchUploaded(data, batch)
    batch = []
    batchSize = 0
  }
  for (const file of files) {
    if (batch.length === 10 || batchSize + file.size > 30 * 1024 * 1024) {
      await uploadBatch()
    }
    batch.push(file)
    batchSize += file.size
  }
  await uploadBatch()
  return uploaded
}

export async function submitCar(id) {
  const { data } = await api.post(`/cars/${id}/submit/`)
  return data
}

export async function deactivateCar(id) {
  const { data } = await api.post(`/cars/${id}/deactivate/`)
  return data
}

export async function reactivateCar(id) {
  const { data } = await api.post(`/cars/${id}/reactivate/`)
  return data
}

export async function deleteCar(id) {
  await api.delete(`/cars/${id}/`)
}

export async function deleteCarImage(carId, imageId) {
  await api.delete(`/cars/${carId}/images/${imageId}/`)
}

export async function setCarCover(carId, imageId, isCover = true) {
  const { data } = await api.patch(`/cars/${carId}/images/${imageId}/`, {
    is_cover: isCover,
  })
  return data
}

export async function reorderCarImages(carId, imageIds) {
  const { data } = await api.post(`/cars/${carId}/images/reorder/`, {
    image_ids: imageIds,
  })
  return data
}

export async function listCarImages(carId) {
  const { data } = await api.get(`/cars/${carId}/images/`)
  return data
}
