import { Link } from 'react-router-dom'
import { Heart } from 'lucide-react'
import { useFavorites } from '../context/FavoritesContext.jsx'
import { EmptyState, ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import CarGrid from '../components/cars/CarGrid.jsx'

export default function FavoritesPage() {
  const { favorites, loading, loadError, reloadFavorites } = useFavorites()
  const cars = favorites.map((favorite) => favorite.car_details).filter(Boolean)

  return (
    <section className="account-page">
      <PageTitle eyebrow="Сохранённые объявления" title="Избранное" description="Автомобили, к которым вы хотите вернуться." />
      {loading ? <LoadingState label="Загружаем избранное…" /> : loadError ? (
        <ErrorState message={loadError} onRetry={reloadFavorites} />
      ) : cars.length ? (
        <CarGrid cars={cars} />
      ) : (
        <EmptyState title="Здесь пока пусто" action={<Link className="button button--primary" to="/catalog">Перейти в каталог</Link>}>
          <Heart size={16} /> Нажимайте на сердечко, чтобы сохранить понравившиеся объявления.
        </EmptyState>
      )}
    </section>
  )
}
