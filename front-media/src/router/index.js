import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import AnimeDetail from '../views/AnimeDetail.vue'
import UserCenter from '../views/UserCenter.vue'

const routes = [
  { path: '/', name: '首页', component: Home },
  { path: '/login', name: '登录', component: Login },
  { path: '/anime/:id', name: '动漫详情', component: AnimeDetail },
  { path: '/user', name: '个人中心', component: UserCenter },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router