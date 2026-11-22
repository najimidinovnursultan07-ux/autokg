import { Component } from 'react'
import { Link } from 'react-router-dom'
import { isChunkLoadError, reloadForFreshVersion } from '../../utils/chunkReload.js'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, chunkError: false }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, chunkError: isChunkLoadError(error) }
  }

  componentDidCatch(error) {
    // Файл страницы не загрузился (новый деплой) — тихо перезагружаемся вместо экрана ошибки.
    // Если уже перезагружались только что — показываем обычный экран ошибки.
    if (isChunkLoadError(error) && !reloadForFreshVersion()) this.setState({ chunkError: false })
  }

  render() {
    if (this.state.hasError && this.state.chunkError) return null
    if (this.state.hasError) {
      return (
        <div className="fatal-error">
          <div className="container">
            <span className="eyebrow">Непредвиденная ошибка</span>
            <h1>Страница временно недоступна</h1>
            <p>Обновите страницу или вернитесь на главную.</p>
            <Link className="button button--primary" to="/">На главную</Link>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
