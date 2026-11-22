# AutoBuy

Маркетплейс автомобилей Кыргызстана: React/Vite frontend, Django REST API и PostgreSQL.

## Структура проекта

```text
AutoBuy/
├── .env.example
├── .env.production.example
├── .gitignore
├── docker-compose.yml
├── docker-compose.prod.yml
├── README.md
├── .vscode/
│   └── settings.json
├── backend/
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/
│   │   ├── asgi.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── settings/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── local.py
│   │       └── production.py
│   └── apps/
│       ├── __init__.py
│       ├── accounts/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── tokens.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   ├── migrations/
│       │   │   ├── __init__.py
│       │   │   ├── 0001_initial.py
│       │   │   ├── 0002_user_favorite_cars_user_updated_at.py
│       │   │   ├── 0003_require_user_updated_at.py
│       │   │   └── 0004_profile_photo.py
│       │   └── tests/
│       │       ├── __init__.py
│       │       └── test_auth_api.py
│       ├── admin_api/
│       │   ├── __init__.py
│       │   ├── apps.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests/
│       │       ├── __init__.py
│       │       └── test_admin_api.py
│       ├── cars/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── filters.py
│       │   ├── models.py
│       │   ├── pagination.py
│       │   ├── permissions.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   ├── migrations/
│       │   │   ├── __init__.py
│       │   │   ├── 0001_initial.py
│       │   │   ├── 0002_model_remove_vehiclemodel_brand_and_more.py
│       │   │   ├── 0003_backfill_timestamps_and_seed_cities.py
│       │   │   ├── 0004_alter_car_engine_volume.py
│       │   │   ├── 0005_car_car_engine_type_is_valid_and_more.py
│       │   │   ├── 0006_alter_car_contact_phone.py
│       │   │   └── 0007_alter_carimage_image.py
│       │   └── tests/
│       │       ├── __init__.py
│       │       ├── test_car_api.py
│       │       └── test_models_and_serializers.py
│       ├── common/
│       │   ├── __init__.py
│       │   ├── admin_config.py
│       │   ├── admin_site.py
│       │   ├── apps.py
│       │   ├── exceptions.py
│       │   ├── permissions.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   └── tests/
│       │       ├── __init__.py
│       │       └── test_health_api.py
│       ├── favorites/
│       │   ├── __init__.py
│       │   ├── admin.py
│       │   ├── apps.py
│       │   ├── models.py
│       │   ├── serializers.py
│       │   ├── urls.py
│       │   ├── views.py
│       │   ├── migrations/
│       │   │   ├── __init__.py
│       │   │   ├── 0001_initial.py
│       │   │   └── 0002_alter_favorite_car_alter_favorite_user.py
│       │   └── tests.py
│       └── moderation/
│           ├── __init__.py
│           ├── admin.py
│           ├── apps.py
│           ├── models.py
│           └── migrations/
│               ├── __init__.py
│               ├── 0001_initial.py
│               └── 0002_alter_moderationevent_action.py
└── frontend/
    ├── .dockerignore
    ├── .env.example
    ├── .gitignore
    ├── .oxlintrc.json
    ├── Dockerfile
    ├── README.md
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js
    ├── nginx/
    │   └── default.conf
    ├── public/
    │   ├── favicon.svg
    │   └── icons.svg
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── api/
        │   ├── admin.js
        │   ├── auth.js
        │   ├── cars.js
        │   ├── client.js
        │   └── favorites.js
        ├── assets/
        │   ├── hero.png
        │   ├── react.svg
        │   └── vite.svg
        ├── components/
        │   ├── cars/
        │   │   ├── CarCard.jsx
        │   │   ├── CarGrid.jsx
        │   │   └── FavoriteButton.jsx
        │   ├── common/
        │   │   ├── ErrorBoundary.jsx
        │   │   └── States.jsx
        │   ├── layout/
        │   │   ├── AccountLayout.jsx
        │   │   ├── AdminLayout.jsx
        │   │   ├── AppLayout.jsx
        │   │   ├── Footer.jsx
        │   │   └── Header.jsx
        │   └── routing/
        │       ├── AdminRoute.jsx
        │       ├── GuestRoute.jsx
        │       └── ProtectedRoute.jsx
        ├── context/
        │   ├── AuthContext.jsx
        │   ├── FavoritesContext.jsx
        │   └── ToastContext.jsx
        ├── pages/
        │   ├── AboutPage.jsx
        │   ├── AccountSettingsPage.jsx
        │   ├── AdminCarsPage.jsx
        │   ├── AdminCatalogPage.jsx
        │   ├── AdminDashboardPage.jsx
        │   ├── AdminUsersPage.jsx
        │   ├── CarDetailPage.jsx
        │   ├── CarFormPage.jsx
        │   ├── CatalogPage.jsx
        │   ├── ContactsPage.jsx
        │   ├── DashboardPage.jsx
        │   ├── FavoritesPage.jsx
        │   ├── HomePage.jsx
        │   ├── LoginPage.jsx
        │   ├── MyCarsPage.jsx
        │   ├── NotFoundPage.jsx
        │   ├── PasswordResetPage.jsx
        │   ├── ProfilePage.jsx
        │   └── RegisterPage.jsx
        ├── styles/
        │   └── global.css
        └── utils/
            ├── errors.js
            └── format.js
```

