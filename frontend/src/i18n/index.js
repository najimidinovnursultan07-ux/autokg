// Кыргызча которуу. Сайттын тексттери орусча жазылган, ал эми бул модуль
// экрандагы бардык тексттерди (текст түйүндөрү, placeholder/title/aria-label/alt,
// alert/confirm, <title>) сөздүк боюнча кыргызчага которот. React эч нерсе билбейт:
// MutationObserver жаңы/өзгөргөн түйүндөрдү дароо (сүрөт тартылганга чейин) которот.
//
// Сөздүк: орусча сап → кыргызча. {x} — өзгөрмө бөлүк (сан, аталыш, дата);
// котормодо {x} ирети менен, же {1}, {2} — ирети өзгөргөндө.

const STORAGE_KEY = 'autobuy:lang'
const CYR = /[А-Яа-яЁё]/
const ATTRS = ['placeholder', 'title', 'aria-label', 'alt']
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'NOSCRIPT'])

export const LANGUAGES = [
  { code: 'ru', label: 'РУ', name: 'Русский' },
  { code: 'ky', label: 'КЫ', name: 'Кыргызча' },
]

const normalize = (text) => text.replace(/\s+/g, ' ').trim()

// ── Сөздүк ──
const exact = new Map()
const patterns = []
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

// Сөздүк (~145 КБ) кыргызча тандалганда гана жүктөлөт — орусча окугандар аны жүктөбөйт
let dictionaryPromise = null

function loadDictionary() {
  if (!dictionaryPromise) {
    dictionaryPromise = import('./ky/index.js').then(({ default: dictionary }) => {
      for (const [ru, ky] of Object.entries(dictionary)) {
        const key = normalize(ru)
        if (!key.includes('{x}')) {
          exact.set(key, ky)
          continue
        }
        const parts = key.split('{x}')
        const re = new RegExp(`^${parts.map(escapeRe).join('(.+?)')}$`, 's')
        patterns.push({ re, ky, fixed: key.replace(/\{x\}/g, '').length })
      }
      // Узунураак туруктуу бөлүгү барлар биринчи — так дал келгени утат
      patterns.sort((a, b) => b.fixed - a.fixed)
    }).catch((error) => {
      dictionaryPromise = null // кийинки жолу кайра аракет
      throw error
    })
  }
  return dictionaryPromise
}

// ── Айлар (Intl ru-RU форматындагы даталар) ──
const MONTHS_KY = ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
const MONTH_FORMS = [
  ['января', 'январь', 'янв'], ['февраля', 'февраль', 'февр', 'фев'], ['марта', 'март', 'мар'], ['апреля', 'апрель', 'апр'],
  ['мая', 'май'], ['июня', 'июнь', 'июн'], ['июля', 'июль', 'июл'], ['августа', 'август', 'авг'],
  ['сентября', 'сентябрь', 'сент', 'сен'], ['октября', 'октябрь', 'окт'], ['ноября', 'ноябрь', 'нояб', 'ноя'], ['декабря', 'декабрь', 'дек'],
]
const monthIndex = new Map()
MONTH_FORMS.forEach((forms, i) => forms.forEach((f) => monthIndex.set(f, i)))
const MONTH_ALT = [...monthIndex.keys()].sort((a, b) => b.length - a.length).join('|')
const RE_DAY_MONTH_YEAR = new RegExp(`(\\d{1,2})\\s(${MONTH_ALT})\\.?\\s(\\d{4})(?:\\sг\\.)?`, 'gi')
const RE_DAY_MONTH = new RegExp(`(\\d{1,2})\\s(${MONTH_ALT})\\.?(?![А-Яа-яЁё])`, 'gi')
const RE_MONTH_YEAR = new RegExp(`(^|[^А-Яа-яЁё])(${MONTH_ALT})\\.?\\s(\\d{4})(?:\\sг\\.?)?`, 'gi')
const RE_MONTH_ONLY = new RegExp(`^(${MONTH_ALT})$`, 'i')
const kyMonth = (name) => MONTHS_KY[monthIndex.get(name.toLowerCase())]
const capitalize = (s, like) => (like[0] === like[0].toUpperCase() ? s[0].toUpperCase() + s.slice(1) : s)

