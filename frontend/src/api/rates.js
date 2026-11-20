import { api } from './client.js'

// Курс НБКР запрашивается один раз за сессию страницы
let ratesPromise = null

export function getRates() {
  if (!ratesPromise) {
    ratesPromise = api.get('/rates/')
      .then(({ data }) => data)
      .catch(() => {
        ratesPromise = null
        return null
      })
  }
  return ratesPromise
}
