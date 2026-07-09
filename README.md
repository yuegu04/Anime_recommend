# 动漫推荐系统（Anime Recommend）

一个基于用户行为与内容特征的**动漫推荐全栈应用**。前端采用 bilibili 风格 UI，后端基于 FastAPI + MySQL + Redis，推荐引擎融合 **ALS 协同过滤** 与 **内容特征**（纯内容召回兜底），支持注册登录、收藏评分、个性化推荐与搜索筛选。

> 在线仓库：https://github.com/yuegu04/Anime_recommend

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Vite + Vue Router + Element Plus + Axios |
| 后端 | FastAPI + Uvicorn + SQLAlchemy + PyMySQL |
| 推荐 | `implicit`(ALS) 协同过滤 + Pandas/NumPy 内容特征 |
| 存储 | MySQL（主库）+ Redis（缓存，可选） |
| 认证 | JWT（PyJWT）+ bcrypt 密码加密 |

---

## 目录结构

```
media_recommend/
├── back-api/              # 后端服务
│   ├── app/               # FastAPI 应用
│   │   ├── main.py        # 入口：应用实例、CORS、日志
│   │   ├── config.py      # 配置中心（读 .env）
│   │   ├── database.py    # SQLAlchemy 引擎与会话
│   │   ├── recommend.py   # ALS 训练与推荐核心
│   │   ├── metadata.py    # Bangumi 元数据补全（封面/简介）
│   │   ├── redis_cache.py # Redis 缓存（不可用自动降级）
│   │   ├── models/        # ORM：User / Media / Rating
│   │   └── routers/       # auth.py（注册登录收藏）、recommendation.py（列表/推荐/详情/行为）
│   ├── sql/               # SQL 脚本
│   ├── enrich_all.py      # 批量补全媒体元数据
│   ├── import_media.py    # 导入媒体数据
│   ├── train_als.py       # 训练 ALS 模型
│   ├── requirements.txt   # Python 依赖
│   └── *.csv              # 训练/导入数据源
│
└── front-media/           # 前端应用
    ├── src/
    │   ├── App.vue        # 顶栏（居中大搜索框 b站风格）
    │   ├── views/         # home / login / usercenter / animeDetail
    │   ├── components/    # MediaCard 等
    │   ├── api/           # 后端接口封装
    │   ├── router/        # 路由
    │   └── style.css      # 全局 bilibili 主题
    ├── package.json
    └── vite.config.js
```

---

## 快速开始

### 1. 后端

```bash
cd back-api

# 创建虚拟环境（项目内已附 venv_back，可直接复用）
python -m venv venv
.\venv\Scripts\activate        # Windows

pip install -r requirements.txt

# 准备数据库：在 MySQL 中创建库 media_recommend，并确保 user/media/rating 表已建
# （模型含唯一约束，参见 sql/ 下脚本）

# 复制并修改配置（可选，不填则用 .env.example 默认值）
copy .env.example .env

# 启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端默认监听 `http://127.0.0.1:8000`。

**主要接口**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录（返回 JWT） |
| GET  | `/auth/favorites` | 我的收藏 |
| GET  | `/media/list` | 动漫列表（支持 `search` / `tag` / 分页） |
| GET  | `/recommend/list` | 推荐（带 token 走个性化） |
| GET  | `/recommend/{id}` | 详情 |
| POST | `/recommend/behavior` | 记录收藏/评分（需登录） |

### 2. 前端

```bash
cd front-media
npm install
npm run dev
```

浏览器打开 Vite 提示的地址（默认 `http://localhost:5173`）。

---

## 推荐策略

- **个性化推荐**：登录用户基于其在 `rating` 表的收藏/评分做 ALS **fold-in 即时预测**。
- **冷启动兜底**：新用户/无行为时，回退到通用推荐（`doing` 列表）或**纯内容相似召回**（基于标签/类型向量），保证有结果。
- **可降级**：Redis 未启动时缓存自动降级，功能正常仅略慢；元数据缺失时由 `enrich_all.py` 调 Bangumi API 补全封面与简介。

---

## 说明

- 虚拟环境、构建产物、`.codebuddy` 等已被 `.gitignore` 忽略，不会进入版本库。
- 数据文件（`*.csv`）已纳入仓库，可直接用于导入/训练。
- 详细后端说明见 [`back-api/README.md`](back-api/README.md)。
