import { useEffect, useState, useSyncExternalStore } from 'react'
import { Download, Share, SquarePlus, X } from 'lucide-react'
import { canPromptInstall, isIos, isStandalone, promptInstall, subscribeInstall } from '../../utils/pwaInstall.js'

export default function InstallAppButton() {
  const canPrompt = useSyncExternalStore(subscribeInstall, canPromptInstall, () => false)
  const [installed, setInstalled] = useState(isStandalone)
  const [help, setHelp] = useState(false)

  useEffect(() => {
    const onInstalled = () => setInstalled(true)
    window.addEventListener('appinstalled', onInstalled)
    return () => window.removeEventListener('appinstalled', onInstalled)
  }, [])

  useEffect(() => {
    if (!help) return undefined
    const onKey = (event) => event.key === 'Escape' && setHelp(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [help])

  if (installed) return null

  const install = async () => {
    if (canPrompt) {
      const accepted = await promptInstall()
      if (accepted) setInstalled(true)
      return
    }
    setHelp(true)
  }

  return (
    <>
      <button type="button" className="footer-install" onClick={install}>
        <Download size={16} /> Скачать приложение
      </button>
      {help && (
        <div className="install-help-backdrop" role="presentation" onClick={() => setHelp(false)}>
          <div className="install-help" role="dialog" aria-modal="true" aria-labelledby="install-help-title" onClick={(event) => event.stopPropagation()}>
            <button type="button" className="install-help-close" onClick={() => setHelp(false)} aria-label="Закрыть"><X size={18} /></button>
            <h2 id="install-help-title">Установить AutoBuy</h2>
            <p>Приложение откроется с иконки на экране, как обычное — без браузера и без App Store.</p>
            {isIos() ? (
              <ol>
                <li>Откройте сайт в <strong>Safari</strong>.</li>
                <li>Нажмите <Share size={15} aria-label="Поделиться" /> <strong>«Поделиться»</strong> внизу экрана.</li>
                <li>Выберите <SquarePlus size={15} aria-hidden="true" /> <strong>«На экран Домой»</strong> и нажмите «Добавить».</li>
              </ol>
            ) : (
              <ol>
                <li>Откройте меню браузера <strong>⋮</strong> (справа сверху).</li>
                <li>Выберите <strong>«Установить приложение»</strong> или <strong>«Добавить на главный экран»</strong>.</li>
                <li>Подтвердите установку — иконка AutoBuy появится на экране.</li>
              </ol>
            )}
          </div>
        </div>
      )}
    </>
  )
}
