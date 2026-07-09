from sqlalchemy import Column, Integer, String, Float, Text
from app.database import Base

class Media(Base):
    __tablename__ = "media"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键ID")
    name = Column(String(100), nullable=False, comment="作品名称（中文优先）")
    cover = Column(Text, comment="封面图片地址")
    score = Column(Float, default=0, comment="VIB评分")
    tags = Column(String(200), comment="标签（类型/子类型/年份，中文逗号分隔）")
    desc = Column(Text, comment="作品简介")
    genre_tags = Column(Text, comment="Bangumi 真实题材标签，逗号分隔（热血/校园/治愈…）")
    year = Column(Integer, nullable=True, comment="发行年份")
    subject_id = Column(Integer, nullable=True, comment="AniList 作品 ID")
