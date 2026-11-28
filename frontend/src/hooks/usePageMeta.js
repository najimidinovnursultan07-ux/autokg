import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

const SITE_URL = 'https://autobuy-kg.vercel.app'
const DEFAULT_TITLE = 'AutoBuy — автомобили Кыргызстана'
const DEFAULT_DESCRIPTION = 'AutoBuy — покупка и продажа автомобилей в Кыргызстане.'

function setTag(selector, create, attr, value) {
  let tag = document.head.querySelector(selector)
  if (!tag) {
    tag = create()
    document.head.appendChild(tag)
  }
  tag.setAttribute(attr, value)
}

/**
 * Заголовок вкладки, description и canonical для поисковиков.
 * Google выполняет JS и берёт их из отрисованной страницы.
 * Пустой title (данные ещё грузятся) — оставляем общий заголовок сайта.
 */
export function usePageMeta(title, description) {
  const { pathname } = useLocation()

  useEffect(() => {
    const fullTitle = title ? `${title} | AutoBuy` : DEFAULT_TITLE
    const text = description || DEFAULT_DESCRIPTION
    document.title = fullTitle
    setTag('meta[name="description"]', () => Object.assign(document.createElement('meta'), { name: 'description' }), 'content', text)
    setTag('meta[property="og:title"]', () => {
      const meta = document.createElement('meta')
      meta.setAttribute('property', 'og:title')
      return meta
    }, 'content', fullTitle)
    setTag('link[rel="canonical"]', () => Object.assign(document.createElement('link'), { rel: 'canonical' }), 'href', `${SITE_URL}${pathname}`)
  }, [title, description, pathname])

  useEffect(() => () => {
    document.title = DEFAULT_TITLE
  }, [])
}
