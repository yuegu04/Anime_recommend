"""在【服务器】运行：读取 media_enriched.csv，按作品名 UPDATE 服务器 media 表。
用 name 做键（非 id），保留服务器原有 id 与评分记录；只升级不降级。
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.metadata import _is_placeholder_cover, _is_placeholder_desc
from app.models.media import Media

SRC = os.path.join(os.path.dirname(__file__), "media_enriched.csv")


def main():
    if not os.path.exists(SRC):
        print(f"找不到 {SRC}，请先把主机的 media_enriched.csv 传到该目录")
        return

    db = SessionLocal()
    try:
        updated = 0
        with open(SRC, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    continue
                media = db.query(Media).filter(Media.name == name).first()
                if not media:
                    continue

                host_cover = (row.get("cover") or "").strip()
                host_desc = (row.get("desc") or "").strip()
                host_tags = (row.get("genre_tags") or "").strip()
                host_sid = (row.get("subject_id") or "").strip()
                host_year = (row.get("year") or "").strip()

                # 只升级：主机有真实数据才覆盖，避免用占位文本覆盖现有内容
                if host_cover and not _is_placeholder_cover(host_cover):
                    media.cover = host_cover
                if host_desc and not _is_placeholder_desc(host_desc):
                    media.desc = host_desc
                if host_tags:
                    media.genre_tags = host_tags
                if host_sid:
                    try:
                        media.subject_id = int(host_sid)
                    except (ValueError, TypeError):
                        pass
                if host_year:
                    try:
                        media.year = int(host_year)
                    except (ValueError, TypeError):
                        pass

                updated += 1
                if updated % 500 == 0:
                    db.commit()
                    print(f"已更新 {updated} 条...")

            db.commit()
        print(f"完成，共更新 {updated} 条")
    finally:
        db.close()


if __name__ == "__main__":
    main()
