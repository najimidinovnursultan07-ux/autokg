import { useEffect } from 'react'
import { useLocation, useNavigationType } from 'react-router-dom'

// При переходе на другую страницу (меню, ссылки, админка) — открываем её с самого верха.
// Кнопки браузера «Назад/Вперёд» (POP) не трогаем: там браузер сам вернёт прежнюю прокрутку.
export default function ScrollToTop() {
  const { pathname } = useLocation()
  const navigationType = useNavigationType()

  useEffect(() => {
    if (navigationType !== 'POP') window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [pathname, navigationType])

  return null
}
