/* global __APP_VERSION__, __APP_COMMIT__, __APP_BUILD_DATE__ */
// Значения подставляет Vite при сборке (см. vite.config.js)
export const APP_VERSION = __APP_VERSION__
export const APP_COMMIT = __APP_COMMIT__
export const APP_BUILD_DATE = __APP_BUILD_DATE__

// «v1.0.0» — коротко для подвала
export const versionLabel = `v${APP_VERSION}`

// «v1.0.0 · 8022a3c · 2026-11-22» — подробно для админки
export const versionDetails = [versionLabel, APP_COMMIT, APP_BUILD_DATE].filter(Boolean).join(' · ')
