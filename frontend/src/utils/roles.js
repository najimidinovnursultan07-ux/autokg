// Домашняя страница по роли пользователя
export function homeForRole(user) {
  if (user?.role === 'admin' && user?.is_staff) return '/admin'
  if (user?.role === 'dealer') return '/dashboard'
  return '/'
}

export function hasPanelAccess(user) {
  return (user?.role === 'admin' && user?.is_staff) || user?.role === 'dealer'
}
