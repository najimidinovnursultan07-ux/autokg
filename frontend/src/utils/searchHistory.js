const KEY = 'autobuy_search_history'
const MAX = 8

export function getSearchHistory() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}

export function addSearchHistory(query) {
  if (!query?.trim()) return
  const history = getSearchHistory().filter((item) => item !== query.trim())
  history.unshift(query.trim())
  localStorage.setItem(KEY, JSON.stringify(history.slice(0, MAX)))
}

export function removeSearchHistory(query) {
  const history = getSearchHistory().filter((item) => item !== query)
  localStorage.setItem(KEY, JSON.stringify(history))
}

export function clearSearchHistory() {
  localStorage.removeItem(KEY)
}
