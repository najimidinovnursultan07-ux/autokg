const KEY = 'autokg_compare'
const MAX = 3

export function getCompareList() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}

export function addToCompare(car) {
  const list = getCompareList()
  if (list.find((c) => c.id === car.id)) return { added: false, reason: 'already' }
  if (list.length >= MAX) return { added: false, reason: 'full' }
  list.push({ id: car.id, title: car.brand + ' ' + car.model_name + ' ' + car.year, price: car.price, image: car.images?.[0]?.image || '' })
  localStorage.setItem(KEY, JSON.stringify(list))
  window.dispatchEvent(new Event('autokg:compare-updated'))
  return { added: true }
}

export function removeFromCompare(id) {
  const list = getCompareList().filter((c) => c.id !== id)
  localStorage.setItem(KEY, JSON.stringify(list))
  window.dispatchEvent(new Event('autokg:compare-updated'))
}

export function clearCompare() {
  localStorage.removeItem(KEY)
  window.dispatchEvent(new Event('autokg:compare-updated'))
}

export function isInCompare(id) {
  return getCompareList().some((c) => c.id === id)
}
