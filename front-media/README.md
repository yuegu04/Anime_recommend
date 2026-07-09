# 动漫推荐系统 · 前端（front-media）

基于 **Vue 3 + Vite + Element Plus** 的动漫推荐前端，采用 bilibili 风格 UI（浅灰背景、`#FB7299` 主色、居中大搜索栏、白底圆角卡片）。

## 技术栈

- Vue 3（`<script setup>` SFC）
- Vite 构建
- Vue Router 路由
- Element Plus 组件库
- Axios 请求后端（`src/api`）

## 目录结构

```
src/
├── App.vue          # 顶栏（居中搜索框、我的收藏、用户菜单）
├── main.js          # 入口
├── style.css        # 全局 bilibili 主题变量
├── api/             # 后端接口封装
├── router/          # 路由配置
├── components/      # MediaCard 等组件
├── views/           # home / login / usercenter / animeDetail
└── utils/           # 本地存储等工具
```

## 开发

```bash
npm install
npm run dev        # 开发服务器（默认 http://localhost:5173）
npm run build      # 打包到 dist/
npm run preview    # 预览构建产物
```

## 对接后端

前端默认请求 `http://127.0.0.1:8000`。启动后端（`back-api`，监听 8000 端口）后，顶栏搜索、推荐、登录收藏等功能即可联调。跨域来源在后端 `CORS_ORIGINS` 中配置（`http://localhost:5173` 已默认包含）。
