import { api, ensureCsrfCookie } from './client.js'

export async function login(credentials) {
  await ensureCsrfCookie()
  const { data } = await api.post('/auth/login/', credentials)
  return data
}

export async function register(details) {
  await ensureCsrfCookie()
  const { data } = await api.post('/auth/register/', details)
  return data
}

export async function logout() {
  await api.post('/auth/logout/')
}

export async function getCurrentUser() {
  const { data } = await api.get('/auth/me/')
  return data
}

export async function updateProfile(details) {
  const { data } = await api.patch('/auth/profile/', details)
  return data
}

export async function changePassword(details) {
  const { data } = await api.post('/auth/password-change/', details)
  return data
}

export async function requestPasswordReset(email) {
  await ensureCsrfCookie()
  const { data } = await api.post('/auth/password-reset/', { email })
  return data
}

export async function confirmPasswordReset(payload) {
  await ensureCsrfCookie()
  const { data } = await api.post('/auth/password-reset/confirm/', payload)
  return data
}
