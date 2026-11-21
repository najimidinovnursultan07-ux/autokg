import { api } from './client.js'

// Скачивает файл с API (с авторизацией) и сохраняет под именем из Content-Disposition
export async function downloadFile(path, fallbackName) {
  let response
  try {
    response = await api.get(path, { responseType: 'blob' })
  } catch (error) {
    // При responseType: 'blob' текст ошибки сервера тоже приходит Blob — превращаем в JSON
    const data = error?.response?.data
    if (data instanceof Blob) {
      try { error.response.data = JSON.parse(await data.text()) } catch { /* не JSON */ }
    }
    throw error
  }
  const disposition = response.headers['content-disposition'] || ''
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] || fallbackName
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
