import { useSyncExternalStore } from 'react'
import { LANGUAGES, getLanguage, setLanguage, subscribeLanguage } from '../../i18n/index.js'

// data-i18n-skip — «РУ / КЫ» өзү которулбасын
export default function LanguageSwitcher({ className = '' }) {
  const lang = useSyncExternalStore(subscribeLanguage, getLanguage)
  return (
    <div className={`lang-switcher ${className}`} role="group" aria-label="Язык / Тил" data-i18n-skip>
      {LANGUAGES.map(({ code, label, name }) => (
        <button
          key={code}
          type="button"
          lang={code}
          title={name}
          aria-pressed={lang === code}
          className={`lang-switcher-option ${lang === code ? 'lang-switcher-option--active' : ''}`}
          onClick={() => setLanguage(code)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
