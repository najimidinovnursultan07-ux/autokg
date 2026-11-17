export function getErrorMessage(
  error,
  fallback = 'Что-то пошло не так. Попробуйте ещё раз.',
) {
  const responseData = error?.response?.data
  const data = responseData?.error?.details || responseData
  if (!data) {
    return error?.message === 'Network Error'
      ? 'Не удалось подключиться к серверу. Проверьте, запущен ли backend.'
      : fallback
  }
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
