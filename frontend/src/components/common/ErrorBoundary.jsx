import { Component } from 'react'
import { Link } from 'react-router-dom'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
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
