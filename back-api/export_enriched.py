"""在【主机】运行：把 media 表中已补全的封面/简介按作品名导出为 media_enriched.csv。
复用 app.database 的配置（读取主机 .env），无需手动填库密码。
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models.media import Media

OUT = os.path.join(os.path.dirname(__file__), "media_enriched.csv")


def main():
    db = SessionLocal()
    try:
        rows = db.query(
            Media.name, Media.cover, Media.desc, Media.genre_tags, Media.subject_id, Media.year
        ).all()
        with open(OUT, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "cover", "desc", "genre_tags", "subject_id", "year"])
            for r in rows:
                w.writerow([
                    r.name or "",
                    r.cover or "",
                    r.desc or "",
                    r.genre_tags or "",
                    r.subject_id if r.subject_id is not None else "",
                    r.year if r.year is not None else "",
                ])
        print(f"导出完成：{len(rows)} 条 -> {OUT}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
