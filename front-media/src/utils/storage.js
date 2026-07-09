import { reactive } from 'vue'

const USER_KEY = 'anime_user'
const TOKEN_KEY = 'anime_token'
const FAVORITES_KEY = 'anime_favorites'
const RECENT_KEY = 'anime_recent'
const RATINGS_KEY = 'anime_ratings'
const PROGRESS_KEY = 'anime_progress'

const state = reactive({
  user: loadUser(),
  token: localStorage.getItem(TOKEN_KEY) || '',
  favorites: loadArray(FAVORITES_KEY),
  recentViews: loadArray(RECENT_KEY),
  ratings: loadObject(RATINGS_KEY),
  progress: loadObject(PROGRESS_KEY),
})

function loadUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY)) || null
  } catch {
    return null
  }
}

function loadArray(key) {
  try {
    return JSON.parse(localStorage.getItem(key)) || []
  } catch {
    return []
  }
}

function loadObject(key) {
  try {
    return JSON.parse(localStorage.getItem(key)) || {}
  } catch {
    return {}
  }
}

function persist(key, value) {
  localStorage.setItem(key, JSON.stringify(value))
}

// ============ 用户认证 ============

export function getCurrentUser() {
  return state.user
}

export function getToken() {
  return state.token
}

export function setCurrentUser(user, token = '') {
  state.user = user
  state.token = token
  persist(USER_KEY, user)
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  }
}

export function clearCurrentUser() {
  state.user = null
  state.token = ''
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(TOKEN_KEY)
}

export function isLoggedIn() {
  return !!state.token && !!state.user
}

// ============ 收藏 ============

export function getFavorites() {
  return state.favorites
}

export function saveFavorites(items) {
  state.favorites = items
  persist(FAVORITES_KEY, items)
}

export function toggleFavorite(item) {
  const list = getFavorites()
  const exists = list.some((entry) => entry.id === item.id)
  const next = exists ? list.filter((entry) => entry.id !== item.id) : [...list, item]
  saveFavorites(next)
  return next
}

export async function syncFavoritesFromServer(token) {
  try {
    const res = await fetch('http://127.0.0.1:8000/auth/favorites', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      saveFavorites([])
      return
    }
    const data = await res.json()
    saveFavorites(data.items || [])
  } catch {
    saveFavorites([])
  }
}

// ============ 最近浏览 ============

export function getRecentViews() {
  return state.recentViews
}

export function addRecentView(item) {
  const list = getRecentViews()
  const next = [item, ...list.filter((entry) => entry.id !== item.id)].slice(0, 6)
  state.recentViews = next
  persist(RECENT_KEY, next)
  return next
}

export function removeRecentView(id) {
  const list = getRecentViews()
  const next = list.filter((entry) => entry.id !== id)
  state.recentViews = next
  persist(RECENT_KEY, next)
  return next
}

export function clearRecentViews() {
  state.recentViews = []
  persist(RECENT_KEY, [])
}

// ============ 评分 ============

export function getRating(mediaId) {
  return state.ratings[mediaId] || 0
}

export function saveRating(mediaId, score) {
  state.ratings = { ...state.ratings, [mediaId]: score }
  persist(RATINGS_KEY, state.ratings)
}

// ============ 进度 ============

export function getProgress(mediaId) {
  return state.progress[mediaId] || 0
}

export function saveProgress(mediaId, value) {
  state.progress = { ...state.progress, [mediaId]: value }
  persist(PROGRESS_KEY, state.progress)
}