`.env` — локальные секреты и настройки, он не должен попадать в Git. SQLite-файлы, `media/`, `staticfiles/`, `node_modules/` и `dist/` — локальные или собираемые данные, а не исходные файлы проекта.

## Зависимости и конфигурация

- Backend: Python 3.14, Django, Django REST Framework, Simple JWT, django-filter, Pillow, psycopg 3, Gunicorn и WhiteNoise. Прямые Python-зависимости закреплены в `backend/requirements.txt`.
- Frontend: Node.js 22+ (для Vite 8 — 22.12+), React, React Router, Axios и Lucide React. Точные версии зависимостей зафиксированы в `frontend/package-lock.json`; устанавливайте их через `npm ci`.
- Database: PostgreSQL 17. Для локальной разработки можно установить его отдельно или запустить через Compose.
- Локальные настройки читаются из корневого `.env`; `config.settings.local` предназначен для разработки, `config.settings.production` — для HTTPS-развёртывания.

## Локальный запуск в Windows PowerShell

### 1. Создать окружение

Из корня проекта:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

Если PowerShell блокирует активацию виртуального окружения, откройте новый PowerShell с разрешённым выполнением локальных скриптов либо запускайте `.\.venv\Scripts\python.exe` напрямую.

Проверьте корневой `.env`: для установленного локально PostgreSQL задайте правильные `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST=localhost` и `DB_PORT`. Не используйте примерный пароль на production-сервере.

Если PostgreSQL установлен отдельно и роль/база ещё не созданы, выполните в `psql -U postgres` (пароль укажите такой же, как `DB_PASSWORD`):

```sql
CREATE USER autobuy WITH PASSWORD 'local-only-change-me';
CREATE DATABASE autobuy OWNER autobuy;
```

### 2. Запустить Backend

Убедитесь, что PostgreSQL 17 запущен, затем в отдельном терминале:

```powershell
.\.venv\Scripts\Activate.ps1
Set-Location backend
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

`migrate` применяет уже включённые в проект миграции, в том числе начальный каталог популярных марок и моделей. Дополнить каталог можно через административную панель. `makemigrations` запускайте после изменения моделей, а не при обычном старте:

```powershell
python manage.py makemigrations
python manage.py migrate
```

### 3. Запустить Frontend

В другом терминале из корня проекта:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Откройте `http://localhost:5173`. По умолчанию браузер обращается к API на том же hostname и порту `8000`; при другом расположении API укажите `VITE_API_BASE_URL` в `frontend/.env.local`, например `http://localhost:8000/api`.

### Проверки разработки

Из `backend/`:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Из `frontend/`:

```powershell
npm run lint
npm run build
```

## Запуск локального стека через Docker Compose

Нужны Docker Desktop (Windows) или Docker Engine и Compose plugin. Скопируйте `.env.example` в `.env`, если `.env` ещё не создан, затем из корня проекта выполните:

```powershell
docker compose up --build -d
docker compose ps
```

Compose запускает PostgreSQL, Django с миграциями и Vite. Откройте `http://localhost:5173`; API доступен на `http://localhost:8000`. PostgreSQL и пользовательские фотографии сохраняются в именованных Docker volumes.

Создать администратора:

```powershell
docker compose exec backend python manage.py createsuperuser
```

Остановить приложения, сохранив данные:

```powershell
docker compose down
```

## Production-сборка и запуск

Production Compose использует Django production settings и Gunicorn, собирает React в Nginx, проксирует API/admin/static и раздаёт загруженные фото из постоянного media volume.

