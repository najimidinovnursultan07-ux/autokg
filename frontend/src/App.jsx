import { Route, Routes } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout.jsx'
import AccountLayout from './components/layout/AccountLayout.jsx'
import AdminLayout from './components/layout/AdminLayout.jsx'
import ProtectedRoute from './components/routing/ProtectedRoute.jsx'
import AdminRoute from './components/routing/AdminRoute.jsx'
import GuestRoute from './components/routing/GuestRoute.jsx'
import AdminLoginPage from './pages/AdminLoginPage.jsx'
import AboutPage from './pages/AboutPage.jsx'
import AccountSettingsPage from './pages/AccountSettingsPage.jsx'
import AdminCarsPage from './pages/AdminCarsPage.jsx'
import AdminCatalogPage from './pages/AdminCatalogPage.jsx'
import AdminDashboardPage from './pages/AdminDashboardPage.jsx'
import AdminUsersPage from './pages/AdminUsersPage.jsx'
import CarDetailPage from './pages/CarDetailPage.jsx'
import CarFormPage from './pages/CarFormPage.jsx'
import CatalogPage from './pages/CatalogPage.jsx'
import ContactsPage from './pages/ContactsPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import FavoritesPage from './pages/FavoritesPage.jsx'
import HomePage from './pages/HomePage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import MyCarsPage from './pages/MyCarsPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import PasswordResetPage from './pages/PasswordResetPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="cars/:id" element={<CarDetailPage />} />
        <Route path="contacts" element={<ContactsPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route element={<GuestRoute />}>
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="password-reset" element={<PasswordResetPage />} />
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route element={<AccountLayout />}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="my-cars" element={<MyCarsPage />} />
            <Route path="favorites" element={<FavoritesPage />} />
            <Route path="account-settings" element={<AccountSettingsPage />} />
          </Route>
          <Route path="cars/new" element={<CarFormPage />} />
          <Route path="cars/:id/edit" element={<CarFormPage />} />
        </Route>
        <Route element={<AdminRoute />}>
          <Route element={<AdminLayout />}>
            <Route path="admin" element={<AdminDashboardPage />} />
            <Route path="admin/users" element={<AdminUsersPage />} />
            <Route path="admin/cars" element={<AdminCarsPage />} />
            <Route path="admin/catalog" element={<AdminCatalogPage />} />
          </Route>
        </Route>
        <Route path="admin/login" element={<AdminLoginPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
