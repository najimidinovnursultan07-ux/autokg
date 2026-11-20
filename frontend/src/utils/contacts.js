// Контакты площадки AutoBuy (страница «Контакты» и плавающая кнопка WhatsApp)
export const SUPPORT_PHONE = '+996 708 887 776'
export const SUPPORT_PHONE_DIGITS = SUPPORT_PHONE.replace(/\D/g, '')

export function whatsappLink(phone, message = '') {
  const digits = String(phone || '').replace(/\D/g, '')
  if (!digits) return ''
  return `https://wa.me/${digits}${message ? `?text=${encodeURIComponent(message)}` : ''}`
}
