/// <reference types="vite/client" />

import "vue-router"

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_USE_MOCK?: string
  readonly VITE_APP_TITLE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare module "vue-router" {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    permission?: string
  }
}
