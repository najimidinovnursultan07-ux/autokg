// После нового деплоя старые файлы страниц удаляются. Если вкладка была открыта до деплоя
// и пытается загрузить такую страницу — один раз тихо перезагружаемся, чтобы получить свежую версию.
const KEY = 'autobuy:chunk-reload'

const CHUNK_ERROR = /dynamically imported module|Importing a module script failed|error loading dynamically|is not a valid JavaScript MIME type|ChunkLoadError|Unable to preload/i

export function isChunkLoadError(error) {
  return CHUNK_ERROR.test(String(error?.message || error || ''))
}

/** Перезагружает страницу, если не делали этого последние 10 секунд. Возвращает true, если перезагрузка началась. */
export function reloadForFreshVersion() {
  let reloadedRecently = false
  try {
    reloadedRecently = Date.now() - Number(sessionStorage.getItem(KEY) || 0) < 10000
    sessionStorage.setItem(KEY, String(Date.now()))
  } catch { /* sessionStorage недоступен — просто перезагружаемся */ }
  if (reloadedRecently) return false
  window.location.reload()
  return true
}
