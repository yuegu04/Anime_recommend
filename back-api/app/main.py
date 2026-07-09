import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.routers.recommendation import router as recommendation_router
from app.routers.auth import router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("media_recommend")

app = FastAPI(title="智能推荐系统", version="1.0")

# 显式列出允许的前端来源，避免 allow_origins=["*"] 与凭据模式冲突导致跨域被浏览器拦截
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(recommendation_router)

@app.get("/")
def index():
    return {"msg": "推荐系统后端服务运行正常"}