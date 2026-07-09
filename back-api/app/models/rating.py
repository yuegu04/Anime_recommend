from sqlalchemy import Column, Integer, Float, DateTime, UniqueConstraint
from datetime import datetime
from app.database import Base

class Rating(Base):
    __tablename__ = "rating"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    media_id = Column(Integer, nullable=False)
    score = Column(Float, nullable=False)
    create_time = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("user_id", "media_id", name="uq_user_media"),
    )