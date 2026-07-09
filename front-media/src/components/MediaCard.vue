<template>
  <div class="anime-card" @click="handleViewDetail">
    <div class="card-cover">
      <img v-if="coverSrc" :src="coverSrc" alt="封面" @error="onCoverError">
      <div v-else class="cover-placeholder">
        <span class="placeholder-icon">🎬</span>
        <span class="placeholder-text">{{ media.name }}</span>
      </div>
      <div class="card-score" v-if="media.score">⭐ {{ (media.score || 0).toFixed(1) }}</div>
    </div>
    <div class="card-info">
      <h3 class="anime-name">{{ media.name }}</h3>
      <p class="anime-desc">{{ media.desc || media.tags || '暂无简介' }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { addRecentView } from '../utils/storage'

const props = defineProps({
  media: {
    type: Object,
    required: true,
  },
})

const router = useRouter()

const coverSrc = computed(() => {
  const c = props.media.cover
  if (!c || !String(c).trim()) return ''
  if (String(c).includes('data:image/svg+xml')) return ''
  if (String(c).includes('via.placeholder.com')) return ''
  return c
})

const onCoverError = (e) => {
  e.target.style.display = 'none'
}

const handleViewDetail = () => {
  addRecentView({
    id: props.media.id,
    name: props.media.name,
    cover: props.media.cover,
    score: props.media.score,
    tags: props.media.tags,
    desc: props.media.desc,
  })
  router.push(`/anime/${props.media.id}`)
}
</script>

<style scoped>
.anime-card {
  background: var(--bili-card);
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
  height: 300px;
  position: relative;
  overflow: hidden;
  background: #f0f1f3;
}
.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.35s ease;
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
  font-size: 44px;
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
  padding: 12px 14px 16px;
}
.anime-name {
  font-size: 16px;
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
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
