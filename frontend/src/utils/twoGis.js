// Бесплатный JS API карт 2ГИС 2.0 (без ключа): https://api.2gis.ru/doc/maps/ru/manual/
const LOADER_URL = 'https://maps.api.2gis.ru/2.0/loader.js?pkg=full'

// Ключ Raster JS API (platform.2gis.ru). Без него 2ГИС не отдаёт тайлы — карта пустая.
export const TWOGIS_KEY = import.meta.env.VITE_TWOGIS_KEY || ''

// Центр Бишкека — точка по умолчанию для карты и выбора места
export const DEFAULT_CENTER = [42.8746, 74.5698]

let loadPromise = null

const LOAD_TIMEOUT = 20000

function withTimeout(promise) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Карта 2ГИС не ответила')), LOAD_TIMEOUT)
    promise.then(
      (value) => { clearTimeout(timer); resolve(value) },
      (error) => { clearTimeout(timer); reject(error) },
    )
  })
}

// ВАЖНО: у объекта DG есть свой метод then, поэтому промис нельзя резолвить самим DG —
// Promise примет его за thenable и вернёт undefined. Резолвим без значения и берём window.DG.
function waitReady(resolve, reject) {
  window.DG.then(() => resolve(), () => reject(new Error('Не удалось загрузить карту 2ГИС')))
}

/** Загружает API 2ГИС. Промис резолвится без значения — используйте window.DG. */
export function loadTwoGis() {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'))
  if (window.DG?.ready && window.DG.map) return Promise.resolve()
  if (window.DG?.then) return withTimeout(new Promise(waitReady))
  if (!loadPromise) {
    loadPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = LOADER_URL
      script.async = true
      script.onload = () => waitReady(resolve, reject)
      script.onerror = () => {
        loadPromise = null
        script.remove()
        reject(new Error('Не удалось загрузить карту 2ГИС'))
      }
      document.head.appendChild(script)
    })
  }
  return withTimeout(loadPromise)
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
 * «42.8746, 74.5698», ссылка 2ГИС с ?m=74.5698,42.8746/16, /geo/74.5698,42.8746 или /geo/<id>/74.5698%2C42.8746,
 * ссылка Google Maps с @42.8746,74.5698.
 */
export function parseLocation(text) {
  let value = String(text || '').trim()
  if (!value) return null
  try { value = decodeURIComponent(value) } catch { /* оставляем как есть */ }
  const valid = (lat, lng) => (Math.abs(lat) <= 90 && Math.abs(lng) <= 180 ? [lat, lng] : null)
  const NUM = '(-?\\d+(?:\\.\\d+)?)'

  // 2ГИС: долгота, широта — ?m=74.56,42.87/16, /geo/74.56,42.87, /geo/<id>/74.56,42.87, /firm/<id>/74.56,42.87
  let match = value.match(new RegExp(`[?&]m=${NUM},${NUM}`))
  if (match) return valid(Number(match[2]), Number(match[1]))
  if (/2gis\./i.test(value)) {
    match = value.match(new RegExp(`/${NUM},${NUM}(?:[/?#]|$)`))
    if (match) return valid(Number(match[2]), Number(match[1]))
  }
  match = value.match(/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/)
  if (match) return valid(Number(match[1]), Number(match[2])) // Google: широта, долгота
  match = value.match(/^(-?\d+(?:\.\d+)?)\s*[,;\s]\s*(-?\d+(?:\.\d+)?)$/)
  if (match) return valid(Number(match[1]), Number(match[2]))
  return null
}
