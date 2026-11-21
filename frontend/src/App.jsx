import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout.jsx'
import AccountLayout from './components/layout/AccountLayout.jsx'
import AdminLayout from './components/layout/AdminLayout.jsx'
import ProtectedRoute from './components/routing/ProtectedRoute.jsx'
import GuestRoute from './components/routing/GuestRoute.jsx'
import AboutPage from './pages/AboutPage.jsx'
import ComparePage from './pages/ComparePage.jsx'
import MySubscriptionPage from './pages/MySubscriptionPage.jsx'
import PricingPage from './pages/PricingPage.jsx'
import AdminSubscriptionsPage from './pages/AdminSubscriptionsPage.jsx'
import AdminReportPage from './pages/AdminReportPage.jsx'
import PaymentHistoryPage from './pages/PaymentHistoryPage.jsx'
import DealersPage from './pages/DealersPage.jsx'
import DealerDetailPage from './pages/DealerDetailPage.jsx'
import DealerDashboardPage from './pages/DealerDashboardPage.jsx'
import DealerProfilePage from './pages/DealerProfilePage.jsx'
import AdminDealersPage from './pages/AdminDealersPage.jsx'
import AdminManagersPage from './pages/AdminManagersPage.jsx'
import AdminReviewsPage from './pages/AdminReviewsPage.jsx'
import AccountSettingsPage from './pages/AccountSettingsPage.jsx'
import AdminCarsPage from './pages/AdminCarsPage.jsx'
import AdminCatalogPage from './pages/AdminCatalogPage.jsx'
import AdminDashboardPage from './pages/AdminDashboardPage.jsx'
import CarDetailPage from './pages/CarDetailPage.jsx'
import CarFormPage from './pages/CarFormPage.jsx'
import CatalogPage from './pages/CatalogPage.jsx'
import ContactsPage from './pages/ContactsPage.jsx'
import HomePage from './pages/HomePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import PasswordResetPage from './pages/PasswordResetPage.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        {/* Публичные страницы */}
        <Route index element={<HomePage />} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="cars/:id" element={<CarDetailPage />} />
        <Route path="compare" element={<ComparePage />} />
        <Route path="dealers" element={<DealersPage />} />
        <Route path="dealers/:slug" element={<DealerDetailPage />} />
        <Route path="contacts" element={<ContactsPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="pricing" element={<PricingPage />} />

        {/* Вход (публичной регистрации нет) */}
        <Route element={<GuestRoute />}>
          <Route path="login" element={<LoginPage />} />
          <Route path="password-reset" element={<PasswordResetPage />} />
        </Route>
        <Route path="admin/login" element={<Navigate to="/login" replace />} />

        {/* Кабинет автосалона — только role=dealer */}
        <Route element={<ProtectedRoute roles={['dealer']} />}>
          <Route element={<AccountLayout />}>
            <Route path="dashboard" element={<DealerDashboardPage />} />
            <Route path="dashboard/cars/new" element={<CarFormPage />} />
            <Route path="dashboard/cars/:id/edit" element={<CarFormPage />} />
            <Route path="dashboard/profile" element={<DealerProfilePage />} />
            <Route path="dashboard/subscription" element={<MySubscriptionPage />} />
            <Route path="dashboard/payments" element={<PaymentHistoryPage />} />
            <Route path="dashboard/account" element={<AccountSettingsPage />} />
          </Route>
        </Route>

        {/* Админка платформы — только role=admin */}
        <Route element={<ProtectedRoute roles={['admin']} />}>
          <Route element={<AdminLayout />}>
            <Route path="admin" element={<AdminDashboardPage />} />
            <Route path="admin/dealers" element={<AdminDealersPage />} />
            <Route path="admin/managers" element={<AdminManagersPage />} />
            <Route path="admin/reviews" element={<AdminReviewsPage />} />
            <Route path="admin/subscriptions" element={<AdminSubscriptionsPage />} />
            <Route path="admin/report" element={<AdminReportPage />} />
            <Route path="admin/cars" element={<AdminCarsPage />} />
            <Route path="admin/catalog" element={<AdminCatalogPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
