import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { CheckCircle2, CircleAlert, Info, X } from 'lucide-react'

const ToastContext = createContext(null)
const icons = { success: CheckCircle2, error: CircleAlert, info: Info }

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])

  const dismiss = useCallback((id) => {
    setItems((current) => current.filter((item) => item.id !== id))
  }, [])

  const notify = useCallback(
    (message, type = 'info') => {
      const id = crypto.randomUUID()
      setItems((current) => [...current, { id, message, type }])
      window.setTimeout(() => dismiss(id), 4500)
    },
    [dismiss],
  )

  const value = useMemo(() => ({ notify }), [notify])
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {items.map((item) => {
          const Icon = icons[item.type] || Info
          return (
            <div className={`toast toast--${item.type}`} key={item.id}>
              <Icon size={19} />
              <span>{item.message}</span>
              <button
                type="button"
                aria-label="Закрыть уведомление"
                onClick={() => dismiss(item.id)}
              >
                <X size={16} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}
