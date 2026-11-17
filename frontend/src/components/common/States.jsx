import { AlertCircle, LoaderCircle } from 'lucide-react'

export function LoadingState({ label = 'Загружаем данные…', compact = false }) {
  return (
    <div className={`state-panel ${compact ? 'state-panel--compact' : ''}`} role="status">
      <LoaderCircle className="spin" size={25} />
      <span>{label}</span>
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="state-panel state-panel--error" role="alert">
      <AlertCircle size={24} />
      <span>{message}</span>
      {onRetry && <button className="button button--outline" onClick={onRetry}>Повторить</button>}
    </div>
  )
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">—</div>
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  )
}

export function PageTitle({ eyebrow, title, description, action }) {
  return (
    <div className="page-title-row">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  )
}
