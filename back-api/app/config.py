"""集中管理配置：密钥/数据库/跨域来源等都从项目内 .env 读取，不依赖系统环境变量。

.env 文件不会被提交（见 .gitignore）。若 .env 不存在，则使用下方默认值，保证项目开箱即用。
"""
import os


def _load_dotenv(path: str = ".env") -> None:
    """极简 .env 解析：仅对进程内 os.environ 赋值（不修改系统环境变量）。"""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass


_load_dotenv()

# ---- JWT ----
JWT_SECRET = os.getenv("JWT_SECRET", "media_recommend_secret_key_2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "7"))

# ---- 数据库 ----
DB_USER = os.getenv("DB_USER", "root")
DB_PWD = os.getenv("DB_PWD", "123456")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "media_recommend")

# ---- 跨域：允许的前端来源（逗号分隔）----
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]
