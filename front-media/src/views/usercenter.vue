<template>
<div class="user">
  <h2>我的个人中心</h2>
  <div class="user-info">
    <div>当前用户：{{ user?.nickname || '未登录' }}</div>
    <el-button text type="danger" @click="logout">退出登录</el-button>
  </div>
  <div class="collect-title">我的收藏动漫</div>
  <div v-if="loading" v-loading="loading" class="collect-list" style="min-height: 200px;"></div>
  <div class="collect-list" v-else-if="favorites.length">
    <div class="card" v-for="item in favorites" :key="item.id">
      <img :src="item.cover || defaultCover" alt="" @error="onCoverError">
      <p>{{ item.name }}</p>
      <el-button text type="primary" @click="$router.push(`/anime/${item.id}`)">查看详情</el-button>
    </div>
  </div>
  <div v-else class="empty">还没有收藏任何动漫，去首页探索吧！</div>
</div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clearCurrentUser, getCurrentUser, getFavorites, isLoggedIn, saveFavorites } from '../utils/storage'
import api from '../api'

const router = useRouter()
const user = computed(() => getCurrentUser())
const favorites = ref([])
const loading = ref(false)
const defaultCover = 'https://via.placeholder.com/300x420?text=No+Cover'

const onCoverError = (e) => {
  e.target.src = defaultCover
}

const loadFavorites = async () => {
  if (isLoggedIn()) {
    // 已登录：从后端获取收藏列表
    loading.value = true
    try {
      const res = await api.get('/auth/favorites')
      favorites.value = res.data.items || []
    } catch (error) {
      console.error('获取收藏失败，使用本地数据', error)
      favorites.value = getFavorites()
    } finally {
      loading.value = false
    }
  } else {
    // 未登录：使用本地数据
    favorites.value = getFavorites()
  }
}

onMounted(() => {
  loadFavorites()
})

const logout = () => {
  clearCurrentUser()
  saveFavorites([])  // 清空本地收藏，避免显示上一个用户的收藏
  favorites.value = []
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>
<style scoped>
.user{
  color:var(--bili-text);
  padding:8px 0;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
  color: var(--bili-text-2);
}
.collect-title{
  font-size:20px;
  font-weight:600;
  color:var(--bili-text);
  margin:24px 0 16px;
}
.collect-list{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
  gap:24px;
}
.card{
  background:#fff;
  border-radius:12px;
  overflow:hidden;
  border:1px solid var(--bili-border);
}
.card img{
  width:100%;
  height:260px;
  object-fit:cover;
  background:#f0f1f3;
}
.card p{
  text-align:center;
  padding:10px;
  margin:0;
  color:var(--bili-text);
}
.empty {
  text-align: center;
  padding: 40px;
  color: var(--bili-text-3);
  font-size: 16px;
}
</style>