function translateDates(text) {
  let out = text
    .replace(RE_DAY_MONTH_YEAR, (_, d, m, y) => `${y}-ж. ${d}-${kyMonth(m)}`)
    .replace(RE_MONTH_YEAR, (_, pre, m, y) => `${pre}${y}-ж. ${capitalize(kyMonth(m), m)}`)
    .replace(RE_DAY_MONTH, (_, d, m) => `${d}-${kyMonth(m)}`)
  const only = RE_MONTH_ONLY.exec(out)
  if (only) out = capitalize(kyMonth(only[1]), only[1])
  return out
}

// ── Которуу ──
const cache = new Map()

function fill(template, values) {
  let i = 0
  return template
    .replace(/\{(\d)\}/g, (_, n) => values[Number(n) - 1] ?? '')
    .replace(/\{x\}/g, () => values[i++] ?? '')
}

function translateInner(value) {
  const t = lookup(normalize(value))
  return t ?? value
}

function lookup(text) {
  if (!text || !CYR.test(text)) return null
  if (cache.has(text)) return cache.get(text)
  let result = exact.get(text) ?? null

  if (result === null) {
    for (const { re, ky } of patterns) {
      const m = re.exec(text)
      if (m) {
        result = fill(ky, m.slice(1).map(translateInner))
        break
      }
    }
  }

  if (result === null) {
    // Сүйлөмдөр биригип калса — ар бирин өзүнчө
    const sentences = text.split(/(?<=[.!?…])\s+(?=[«"(А-ЯЁA-Z])/)
    if (sentences.length > 1) {
      const translated = sentences.map((s) => lookup(s))
      if (translated.some((s) => s !== null)) {
        result = translated.map((s, i) => s ?? sentences[i]).join(' ')
      }
    }
  }

  if (result === null) {
    const dated = translateDates(text)
    if (dated !== text) result = dated
  }

  cache.set(text, result)
  return result
}

// Аралыктарды (башы/аягы) сактап которот
function translatePreserving(text) {
  const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(text)
  const t = lookup(normalize(m[2]))
  return t === null ? text : m[1] + t + m[3]
}

export function translateText(text) {
  if (lang !== 'ky' || typeof text !== 'string') return text
  // Көп саптуу (confirm) — саптарды сактап, ар бирин өзүнчө
  if (text.includes('\n')) {
    const lines = text.split('\n').map(translatePreserving).join('\n')
    if (lines !== text) return lines
  }
  return translatePreserving(text)
}

// ── DOM ──
const textRecords = new WeakMap() // Text → { orig, applied }
const attrRecords = new WeakMap() // Element → { [attr]: { orig, applied } }
let observer = null
let lang = readLang()

function readLang() {
  try {
    // ?lang=ky / ?lang=ru — шилтеме аркылуу тилди тандоо (эстеп калат)
    const fromUrl = new URLSearchParams(window.location?.search || '').get('lang')
    if (fromUrl === 'ky' || fromUrl === 'ru') {
      localStorage.setItem(STORAGE_KEY, fromUrl)
      return fromUrl
    }
    return localStorage.getItem(STORAGE_KEY) === 'ky' ? 'ky' : 'ru'
  } catch {
    return 'ru'
  }
}

function skipped(element) {
  if (!element || element.nodeType !== 1) return true
  if (SKIP_TAGS.has(element.tagName)) return true
  return Boolean(element.closest('[data-i18n-skip], [contenteditable="true"]'))
}

const originalOf = (node) => {
  const rec = textRecords.get(node)
  return rec && node.data === rec.applied ? rec.orig : node.data
}

function applyText(node, orig, value) {
  if (value === orig) {
    if (textRecords.has(node)) {
      textRecords.delete(node)
      if (node.data !== orig) node.data = orig
    }
    return
  }
  textRecords.set(node, { orig, applied: value })
  if (node.data !== value) node.data = value
}

// Элементте бир нече текст түйүнү гана болсо (мисалы, «Удалить «{name}»?»),
// аларды бириктирип котору — кыргызчада сөз ирети башка.
function translateElementTexts(element) {
  const nodes = [...element.childNodes]
  const origs = nodes.map(originalOf)
  const joined = origs.join('')
  const whole = translatePreserving(joined)
  if (whole !== joined) {
    nodes.forEach((node, i) => applyText(node, origs[i], i === 0 ? whole : ''))
    return
  }
  nodes.forEach((node, i) => applyText(node, origs[i], translatePreserving(origs[i])))
}

function translateTextNode(node) {
  const parent = node.parentNode
  if (skipped(parent)) return
  const siblings = parent.childNodes
  if (siblings.length > 1 && [...siblings].every((n) => n.nodeType === 3)) {
    translateElementTexts(parent)
    return
  }
  const orig = originalOf(node)
  applyText(node, orig, translatePreserving(orig))
}

function translateAttr(element, attr) {
  if (!element.hasAttribute(attr) || element.closest('[data-i18n-skip]')) return
  const records = attrRecords.get(element) || {}
  const current = element.getAttribute(attr)
  const rec = records[attr]
  const orig = rec && current === rec.applied ? rec.orig : current
  const value = translatePreserving(orig)
  if (value === orig) {
    if (rec) {
      delete records[attr]
      if (current !== orig) element.setAttribute(attr, orig)
    }
    return
  }
  records[attr] = { orig, applied: value }
  attrRecords.set(element, records)
  if (current !== value) element.setAttribute(attr, value)
}

const ATTR_SELECTOR = ATTRS.map((a) => `[${a}]`).join(',')

function translateTree(root) {
  if (root.nodeType === 3) {
    translateTextNode(root)
    return
  }
  if (root.nodeType !== 1) return
  ATTRS.forEach((a) => translateAttr(root, a))
  root.querySelectorAll(ATTR_SELECTOR).forEach((el) => ATTRS.forEach((a) => translateAttr(el, a)))
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const done = new Set()
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const parent = node.parentNode
    if (done.has(parent)) continue
    if (parent.childNodes.length > 1 && [...parent.childNodes].every((n) => n.nodeType === 3)) done.add(parent)
    translateTextNode(node)
  }
}

function restoreTree(root) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const rec = textRecords.get(node)
    if (!rec) continue
    if (node.data === rec.applied) node.data = rec.orig
    textRecords.delete(node)
  }
  root.querySelectorAll(ATTR_SELECTOR).forEach((el) => {
    const records = attrRecords.get(el)
    if (!records) return
    for (const [attr, rec] of Object.entries(records)) {
      if (el.getAttribute(attr) === rec.applied) el.setAttribute(attr, rec.orig)
    }
    attrRecords.delete(el)
  })
}

