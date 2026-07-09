<template>
  <div class="app-wrap">
    <el-header class="bili-header">
      <div class="header-inner">
        <div class="logo" @click="goHome">
          <span class="logo-badge">B</span>
          <span class="logo-text">番剧推荐</span>
        </div>
        <div class="search-area">
          <el-input
            v-model="searchKey"
            placeholder="搜索番剧、标签、类型"
            class="header-search"
            clearable
            @keyup.enter="doSearch"
          >
            <template #append>
              <el-button class="search-btn" @click="doSearch">
                <el-icon><Search /></el-icon>
              </el-button>
            </template>
          </el-input>
        </div>
        <div class="header-right">
          <el-button text class="nav-link" @click="goUser">
            <el-icon><Star /></el-icon> 我的收藏
          </el-button>
          <template v-if="currentUser">
            <el-dropdown trigger="click">
              <span class="user-box">
                <span class="avatar">{{ (currentUser.nickname || 'U').slice(0, 1) }}</span>
                <span class="nickname">{{ currentUser.nickname }}</span>
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="goUser">我的收藏</el-dropdown-item>
                  <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <el-button v-else type="primary" round @click="goLogin">登录</el-button>
        </div>
      </div>
    </el-header>

    <el-main class="main">
      <router-view />
    </el-main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clearCurrentUser, getCurrentUser, isLoggedIn, saveFavorites } from './utils/storage'

const router = useRouter()
const currentUser = computed(() => getCurrentUser())
const searchKey = ref('')

const goHome = () => router.push('/')
const goUser = () => router.push('/user')
const goLogin = () => router.push('/login')

const doSearch = () => {
  router.push({ path: '/', query: { q: searchKey.value.trim() || undefined } })
}

const logout = () => {
  clearCurrentUser()
  saveFavorites([])
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.app-wrap {
  width: 100vw;
  min-height: 100vh;
  background: var(--bili-bg);
}
.bili-header {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid var(--bili-border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
.header-inner {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 24px;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex-shrink: 0;
}
.logo-badge {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--bili-pink), #ff9bbd);
  color: #fff;
  font-weight: 800;
  font-size: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 10px rgba(251, 114, 153, 0.35);
}
.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--bili-text);
  letter-spacing: 1px;
}
.search-area {
  flex: 1;
  max-width: 520px;
}
.header-search :deep(.el-input__wrapper) {
  border-radius: 8px 0 0 8px;
  background: #fff;
  box-shadow: 0 0 0 1px #d9dde3 inset;
}
.header-search :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--bili-pink) inset;
}
.header-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--bili-pink) inset;
}
.header-search :deep(.el-input__inner) {
  color: var(--bili-text);
}
.header-search :deep(.el-input__inner::placeholder) {
  color: #9499a0;
}
.header-search :deep(.el-input-group__append) {
  border-radius: 0 8px 8px 0;
  padding: 0;
  border: none;
  background: transparent;
}
.search-btn {
  width: 56px;
  height: 100%;
  border-radius: 0 8px 8px 0;
  background: var(--bili-pink);
  border: none;
  color: #fff;
  font-size: 18px;
}
.search-btn:hover {
  background: #fc8aab;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-shrink: 0;
  margin-left: auto;
}
.nav-link {
  color: var(--bili-text-2);
  font-size: 15px;
}
.nav-link:hover {
  color: var(--bili-pink);
}
.user-box {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  outline: none;
}
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--bili-blue), #5cc9f5);
  color: #fff;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.nickname {
  color: var(--bili-text);
  font-size: 15px;
}
.main {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}
</style>
