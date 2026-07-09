<template>
  <div class="home">
    <section class="hero-card">
      <div class="hero-copy">
        <p class="eyebrow">个性化动漫推荐</p>
        <h1>发现你真正会爱的动漫</h1>
        <p class="hero-text">根据你的浏览、追番和评分，推荐番剧、剧场版与 OVA，让每一次探索都更贴合你的口味。</p>
        <div class="hero-stats">
          <span><b>{{ allMediaList.length || '—' }}</b> 部可看</span>
          <span class="dot">·</span>
          <span>专属你的内容过滤推荐</span>
        </div>
      </div>
      <div class="hero-side">
        <div class="mini-card" v-if="recommendedList[0]" @click="goDetail(recommendedList[0])">
          <div class="mini-label">今日推荐</div>
          <div class="mini-title">{{ recommendedList[0].name }}</div>
          <div class="mini-desc">{{ recommendedList[0].tags || '根据你的兴趣进行智能匹配' }}</div>
        </div>
        <div class="mini-card" v-else>
          <div class="mini-label">今日推荐</div>
          <div class="mini-title">{{ recommendedList[0]?.name || '正在生成推荐…' }}</div>
        </div>
      </div>
    </section>

    <section class="section-block" v-if="recentViews.length">
      <div class="section-title-row">
        <h2>最近浏览</h2>
        <span>你刚刚查看过的动漫会在这里保留</span>
        <el-button text type="danger" size="small" @click="handleClearRecent">清空</el-button>
      </div>
      <div class="anime-list">
        <div class="anime-card recent-card" v-for="item in recentViews" :key="item.id" @click="goDetail(item)">
          <div class="card-cover">
            <img v-if="getCover(item.cover)" :src="getCover(item.cover)" alt="封面" @error="onCoverError">
            <div v-else class="cover-placeholder">
              <span class="placeholder-icon">🎬</span>
              <span class="placeholder-text">{{ item.name }}</span>
            </div>
            <div class="card-score" v-if="item.score">⭐ {{ (item.score || 0).toFixed(1) }}</div>
            <button class="del-btn" @click.stop="handleRemoveRecent(item.id)" title="删除">✕</button>
          </div>
          <div class="card-info">
            <h3 class="anime-name">{{ item.name }}</h3>
            <p class="anime-desc">{{ item.desc || item.tags || '暂无简介' }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="section-block" v-if="!isSearching">
      <div class="section-title-row">
        <h2>为你推荐</h2>
        <span>基于你的行为偏好生成的个性化结果</span>
      </div>
      <div v-loading="recommendLoading" class="anime-list">
        <MediaCard v-for="item in recommendedList" :key="item.media_id || item.name" :media="{ ...item, id: item.media_id || item.id }" />
      </div>
    </section>

    <section class="section-block">
      <div class="section-title-row">
        <h2>{{ isSearching ? '搜索结果' : '全部动漫' }}</h2>
        <span v-if="isSearching">
          {{ searchKey ? `关键词「${searchKey}」` : '' }}{{ searchKey && selectedTag !== '全部' ? ' · ' : '' }}{{ selectedTag !== '全部' ? `标签「${selectedTag}」` : '' }}
        </span>
        <span v-else>支持搜索与标签筛选</span>
        <el-button v-if="isSearching" text type="primary" size="small" @click="resetSearch">返回全部</el-button>
      </div>
      <div class="tag-group">
        <el-tag
          v-for="tag in tagOptions"
          :key="tag"
          effect="plain"
          size="large"
          class="tag-item"
          :class="{ active: selectedTag === tag }"
          @click="selectedTag = tag; loadAllMedia()"
        >
          {{ tag }}
        </el-tag>
      </div>
      <div class="result-bar" v-if="!mediaLoading">
        <span>共 {{ allMediaList.length }} 条结果</span>
        <span v-if="!allMediaList.length">没有匹配到动漫，请换个关键词再试试</span>
      </div>
      <div v-if="mediaLoading && mediaPage === 0" v-loading="mediaLoading" class="anime-list"></div>
      <div v-else-if="allMediaList.length" class="anime-list">
        <MediaCard v-for="item in allMediaList" :key="item.id" :media="item" />
      </div>
      <div v-else class="empty-state">
        <p>暂时没有找到符合条件的动漫</p>
      </div>
      <div v-if="allMediaList.length && !mediaFinished" class="load-more">
        <el-button :loading="mediaLoading" @click="loadMoreMedia">加载更多</el-button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import MediaCard from '../components/MediaCard.vue'
import { getCurrentUser, getRecentViews, isLoggedIn, removeRecentView, clearRecentViews } from '../utils/storage'

const router = useRouter()
const route = useRoute()
const searchKey = ref('')
const selectedTag = ref('全部')
const recommendedList = ref([])
const allMediaList = ref([])
const recentViews = ref([])
const tagOptions = ref(['全部'])
const recommendLoading = ref(false)
const mediaLoading = ref(false)
const mediaPage = ref(0)
const mediaPageSize = 24
const mediaFinished = ref(false)
const currentUser = computed(() => getCurrentUser())
const isSearching = computed(() => !!searchKey.value.trim() || selectedTag.value !== '全部')

const resetSearch = () => {
  searchKey.value = ''
  selectedTag.value = '全部'
  router.replace({ path: '/' })
}

const getCover = (cover) => {
  if (!cover || !String(cover).trim()) return ''
  if (String(cover).includes('data:image/svg+xml')) return ''
  if (String(cover).includes('via.placeholder.com')) return ''
  return cover
}

const onCoverError = (e) => {
  e.target.style.display = 'none'
}

const goDetail = (item) => {
  router.push(`/anime/${item.id}`)
}

const handleRemoveRecent = (id) => {
  recentViews.value = removeRecentView(id)
}

const handleClearRecent = () => {
  clearRecentViews()
  recentViews.value = []
}

const loadRecommendations = async () => {
  recommendLoading.value = true
  try {
    const userId = isLoggedIn() ? String(currentUser.value.id) : 'doing'
    const res = await api.get('/recommend/list', {
      params: { user_id: userId, top_n: 8 }
    })
    recommendedList.value = res.data.items || []
  } catch (error) {
    console.error(error)
    recommendedList.value = []
  } finally {
    recommendLoading.value = false
  }
}

const loadAllMedia = async (append = false) => {
  if (!append) {
    mediaPage.value = 0
    mediaFinished.value = false
    allMediaList.value = []
  }
  mediaLoading.value = true
  try {
    const res = await api.get('/media/list', {
      params: {
        search: searchKey.value,
        tag: selectedTag.value,
        limit: mediaPageSize,
        offset: mediaPage.value * mediaPageSize,
      }
    })
    const items = res.data.items || []
    tagOptions.value = ['全部', ...(res.data.tags || [])]
    if (append) {
      allMediaList.value = [...allMediaList.value, ...items]
    } else {
      allMediaList.value = items
    }
    mediaFinished.value = items.length < mediaPageSize
  } catch (error) {
    console.error(error)
    if (!append) allMediaList.value = []
  } finally {
    mediaLoading.value = false
  }
}

const loadMoreMedia = () => {
  if (mediaLoading.value || mediaFinished.value) return
  mediaPage.value += 1
  loadAllMedia(true)
}

const refreshRecentViews = () => {
  recentViews.value = getRecentViews()
}

// 顶栏搜索通过路由 ?q= 驱动列表
watch(() => route.query.q, (q) => {
  searchKey.value = q ? String(q) : ''
  loadAllMedia()
})

onMounted(() => {
  refreshRecentViews()
  loadRecommendations()
  const q = route.query.q
  if (q) {
    searchKey.value = String(q)
  }
  loadAllMedia()
})
</script>

<style scoped>
.home {
  width: 100%;
}
.recent-card {
  position: relative;
}
.del-btn {
  position: absolute;
  top: 10px;
  left: 10px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 14px;
  line-height: 26px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 2;
}
.recent-card:hover .del-btn {
  opacity: 1;
}
.del-btn:hover {
  background: var(--bili-pink);
}
.hero-card {
  display: grid;
  grid-template-columns: 1.6fr 0.8fr;
  gap: 24px;
  padding: 32px;
  border-radius: 20px;
  background: linear-gradient(135deg, #ffeef5 0%, #e9f3ff 100%);
  border: 1px solid var(--bili-border);
  margin-bottom: 32px;
}
.eyebrow {
  color: var(--bili-pink);
  font-size: 13px;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  margin-bottom: 10px;
  font-weight: 600;
}
.hero-copy h1 {
  color: var(--bili-text);
  font-size: 34px;
  margin: 0 0 12px;
}
.hero-text {
  color: var(--bili-text-2);
  line-height: 1.8;
  font-size: 15px;
  margin-bottom: 18px;
}
.hero-stats {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--bili-text-2);
  font-size: 14px;
}
.hero-stats b {
  color: var(--bili-pink);
  font-size: 16px;
}
.hero-stats .dot {
  color: var(--bili-text-3);
}
.hero-side {
  display: flex;
  align-items: center;
  justify-content: center;
}
.mini-card {
  width: 100%;
  padding: 22px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid var(--bili-border);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: transform 0.2s;
}
.mini-card:hover {
  transform: translateY(-4px);
}
.mini-label {
  color: var(--bili-pink);
  font-size: 12px;
  margin-bottom: 8px;
  text-transform: uppercase;
  font-weight: 600;
}
.mini-title {
  color: var(--bili-text);
  font-size: 20px;
  margin-bottom: 8px;
  font-weight: 600;
}
.mini-desc {
  color: var(--bili-text-2);
  line-height: 1.6;
}
.section-block {
  margin-bottom: 32px;
}
.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.section-title-row h2 {
  color: var(--bili-text);
  margin: 0;
}
.section-title-row span {
  color: var(--bili-text-3);
}
.tag-group {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.tag-item {
  padding: 8px 14px;
  cursor: pointer;
  background: #fff !important;
  border: 1px solid var(--bili-border) !important;
  color: var(--bili-text-2);
}
.tag-item.active {
  background: var(--bili-pink) !important;
  border-color: var(--bili-pink) !important;
  color: #fff !important;
}
.result-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--bili-text-3);
  margin-bottom: 16px;
}
.empty-state {
  padding: 24px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid var(--bili-border);
  color: var(--bili-text-3);
  text-align: center;
}
.anime-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 24px;
}
.anime-card {
  background: #fff;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--bili-border);
  cursor: pointer;
  transition: all 0.25s ease;
}
.anime-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
  border-color: rgba(251, 114, 153, 0.5);
}
.card-cover {
  width: 100%;
  height: 320px;
  position: relative;
  overflow: hidden;
  background: #f0f1f3;
}
.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: 0.4s;
}
.anime-card:hover .card-cover img {
  transform: scale(1.06);
}
.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8eaed, #f4f5f7);
  gap: 12px;
}
.placeholder-icon {
  font-size: 48px;
}
.placeholder-text {
  color: var(--bili-text-3);
  font-size: 14px;
  text-align: center;
  padding: 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-score {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.6);
  color: #ffdd70;
  padding: 3px 9px;
  border-radius: 10px;
  font-size: 13px;
}
.card-info {
  padding: 14px 16px 18px;
}
.anime-name {
  font-size: 17px;
  color: var(--bili-text);
  margin: 0 0 8px;
  font-weight: 600;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.anime-name:hover {
  color: var(--bili-pink);
}
.anime-desc {
  color: var(--bili-text-2);
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
@media (max-width: 900px) {
  .hero-card {
    grid-template-columns: 1fr;
  }
}
</style>
