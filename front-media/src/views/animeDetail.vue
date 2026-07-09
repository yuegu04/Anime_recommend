<template>
<div class="detail" v-if="media">
  <div class="top-box">
    <img class="cover" :src="media.cover || defaultCover" alt="封面" @error="onCoverError">
    <div class="info">
      <h2>{{ media.name }}</h2>
      <el-rate :model-value="Math.min((media.score || 0) / 2, 5)" disabled size="20"></el-rate>
      <div class="tag-box">
        <el-tag v-for="tag in (media.tags || '').split(',').filter(Boolean)" :key="tag" effect="dark">{{ tag }}</el-tag>
      </div>
      <div class="btn-group">
        <el-button
          v-for="opt in statusOptions"
          :key="opt.value"
          :type="currentStatus === opt.value ? 'primary' : 'default'"
          :plain="currentStatus !== opt.value"
          :loading="favLoading && pendingStatus === opt.value"
          @click="setStatus(opt.value)"
        >{{ currentStatus === opt.value ? opt.activeText : opt.text }}</el-button>
        <el-button type="success" @click="showRating = true">打分评价</el-button>
      </div>
    </div>
  </div>
  <div class="desc-box">
    <h3>剧情简介</h3>
    <p>{{ media.desc || '暂无简介' }}</p>
  </div>
  <el-dialog v-model="showRating" title="打分评价" width="400px">
    <el-rate v-model="ratingValue" :max="5" />
    <template #footer>
      <el-button @click="showRating = false">取消</el-button>
      <el-button type="primary" :loading="rateLoading" @click="handleRate">提交</el-button>
    </template>
  </el-dialog>
</div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { getFavorites, getRating, saveRating, saveFavorites, isLoggedIn, addRecentView } from '../utils/storage'

const route = useRoute()
const media = ref(null)
const serverScore = ref(null)       // 后端返回的当前档位分值（1=想看 / 3=在看 / 5=看过 / null=未收藏）
const pendingStatus = ref(0)        // 正在提交的状态档位，用于按钮 loading
// 本地占位封面（不依赖外网，避免 via.placeholder.com 被墙导致破图）
const defaultCover = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(
  `<svg xmlns='http://www.w3.org/2000/svg' width='300' height='420'><rect width='100%' height='100%' fill='#2a2147'/><text x='50%' y='50%' fill='#ffb6e0' font-size='20' font-family='Microsoft YaHei,sans-serif' text-anchor='middle' dominant-baseline='middle'>暂无封面</text></svg>`
)))
const showRating = ref(false)
const ratingValue = ref(0)
const favLoading = ref(false)
const rateLoading = ref(false)

// 当前收藏档位：登录读后端 serverScore，未登录读本地 rating（1/3/5 或 0）
const currentStatus = computed(() => {
  if (isLoggedIn()) return serverScore.value || 0
  return getRating(Number(route.params.id)) || 0
})

const onCoverError = (e) => {
  e.target.src = defaultCover
}

onMounted(async () => {
  try {
    const id = route.params.id
    const res = await api.get(`/recommend/${id}`)
    media.value = res.data
    ratingValue.value = getRating(id)
    // 详情页获取到真实数据后，同步更新最近浏览记录中的封面和简介
    addRecentView({
      id: res.data.id,
      name: res.data.name,
      cover: res.data.cover,
      score: res.data.score,
      tags: res.data.tags,
      desc: res.data.desc,
    })
    // 已登录时，从后端获取真实收藏状态
    if (isLoggedIn()) {
      try {
        const favRes = await api.get('/auth/favorites')
        const items = favRes.data.items || []
        const me = items.find((it) => it.id === Number(id))
        serverScore.value = me ? me.my_score : null
      } catch {
        serverScore.value = null
      }
    }
  } catch (error) {
    console.error(error)
  }
})

// 收藏档位配置：想看=1 / 在看=3 / 看过=5（分值同时作为推荐系统的偏好强度）
const statusOptions = [
  { value: 1, text: '想看', activeText: '✓ 想看' },
  { value: 3, text: '在看', activeText: '✓ 在看' },
  { value: 5, text: '看过', activeText: '✓ 看过' },
]

// 同步本地收藏列表（用于「我的收藏」页展示）
const syncLocalFav = (mediaId, newScore) => {
  const item = { id: mediaId, name: media.value.name, cover: media.value.cover }
  const list = getFavorites()
  if (newScore > 0) {
    if (!list.some((e) => e.id === mediaId)) saveFavorites([...list, item])
  } else {
    saveFavorites(list.filter((e) => e.id !== mediaId))
  }
}

// 设置收藏档位：再次点击同一档位 = 取消（score=0）
const setStatus = async (target) => {
  if (!media.value) return
  const mediaId = media.value.id
  const cur = currentStatus.value
  const newScore = cur === target ? 0 : target
  const label = statusOptions.find((o) => o.value === newScore)?.text

  if (isLoggedIn()) {
    pendingStatus.value = target
    favLoading.value = true
    try {
      await api.post('/recommend/behavior', null, {
        params: { media_id: mediaId, score: newScore },
      })
      serverScore.value = newScore || null
      syncLocalFav(mediaId, newScore)
      ElMessage.success(newScore ? `已标记为「${label}」` : '已取消收藏')
    } catch (error) {
      ElMessage.error('操作失败，请重试')
    } finally {
      favLoading.value = false
      pendingStatus.value = 0
    }
  } else {
    // 未登录：仅本地保存
    saveRating(mediaId, newScore)
    syncLocalFav(mediaId, newScore)
    ElMessage.success(newScore ? `已标记为「${label}」` : '已取消收藏')
  }
}

const handleRate = async () => {
  if (!media.value) return
  const mediaId = media.value.id

  rateLoading.value = true
  try {
    if (isLoggedIn()) {
      // 已登录：同步到后端（评分乘以2映射到后端10分制）
      await api.post('/recommend/behavior', null, {
        params: { media_id: mediaId, score: ratingValue.value * 2 },
      })
      serverScore.value = ratingValue.value * 2
    }
    // 本地也保存
    saveRating(mediaId, ratingValue.value)
    showRating.value = false
    ElMessage.success('评分已保存')
  } catch (error) {
    ElMessage.error('评分提交失败')
  } finally {
    rateLoading.value = false
  }
}
</script>
<style scoped>
.detail{
  color:var(--bili-text);
}
.top-box{
  display:flex;
  gap:30px;
  margin-bottom:40px;
}
.cover{
  width:260px;
  height:360px;
  border-radius:12px;
  object-fit:cover;
  background:#f0f1f3;
}
.info h2{
  font-size:28px;
  margin:0 0 10px;
  color:var(--bili-text);
}
.tag-box{
  margin:16px 0;
  display:flex;
  gap:10px;
  flex-wrap: wrap;
}
.btn-group{
  margin-top:20px;
  display:flex;
  gap:16px;
}
.desc-box h3{
  font-size:20px;
  margin-bottom:10px;
  color:var(--bili-text);
}
.desc-box p{
  line-height:1.8;
  color:var(--bili-text-2);
  font-size:16px;
}
</style>
