import { api } from './client.js'

// Скачивает файл с API (с авторизацией) и сохраняет под именем из Content-Disposition
export async function downloadFile(path, fallbackName) {
  const response = await api.get(path, { responseType: 'blob' })
  const disposition = response.headers['content-disposition'] || ''
  const filename = /filename="([^"]+)"/.exec(disposition)?.[1] || fallbackName
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
