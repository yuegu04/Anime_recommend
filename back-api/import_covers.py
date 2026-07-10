"""
在【服务器】运行。读取主机传来的 covers_mapping.csv（orig_url,fname,subject_id），
把库里 cover 等于 orig_url 的记录改为本地路径 /covers/<fname>，由 Nginx 直出。

用法：
    cd /opt/anime/back-api && source venv/bin/activate
    COVERS_DIR=/var/www/covers python import_covers.py
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.media import Media

HERE = os.path.dirname(os.path.abspath(__file__))
MAP_CSV = os.path.join(HERE, "covers_mapping.csv")
URL_PREFIX = "/covers"
COVERS_DIR = os.getenv("COVERS_DIR", "/var/www/covers")


def main():
    if not os.path.exists(MAP_CSV):
        print(f"找不到 {MAP_CSV}，请先把主机的 covers_mapping.csv 传过来")
        return

    # 原始 URL -> /covers/fname
    mapping = {}
    for r in csv.DictReader(open(MAP_CSV, encoding="utf-8")):
        url = (r.get("orig_url") or "").strip()
        fname = (r.get("fname") or "").strip()
        if url and fname:
            mapping[url] = f"{URL_PREFIX}/{fname}"

    print(f"映射表 {len(mapping)} 条，开始按原始 URL 更新库...")

    db = SessionLocal()
    updated = missing_file = no_match = 0
    try:
        rows = db.query(Media).filter(Media.cover.like("http%")).all()
        for media in rows:
            url = media.cover.strip()
            rel = mapping.get(url)
            if not rel:
                no_match += 1
                continue
            fname = os.path.basename(rel)
            if not os.path.exists(os.path.join(COVERS_DIR, fname)):
                missing_file += 1
                continue
            media.cover = rel
            updated += 1
        db.commit()
        print(f"\n完成：更新 {updated} 条")
        print(f"未匹配(库里URL不在映射中) {no_match} 条")
        print(f"映射有但本地缺图(未传covers目录?) {missing_file} 条")
        print(f"提示：本地封面数 = {len(os.listdir(COVERS_DIR))}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