1. Создайте защищённый production `.env` на основе `.env.production.example` (не перезаписывайте существующий файл без резервной копии). Сгенерируйте уникальный ключ:

   ```powershell
   if (-not (Test-Path .env)) { Copy-Item .env.production.example .env }
   python -c "import secrets; print(secrets.token_urlsafe(64))"
   ```

   Задайте реальный `SECRET_KEY`, сильный пароль БД, SMTP-реквизиты, домен в `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` и `CSRF_TRUSTED_ORIGINS`. Установите HTTPS URL в `PASSWORD_RESET_URL`. Не публикуйте production `.env`.

2. Запустите сборку:

   ```powershell
   docker compose -f docker-compose.prod.yml up --build -d
   docker compose -f docker-compose.prod.yml ps
   ```

   Контейнер backend применяет миграции, собирает Django static-файлы и запускает Gunicorn. Nginx обслуживает React SPA, проксирует `/api/`, `/django-admin/` и `/static/`, а `/media/` читает из общего volume. HTTPS должен завершаться на внешнем reverse proxy/load balancer, который передаёт `X-Forwarded-Proto: https`; production Django принудительно включает HTTPS redirect, HSTS и Secure cookies. Production порт Nginx по умолчанию привязан к `127.0.0.1:8080`, чтобы его мог обслуживать локальный TLS proxy.

3. Создайте администратора:

   ```powershell
   docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
   ```

Миграции и `collectstatic` выполняются при старте production backend. Для многорепличного развёртывания вынесите миграции в отдельный deployment job перед масштабированием backend.

## Тарифы автосалонов

Оплата на сайте не принимается: салон оставляет заявку в кабинете («Мой тариф»), платит напрямую, администратор включает тариф в разделе «Тарифы» админки. Цены и лимиты меняются в Django-админке (Тарифы → Тарифы).

Напоминания об окончании тарифа (письма менеджерам салона за 3 дня, за 1 день и в день окончания + сводка админу в Telegram) отправляются раз в день:

- переменные бэкенда: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID` (необязательно), `CRON_SECRET`, настроенный SMTP (`EMAIL_*`);
- если `TELEGRAM_BOT_TOKEN` не задан, уведомления отправляет бот кодов входа (`TELEGRAM_BOT_ADMIN_TOKEN`) — достаточно одного бота;
- запуск — GitHub Actions `.github/workflows/subscription-reminders.yml` (секреты репозитория `BACKEND_URL` и `CRON_SECRET`), либо вручную / Render Cron Job: `python manage.py send_subscription_reminders`.

О каждой новой заявке на тариф администратор сразу получает сообщение в Telegram.

## Реклама партнёров

Баннеры сторонних компаний (банки, страховые, автосервисы и т.д.) — админка → «Реклама». Для баннера задаются рекламодатель, ссылка, место показа, период и приоритет; можно загрузить отдельную картинку для телефона.

Места показа: главная сверху и между блоками (1200×300, телефон 800×400), каталог после 6-го объявления (1200×300), страница авто рядом с контактами (600×400). Если в одном месте несколько баннеров, они чередуются с учётом приоритета.

Показ засчитывается, когда баннер виден на экране хотя бы наполовину; клик идёт через `/api/ads/<id>/click/` с редиректом на сайт рекламодателя (повторный клик с одного IP в течение 10 минут не считается). Статистика по дням и выгрузка в Excel для рекламодателя — кнопка «Статистика» у баннера.

## Проверка работоспособности

Локальный запуск:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health/
Invoke-RestMethod http://127.0.0.1:8000/api/health/ready/
```

`/api/health/` проверяет процесс API, `/api/health/ready/` также проверяет соединение с PostgreSQL. В Docker смотрите статусы и логи:

```powershell
docker compose ps
docker compose logs --tail 100 backend
docker compose logs --tail 100 frontend
```

Production readiness проверяйте через HTTPS-домен:

```powershell
Invoke-RestMethod https://autobuy.example.com/api/health/ready/
```

Также проверьте главную страницу, вход в `/django-admin/`, API-каталог и открытие загруженной фотографии по URL `/media/...`. Если readiness возвращает 503, проверьте PostgreSQL, `DB_*` параметры и логи backend.

## Схема раздачи файлов

- React production build обслуживается Nginx; fallback на `index.html` поддерживает React Router при прямом открытии вложенных маршрутов.
- Django static assets собираются в `STATIC_ROOT` через `collectstatic` и отдаются WhiteNoise через Nginx proxy.
- Car images и profile photos сохраняются в `MEDIA_ROOT`. Production Compose подключает один persistent `media_data` volume к backend на запись и Nginx на чтение.
- PostgreSQL хранится отдельно в persistent volume. `docker compose down` не удаляет volumes; резервное копирование БД и media нужно настроить до production-эксплуатации.
