import { createApp } from "vue"
import ElementPlus from "element-plus"
import zhCn from "element-plus/es/locale/lang/zh-cn"
import "element-plus/dist/index.css"

import App from "./App.vue"
import router from "./router"
import { installRouterGuards } from "./router/guards"
import { AUTH_FORBIDDEN_EVENT, AUTH_UNAUTHORIZED_EVENT } from "./shared/http/runtime"
import { pinia } from "./stores"
import { useAuthStore } from "./stores/auth"
import "./styles/base.css"

installRouterGuards(router, pinia)

window.addEventListener(AUTH_UNAUTHORIZED_EVENT, () => {
  useAuthStore(pinia).clearSession()
  if (router.currentRoute.value.name !== "login") {
    void router.replace({
      name: "login",
      query: { redirect: router.currentRoute.value.fullPath, reason: "expired" },
    })
  }
})

window.addEventListener(AUTH_FORBIDDEN_EVENT, () => {
  if (router.currentRoute.value.name !== "forbidden") {
    void router.replace({ name: "forbidden" })
  }
})

createApp(App)
  .use(pinia)
  .use(router)
  .use(ElementPlus, { locale: zhCn })
  .mount("#app")
