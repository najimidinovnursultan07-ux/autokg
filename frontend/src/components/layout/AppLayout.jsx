import { Suspense } from 'react'
import { Outlet } from 'react-router-dom'
import PullToRefresh from '../common/PullToRefresh.jsx'
import { LoadingState } from '../common/States.jsx'
import AssistantChat from './AssistantChat.jsx'
import Footer from './Footer.jsx'
import Header from './Header.jsx'

export default function AppLayout() {
  return (
    <div className="app-shell">
      <PullToRefresh />
      <Header />
      <main className="site-main">
        <Suspense fallback={<LoadingState label="Загружаем страницу…" />}>
          <Outlet />
        </Suspense>
      </main>
      <Footer />
      <AssistantChat />
    </div>
  )
}
