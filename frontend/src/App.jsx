import { lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout.jsx'
import ProtectedRoute from './components/routing/ProtectedRoute.jsx'
import GuestRoute from './components/routing/GuestRoute.jsx'
import HomePage from './pages/HomePage.jsx'

// Главная грузится сразу; остальные страницы — отдельными файлами, только когда их открывают.
// Так покупатель не скачивает код админки и кабинета салона.
const AccountLayout = lazy(() => import('./components/layout/AccountLayout.jsx'))
const AdminLayout = lazy(() => import('./components/layout/AdminLayout.jsx'))
const AboutPage = lazy(() => import('./pages/AboutPage.jsx'))
const ComparePage = lazy(() => import('./pages/ComparePage.jsx'))
const MySubscriptionPage = lazy(() => import('./pages/MySubscriptionPage.jsx'))
const DealerReportPage = lazy(() => import('./pages/DealerReportPage.jsx'))
const PricingPage = lazy(() => import('./pages/PricingPage.jsx'))
const AdminSubscriptionsPage = lazy(() => import('./pages/AdminSubscriptionsPage.jsx'))
const AdminReportPage = lazy(() => import('./pages/AdminReportPage.jsx'))
const AdminAdsPage = lazy(() => import('./pages/AdminAdsPage.jsx'))
const PaymentHistoryPage = lazy(() => import('./pages/PaymentHistoryPage.jsx'))
const DealersPage = lazy(() => import('./pages/DealersPage.jsx'))
const DealerDetailPage = lazy(() => import('./pages/DealerDetailPage.jsx'))
const DealerDashboardPage = lazy(() => import('./pages/DealerDashboardPage.jsx'))
const DealerProfilePage = lazy(() => import('./pages/DealerProfilePage.jsx'))
const AdminDealersPage = lazy(() => import('./pages/AdminDealersPage.jsx'))
const AdminManagersPage = lazy(() => import('./pages/AdminManagersPage.jsx'))
const AdminReviewsPage = lazy(() => import('./pages/AdminReviewsPage.jsx'))
const AccountSettingsPage = lazy(() => import('./pages/AccountSettingsPage.jsx'))
const AdminCarsPage = lazy(() => import('./pages/AdminCarsPage.jsx'))
const AdminCatalogPage = lazy(() => import('./pages/AdminCatalogPage.jsx'))
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage.jsx'))
const CarDetailPage = lazy(() => import('./pages/CarDetailPage.jsx'))
const CarFormPage = lazy(() => import('./pages/CarFormPage.jsx'))
const CatalogPage = lazy(() => import('./pages/CatalogPage.jsx'))
const ContactsPage = lazy(() => import('./pages/ContactsPage.jsx'))
const LoginPage = lazy(() => import('./pages/LoginPage.jsx'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage.jsx'))
const PasswordResetPage = lazy(() => import('./pages/PasswordResetPage.jsx'))

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
            <Route path="dashboard/report" element={<DealerReportPage />} />
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
            <Route path="admin/ads" element={<AdminAdsPage />} />
            <Route path="admin/cars" element={<AdminCarsPage />} />
            <Route path="admin/catalog" element={<AdminCatalogPage />} />
            <Route path="admin/account" element={<AccountSettingsPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