function handleMutations(mutations) {
  for (const m of mutations) {
    if (m.type === 'childList') m.addedNodes.forEach(translateTree)
    else if (m.type === 'characterData') translateTextNode(m.target)
    else if (m.type === 'attributes') translateAttr(m.target, m.attributeName)
  }
  // Өзүбүз жасаган өзгөртүүлөр кайра иштетилбесин
  observer?.takeRecords()
}

function start() {
  if (lang !== 'ky') return
  const root = document.documentElement
  translateTree(root)
  if (!observer) observer = new MutationObserver(handleMutations)
  observer.observe(root, {
    subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS,
  })
}

function stop() {
  observer?.disconnect()
  restoreTree(document.documentElement)
}

// alert / confirm / prompt — алардын тексти да которулат
for (const name of ['alert', 'confirm', 'prompt']) {
  const native = window[name]?.bind(window)
  if (!native) continue
  window[name] = (message, ...rest) => native(translateText(message), ...rest)
}

// ── Тил ──
const listeners = new Set()

export const getLanguage = () => lang

export function subscribeLanguage(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function setLanguage(next) {
  const value = next === 'ky' ? 'ky' : 'ru'
  if (value === lang) return
  lang = value
  try {
    localStorage.setItem(STORAGE_KEY, value)
  } catch { /* жеке терезе — эстеп калбайт */ }
  document.documentElement.lang = value
  if (value === 'ky') loadDictionary().then(start).catch(() => {})
  else stop()
  listeners.forEach((l) => l(value))
}

// Кыргызча тандалса — сөздүк жүктөлүп, которгуч иштегенден кийин гана Promise бүтөт
export function initLanguage() {
  document.documentElement.lang = lang
  if (lang !== 'ky') return Promise.resolve()
  return loadDictionary().then(start).catch(() => {})
}
