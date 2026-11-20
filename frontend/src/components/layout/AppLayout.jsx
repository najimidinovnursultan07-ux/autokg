import { Outlet } from 'react-router-dom'
import FloatingWhatsApp from './FloatingWhatsApp.jsx'
import Footer from './Footer.jsx'
import Header from './Header.jsx'

export default function AppLayout() {
  return (
    <div className="app-shell">
      <Header />
      <main className="site-main">
        <Outlet />
      </main>
      <Footer />
      <FloatingWhatsApp />
    </div>
  )
}
