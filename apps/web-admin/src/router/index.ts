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
import ProductDetailView from "../views/catalog/ProductDetailView.vue"
import ProductListView from "../views/catalog/ProductListView.vue"
import CategoryListView from "../views/catalog/CategoryListView.vue"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: { title: "登录" },
    },
    { path: "/register", name: "register", component: LoginView, meta: { title: "注册" } },
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
        { path: "admin/users", name: "admin-users", component: () => import("../views/admin/UsersView.vue"), meta: { title: "用户管理", requiresAuth: true, permission: "system:user:list" } },
        { path: "admin/roles", name: "admin-roles", component: () => import("../views/admin/RolesView.vue"), meta: { title: "角色权限", requiresAuth: true, permission: "system:role:list" } },
        { path: "admin/registrations", name: "admin-registrations", component: () => import("../views/admin/RegistrationsView.vue"), meta: { title: "注册审批", requiresAuth: true, permission: "system:registration:list" } },
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
        {
          path: "products",
          name: "product-list",
          component: ProductListView,
          meta: { title: "商品主数据", requiresAuth: true, permission: "product:list" },
        },
        {
          path: "categories",
          name: "category-list",
          component: CategoryListView,
          meta: { title: "类目管理", requiresAuth: true, permission: "category:list" },
        },
        {
          path: "products/:id",
          name: "product-detail",
          component: ProductDetailView,
          meta: { title: "商品详情", requiresAuth: true, permission: "product:detail" },
        },
        { path: "bid-projects", name: "bid-project-list", component: () => import("../views/bid/BidProjectListView.vue"), meta: { title: "投标项目", requiresAuth: true, permission: "bid:list" } },
        { path: "bid-projects/:id", name: "bid-project-detail", component: () => import("../views/bid/BidProjectDetailView.vue"), meta: { title: "投标项目详情", requiresAuth: true, permission: "bid:detail" } },
        { path: "bid-projects/:id/workbench", name: "bid-project-workbench", component: () => import("../views/bid/BidMatchingWorkbenchView.vue"), meta: { title: "匹配工作台", requiresAuth: true, permission: "bid:detail" } },
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
