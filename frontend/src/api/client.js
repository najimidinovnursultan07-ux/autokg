import axios from 'axios'

const browserOrigin = typeof window === 'undefined' ? 'http://localhost' : window.location.origin
const browserHostname = typeof window === 'undefined' ? 'localhost' : window.location.hostname
const configuredApiBaseUrl = import.meta.env?.VITE_API_BASE_URL?.trim()

export const API_BASE_URL =
  configuredApiBaseUrl || `http://${browserHostname}:8000/api`
export const API_ORIGIN = new URL(API_BASE_URL, browserOrigin).origin

let accessToken = null
let refreshPromise = null
const inFlightGetRequests = new Map()

export function setAccessToken(token) {
  accessToken = token || null
}

function getCookie(name) {
  const cookie = document.cookie
    .split('; ')
    .find((item) => item.startsWith(`${name}=`))
  return cookie ? decodeURIComponent(cookie.slice(name.length + 1)) : null
}

export async function ensureCsrfCookie() {
  await api.get('/auth/csrf/')
}

export function resolveMediaUrl(path) {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  return new URL(path, API_ORIGIN).toString()
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: { Accept: 'application/json' },
})

const axiosGet = api.get.bind(api)
api.get = (url, config = {}) => {
  if (config.signal || config.cancelToken) return axiosGet(url, config)

  const requestUrl = api.getUri({ ...config, url })
  const authorization = config.headers?.get?.('Authorization')
    || config.headers?.Authorization
    || accessToken
    || ''
  const key = JSON.stringify({
    requestUrl,
    authorization,
    responseType: config.responseType || 'json',
    withCredentials: config.withCredentials ?? api.defaults.withCredentials,
  })
  const pendingRequest = inFlightGetRequests.get(key)
  if (pendingRequest) return pendingRequest

  const request = axiosGet(url, config).finally(() => {
    if (inFlightGetRequests.get(key) === request) {
      inFlightGetRequests.delete(key)
    }
  })
  inFlightGetRequests.set(key, request)
  return request
}

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  const method = (config.method || 'get').toLowerCase()
  if (!['get', 'head', 'options'].includes(method)) {
    const csrfToken = getCookie('csrftoken')
    if (csrfToken) config.headers['X-CSRFToken'] = csrfToken
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config
    const url = request?.url || ''
    const isAuthRequest = /\/auth\/(login|register|refresh|csrf|logout)\//.test(url)

    if (error.response?.status !== 401 || !request || request._retry || isAuthRequest) {
      return Promise.reject(error)
    }

    request._retry = true
    try {
      if (!refreshPromise) {
        refreshPromise = ensureCsrfCookie()
          .then(() => api.post('/auth/refresh/'))
          .then(({ data }) => {
            setAccessToken(data.access)
            return data.access
          })
          .finally(() => {
            refreshPromise = null
          })
      }
      const token = await refreshPromise
      request.headers.Authorization = `Bearer ${token}`
      return api(request)
    } catch (refreshError) {
      setAccessToken(null)
      window.dispatchEvent(new CustomEvent('autokg:session-expired'))
      return Promise.reject(refreshError)
    }
  },
)
