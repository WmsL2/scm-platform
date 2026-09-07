import { createRouter, createWebHistory } from "vue-router"

import BasicLayout from "../layouts/BasicLayout.vue"
import LoginView from "../views/auth/LoginView.vue"
import DashboardView from "../views/dashboard/DashboardView.vue"
import ForbiddenView from "../views/ForbiddenView.vue"
import NotFoundView from "../views/NotFoundView.vue"
import SupplierCreateView from "../views/supplier/SupplierCreateView.vue"
import SupplierDetailView from "../views/supplier/SupplierDetailView.vue"
import SupplierEditView from "../views/supplier/SupplierEditView.vue"
import SupplierListView from "../views/supplier/SupplierListView.vue"

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
        {
          path: "suppliers",
          name: "supplier-list",
          component: SupplierListView,
          meta: { title: "供应商管理", requiresAuth: true, permission: "supplier:list" },
        },
        {
          path: "suppliers/new",
          name: "supplier-create",
          component: SupplierCreateView,
          meta: { title: "新增供应商", requiresAuth: true, permission: "supplier:create" },
        },
        {
          path: "suppliers/:id",
          name: "supplier-detail",
          component: SupplierDetailView,
          meta: { title: "供应商详情", requiresAuth: true, permission: "supplier:detail" },
        },
        {
          path: "suppliers/:id/edit",
          name: "supplier-edit",
          component: SupplierEditView,
          meta: { title: "编辑供应商", requiresAuth: true, permission: "supplier:update" },
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
