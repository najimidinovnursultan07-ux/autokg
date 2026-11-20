// Бесплатный JS API карт 2ГИС 2.0 (без ключа): https://api.2gis.ru/doc/maps/ru/manual/
const LOADER_URL = 'https://maps.api.2gis.ru/2.0/loader.js?pkg=full'

// Центр Бишкека — точка по умолчанию для карты и выбора места
export const DEFAULT_CENTER = [42.8746, 74.5698]

let loadPromise = null

export function loadTwoGis() {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'))
  if (window.DG?.then) return new Promise((resolve) => window.DG.then(() => resolve(window.DG)))
  if (!loadPromise) {
    loadPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = LOADER_URL
      script.async = true
      script.onload = () => window.DG.then(() => resolve(window.DG))
      script.onerror = () => {
        loadPromise = null
        script.remove()
        reject(new Error('Не удалось загрузить карту 2ГИС'))
      }
      document.head.appendChild(script)
    })
  }
  return loadPromise
}

export function hasLocation(item) {
  return item?.latitude != null && item?.longitude != null && item.latitude !== '' && item.longitude !== ''
}

export function toLatLng(item) {
  return [Number(item.latitude), Number(item.longitude)]
}

// Ссылки в приложение / на сайт 2ГИС (на телефоне откроется приложение, если установлено)
export function twoGisPointUrl(lat, lng) {
  return `https://2gis.kg/geo/${lng},${lat}?m=${lng},${lat}/17`
}

export function twoGisRouteUrl(lat, lng) {
  return `https://2gis.kg/directions/points/%7C${lng}%2C${lat}`
}

/**
 * Достаёт координаты из вставленного текста:
 * «42.8746, 74.5698», ссылка 2ГИС с ?m=74.5698,42.8746/16 или /geo/74.5698,42.8746,
 * ссылка Google Maps с @42.8746,74.5698.
 */
export function parseLocation(text) {
  const value = String(text || '').trim()
  if (!value) return null
  const valid = (lat, lng) => (Math.abs(lat) <= 90 && Math.abs(lng) <= 180 ? [lat, lng] : null)

  let match = value.match(/[?&]m=(-?\d+(?:\.\d+)?)(?:,|%2C)(-?\d+(?:\.\d+)?)/i)
  if (match) return valid(Number(match[2]), Number(match[1])) // 2ГИС: долгота, широта
  match = value.match(/\/geo\/(-?\d+(?:\.\d+)?)(?:,|%2C)(-?\d+(?:\.\d+)?)/i)
  if (match) return valid(Number(match[2]), Number(match[1]))
  match = value.match(/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/)
  if (match) return valid(Number(match[1]), Number(match[2])) // Google: широта, долгота
  match = value.match(/^(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)$/)
  if (match) return valid(Number(match[1]), Number(match[2]))
  return null
}
