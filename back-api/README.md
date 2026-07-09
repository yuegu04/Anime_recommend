# 动漫推荐系统 · 后端

FastAPI + MySQL + Redis 的动漫推荐服务。推荐使用 ALS 协同过滤（`implicit`），
支持虚拟用户（want/doing/done）通用推荐与登录用户的个性化推荐（fold-in 即时预测）。

## 目录结构

```
app/
  main.py             # 入口：FastAPI 实例、CORS、日志
  config.py           # 配置中心（密钥/数据库/跨域，读 .env）
  database.py         # SQLAlchemy 引擎与会话
  recommend.py        # ALS 模型训练与推荐核心
  metadata.py         # Bangumi 元数据补全（封面/简介）
  redis_cache.py      # Redis 缓存（不可用时自动降级）
  models/             # ORM 模型：User / Media / Rating
  routers/
    auth.py           # 注册/登录/收藏
    recommendation.py # 列表/推荐/详情/行为接口
filtered_anime.csv    # 训练数据源（Bangumi 导出）
```

## 快速开始

1. 创建并使用虚拟环境（项目内已附 `venv_back`，可直接复用）：
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. 准备 MySQL 数据库 `media_recommend`，确保 `user/media/rating` 表已建（模型含唯一约束）。
3. （可选）在项目根目录创建 `.env` 覆盖默认配置：
   ```ini
   JWT_SECRET=你的随机密钥
   DB_PWD=你的密码
   CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```
4. 启动：
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 接口概览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录（返回 token） |
| GET  | `/auth/me` | 当前用户 |
| GET  | `/auth/favorites` | 我的收藏 |
| GET  | `/media/list` | 动漫列表（支持 search/tag/分页 offset） |
| GET  | `/recommend/list` | 推荐（带 token 走个性化） |
| GET  | `/recommend/{id}` | 详情 |
| POST | `/recommend/behavior` | 记录收藏/评分（需登录） |

## 说明

- **Redis 非必须**：未启动 Redis 时缓存自动降级，功能正常仅略慢。
- **推荐个性化**：登录用户基于其在 `rating` 表的收藏/评分做 fold-in 预测；
  新用户无行为时回退到 `doing` 通用推荐（冷启动）。
- **封面补全**：数据来自 Bangumi API，需运行 `enrich_all.py` 批量补全。
