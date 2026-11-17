import { api } from './client.js'

export async function listFavorites() {
  const allFavorites = []
  let page = 1
  while (true) {
    const { data } = await api.get('/favorites/', {
      params: { page, page_size: 100 },
    })
    if (Array.isArray(data)) return data
    allFavorites.push(...data.results)
    if (!data.next) return allFavorites
    page += 1
  }
}

export async function addFavorite(carId) {
  const { data } = await api.post('/favorites/', { car: carId })
  return data
}

export async function removeFavorite(favoriteId) {
  await api.delete(`/favorites/${favoriteId}/`)
}
