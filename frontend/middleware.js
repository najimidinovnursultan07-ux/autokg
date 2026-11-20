/**
 * Vercel Routing Middleware: превью ссылок на объявления в WhatsApp, Telegram и т.п.
 *
 * Боты мессенджеров не выполняют JavaScript, поэтому для них на /cars/<id>
 * отдаётся небольшой HTML с Open Graph тегами (фото, название, цена).
 * Обычные посетители получают SPA как раньше — middleware их не трогает.
 */
export const config = {
  matcher: '/cars/:id*',
}

const SITE_URL = 'https://autobuy-kg.vercel.app'
const DEFAULT_IMAGE = `${SITE_URL}/og-image.jpg`
const API_BASE_URL = (process.env.VITE_API_BASE_URL || 'https://autokg.onrender.com/api').replace(/\/$/, '')
const BOT_UA = /whatsapp|telegrambot|facebookexternalhit|facebot|twitterbot|linkedinbot|slackbot|discordbot|vkshare|viber|skypeuripreview|pinterest|redditbot|applebot|odnoklassniki/i
const CAR_ID = /^\/cars\/([0-9a-f-]{36})\/?$/i

const LABELS = {
  transmission: { manual: 'Механика', automatic: 'Автомат', cvt: 'Вариатор', robotic: 'Робот' },
  engine_type: { petrol: 'Бензин', diesel: 'Дизель', hybrid: 'Гибрид', electric: 'Электро', lpg: 'Газ' },
}

export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;')
}

function formatNumber(value) {
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(value).replace(/\s/g, ' ')
}

function formatPrice(value, currency) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return ''
  return currency === 'USD' ? `$${formatNumber(amount)}` : `${formatNumber(amount)} сом`
}

function absoluteUrl(url) {
  if (!url) return ''
  if (/^https?:\/\//i.test(url)) return url
  return new URL(url, new URL(API_BASE_URL).origin).toString()
}

async function fetchCar(id) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 7000)
  try {
    const response = await fetch(`${API_BASE_URL}/cars/${id}/`, {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    })
    return response.ok ? await response.json() : null
  } finally {
    clearTimeout(timer)
  }
}

export function renderPreview(car, url) {
  const title = [car.brand, car.model_name, car.year].filter(Boolean).join(' ')
  const price = formatPrice(car.price, car.currency)
  const details = [
    car.mileage != null ? `${formatNumber(Number(car.mileage) || 0)} км` : '',
    LABELS.transmission[car.transmission],
    LABELS.engine_type[car.engine_type],
    car.city_name,
    car.dealer_detail?.name,
  ].filter(Boolean).join(' · ')
  const cover = car.images?.find((image) => image.is_cover) || car.images?.[0]
  const image = absoluteUrl(cover?.url || cover?.image) || DEFAULT_IMAGE
  const fullTitle = price ? `${title} — ${price}` : title
  const description = `${details}. Смотрите фото и контакты автосалона на AutoBuy.`

  return `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8" />
<title>${escapeHtml(fullTitle)} | AutoBuy</title>
<meta name="description" content="${escapeHtml(description)}" />
<link rel="canonical" href="${escapeHtml(url)}" />
<meta property="og:type" content="product" />
<meta property="og:site_name" content="AutoBuy" />
<meta property="og:locale" content="ru_RU" />
<meta property="og:title" content="${escapeHtml(fullTitle)}" />
<meta property="og:description" content="${escapeHtml(description)}" />
<meta property="og:url" content="${escapeHtml(url)}" />
<meta property="og:image" content="${escapeHtml(image)}" />
<meta property="og:image:alt" content="${escapeHtml(title)}" />
<meta property="product:price:amount" content="${escapeHtml(car.price)}" />
<meta property="product:price:currency" content="${escapeHtml(car.currency)}" />
<meta name="twitter:card" content="summary_large_image" />
</head>
<body>
<h1>${escapeHtml(fullTitle)}</h1>
<p>${escapeHtml(description)}</p>
<p><a href="${escapeHtml(url)}">Открыть объявление на AutoBuy</a></p>
</body>
</html>`
}

export default async function middleware(request) {
  if (!BOT_UA.test(request.headers.get('user-agent') || '')) return undefined
  const match = new URL(request.url).pathname.match(CAR_ID)
  if (!match) return undefined

  try {
    const car = await fetchCar(match[1])
    if (!car) return undefined
    return new Response(renderPreview(car, `${SITE_URL}/cars/${match[1]}`), {
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'public, max-age=300, s-maxage=600',
      },
    })
  } catch {
    // API недоступен (например, Render просыпается) — бот получит обычную страницу с общим превью
    return undefined
  }
}
