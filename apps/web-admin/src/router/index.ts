import { createRouter, createWebHistory } from "vue-router"
import BasicLayout from "../layouts/BasicLayout.vue"
import HomeView from "../views/HomeView.vue"
import NotFoundView from "../views/NotFoundView.vue"
export default createRouter({ history: createWebHistory(), routes: [{ path: "/", component: BasicLayout, children: [{ path: "", component: HomeView }] }, { path: "/:pathMatch(.*)*", component: NotFoundView }] })

