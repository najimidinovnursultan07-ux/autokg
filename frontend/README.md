# AutoBuy frontend

React, Vite, JavaScript, React Router, Axios and Lucide React application for the AutoBuy marketplace.

## Local development

1. Start the Django API at `http://localhost:8000`.
2. From this directory install the locked package versions:

   ```powershell
   npm ci
   ```

3. Start Vite:

   ```powershell
   npm run dev
   ```

The default API URL is `http://localhost:8000/api`. Override it with `VITE_API_BASE_URL`. Set `VITE_SUPPORT_EMAIL` only after a real support address has been provisioned.

## Validation

```powershell
npm run lint
npm run build
```

The access token is kept in memory; the refresh token is held in the backend's HttpOnly cookie. API writes attach the Django CSRF token. The frontend refreshes expired access tokens and clears the local session when refresh is rejected.

## Main folders

- `src/api` — Axios client and API modules for auth, cars and favorites.
- `src/components` — shared layout, car cards, states and protected-route components.
- `src/context` — authentication, favorite-list and notification state.
- `src/pages` — route-level screens.
- `src/styles` — responsive application stylesheet.
