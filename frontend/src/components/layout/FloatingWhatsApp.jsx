import { MessageCircle } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { SUPPORT_PHONE, whatsappLink } from '../../utils/contacts.js'

// На странице машины у покупателя своя кнопка WhatsApp салона — там прячем,
// чтобы вопросы по машине уходили продавцу, а не в поддержку.
const HIDDEN_PREFIXES = ['/cars/', '/dashboard', '/admin', '/payment', '/login', '/password-reset']

export default function FloatingWhatsApp() {
  const { pathname } = useLocation()
  if (HIDDEN_PREFIXES.some((prefix) => pathname.startsWith(prefix))) return null

  return (
    <a
      className="floating-whatsapp"
      href={whatsappLink(SUPPORT_PHONE, 'Здравствуйте! У меня вопрос по AutoBuy.')}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Написать в WhatsApp"
      title="Написать в WhatsApp"
    >
      <MessageCircle size={26} />
      <span>Написать нам</span>
    </a>
  )
}
