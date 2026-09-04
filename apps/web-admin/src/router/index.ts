import { createRouter, createWebHistory } from "vue-router"

import BasicLayout from "../layouts/BasicLayout.vue"
import LoginView from "../views/auth/LoginView.vue"
import DashboardView from "../views/dashboard/DashboardView.vue"
import ForbiddenView from "../views/ForbiddenView.vue"
import NotFoundView from "../views/NotFoundView.vue"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: { title: "登录" },
    },
    {
      path: "/",
      component: BasicLayout,
      meta: { requiresAuth: true },
      children: [
        { path: "", redirect: "/dashboard" },
        {
          path: "dashboard",
          name: "dashboard",
          component: DashboardView,
          meta: { title: "工作台", requiresAuth: true },
        },
      ],
    },
    {
      path: "/403",
      name: "forbidden",
      component: ForbiddenView,
      meta: { title: "无权访问", requiresAuth: true },
    },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      component: NotFoundView,
      meta: { title: "页面不存在" },
    },
  ],
})

export default router
