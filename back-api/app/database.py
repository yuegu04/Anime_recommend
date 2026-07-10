# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

from app.config import DB_USER, DB_PWD, DB_HOST, DB_PORT, DB_NAME

# 数据库连接地址
# 密码经 URL 编码，避免密码中包含 @、:、/、% 等特殊字符时破坏连接串解析
SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PWD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建数据库引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True  # 自动检测连接失效重连
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 所有模型的基类
Base = declarative_base()

# 获取数据库会话依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()