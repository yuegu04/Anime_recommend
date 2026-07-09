<template>
<div class="login-wrap">
  <div class="login-card">
    <h1 class="title">动漫推荐系统 · {{ isRegister ? '注册' : '登录' }}</h1>
    <el-form label-width="80px" @submit.prevent="handleSubmit">
      <el-form-item label="账号">
        <el-input v-model="form.username" placeholder="输入用户名"></el-input>
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" placeholder="输入密码"></el-input>
      </el-form-item>
      <el-form-item v-if="isRegister" label="昵称">
        <el-input v-model="form.nickname" placeholder="输入昵称（选填）"></el-input>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" class="login-btn" :loading="loading" @click="handleSubmit">
          {{ isRegister ? '注册' : '登录' }}
        </el-button>
        <el-button text type="info" @click="isRegister = !isRegister">
          {{ isRegister ? '已有账号？去登录' : '没有账号？去注册' }}
        </el-button>
      </el-form-item>
    </el-form>
  </div>
</div>
</template>
<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { setCurrentUser, syncFavoritesFromServer } from '../utils/storage'

const router = useRouter()
const loading = ref(false)
const isRegister = ref(false)
const form = reactive({ username: '', password: '', nickname: '' })

const handleSubmit = async () => {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }

  loading.value = true
  try {
    if (isRegister.value) {
      // 注册
      const res = await api.post('/auth/register', {
        username: form.username,
        password: form.password,
        nickname: form.nickname || form.username,
      })
      const { id, username, nickname, token } = res.data
      setCurrentUser({ id, username, nickname }, token)
      ElMessage.success('注册成功')
    } else {
      // 登录
      const res = await api.post('/auth/login', {
        username: form.username,
        password: form.password,
      })
      const { id, username, nickname, token } = res.data
      setCurrentUser({ id, username, nickname }, token)
      // 同步后端收藏列表到本地，避免显示上一个用户的收藏
      await syncFavoritesFromServer(token)
      ElMessage.success('登录成功')
    }
    router.push('/')
  } catch (error) {
    const msg = error.response?.data?.detail || '操作失败，请重试'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>
<style scoped>
.login-wrap{
  width:100%;
  min-height:70vh;
  display:flex;
  align-items:center;
  justify-content:center;
  padding:40px 20px;
}
.login-card{
  width:420px;
  max-width:100%;
  padding:40px;
  background:#fff;
  border-radius:16px;
  border:1px solid var(--bili-border);
  box-shadow:0 8px 30px rgba(0,0,0,0.08);
}
.title{
  text-align:center;
  color:var(--bili-text);
  margin-bottom:30px;
  letter-spacing:2px;
}
:deep(.el-form-item__label){
  color:var(--bili-text-2);
}
.login-btn{
  width:100%;
  margin-bottom:12px;
  background:var(--bili-pink);
  border:none;
}
.login-btn:hover{
  background:#fc8aab;
}
</style>
