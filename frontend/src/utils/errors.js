export function getErrorMessage(
  error,
  fallback = 'Что-то пошло не так. Попробуйте ещё раз.',
) {
  // Network / connection error
  if (!error?.response) {
    return error?.message === 'Network Error'
      ? 'Не удалось подключиться к серверу. Проверьте соединение.'
      : fallback
  }

  const status = error.response.status
  const responseData = error.response.data

  // Server returned HTML (e.g. 500 page, nginx error) instead of JSON
  if (typeof responseData === 'string') {
    if (status === 403) return 'Доступ запрещён. Возможно, истёк CSRF-токен — обновите страницу.'
    if (status === 401) return 'Неверный email или пароль.'
    if (status === 500) return 'Ошибка сервера. Попробуйте позже.'
    return fallback
  }

  const data = responseData?.error?.details || responseData
  if (!data) return fallback

  if (typeof data.detail === 'string') return data.detail

  const messages = Object.values(data)
    .flatMap((value) => (Array.isArray(value) ? value : [value]))
    .filter((value) => typeof value === 'string')
  return messages[0] || fallback
}

export function getFieldErrors(error) {
  const responseData = error?.response?.data
  const data = responseData?.error?.details || responseData
  if (!data || typeof data !== 'object') return {}
  return Object.fromEntries(
    Object.entries(data).filter(
      ([key, value]) => key !== 'detail' && Array.isArray(value),
    ),
  )
}
