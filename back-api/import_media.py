"""将 filtered_anime.csv 导入到 MySQL media 表"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from app.database import SessionLocal, engine, Base
from app.models.media import Media

# 确保表存在
Base.metadata.create_all(bind=engine)

csv_path = os.path.join(os.path.dirname(__file__), "filtered_anime.csv")
df = pd.read_csv(csv_path, encoding="gbk")
df.columns = df.columns.str.strip()

# 过滤：剔除子类型=游戏，扩展包，桌游的数据
exclude_types = ["游戏", "扩展包", "桌游"]

# 过滤：标题中包含以下关键词的作品会被跳过
forbidden_keywords = ["乳", "淫", "色情", "性"]


def has_forbidden_keyword(title):
    if pd.isna(title):
        return False
    title_str = str(title).strip()
    return any(keyword in title_str for keyword in forbidden_keywords)


db = SessionLocal()
try:
    count = 0
    for idx, row in df.iterrows():
        # 子类型过滤
        sub_type = str(row.get("子类型", ""))
        if sub_type in exclude_types:
            continue

        name = str(row.get("中文标题") or row.get("标题") or row.get("subject", "")).strip()
        if not name:
            continue

        # 标题关键词过滤
        if has_forbidden_keyword(name):
            continue

        # 检查是否已存在
        existing = db.query(Media).filter(Media.name == name).first()
        if existing:
            continue

        vib_score = pd.to_numeric(row.get("VIB评分", 0), errors="coerce")
        tags_parts = [str(x).strip() for x in [row.get("类型", ""), row.get("子类型", ""), row.get("年份", "")] if str(x).strip()]
        tags = ",".join(tags_parts)
        year = row.get("年份数值") if "年份数值" in df.columns else row.get("年份")
        try:
            year = int(float(year)) if pd.notna(year) else None
        except (ValueError, TypeError):
            year = None

        desc = f"《{name}》是一部值得一看的动漫作品。"
        cover = ""  # 留空，让 metadata 模块自动获取

        # 提取 AniList subject ID
        subject_id = None
        try:
            sid = pd.to_numeric(row.get("subject"), errors="coerce")
            subject_id = int(sid) if pd.notna(sid) else None
        except (ValueError, TypeError):
            pass

        media = Media(
            name=name,
            cover=cover,
            score=float(vib_score) if not pd.isna(vib_score) else 0.0,
            tags=tags,
            desc=desc,
            year=year,
            subject_id=subject_id,
        )
        db.add(media)
        count += 1
        if count % 500 == 0:
            db.commit()
            print(f"已导入 {count} 条...")

    db.commit()
    print(f"导入完成，共 {count} 条记录！")
finally:
    db.close()
