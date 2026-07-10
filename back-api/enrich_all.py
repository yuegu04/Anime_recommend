"""批量通过 Bangumi subject_id 获取真实封面和简介，写入 media 表"""
import sys
import time
sys.path.insert(0, ".")
from app.database import SessionLocal
from app.models.media import Media
from app.metadata import fetch_metadata_by_subject_id, fetch_real_anime_metadata

db = SessionLocal()
try:
    all_media = db.query(Media).all()
    total = len(all_media)

    # 筛选需要补全的
    need_enrich = []
    for m in all_media:
        cover = str(m.cover or "")
        desc = str(m.desc or "")
        has_cover = bool(cover) and "data:image/svg+xml" not in cover and "via.placeholder.com" not in cover
        has_desc = bool(desc) and "是一部值得一看的动漫作品" not in desc
        has_tags = bool(str(m.genre_tags or "").strip())
        if not has_cover or not has_desc or not has_tags:
            need_enrich.append(m)

    need_count = len(need_enrich)
    print(f"共 {total} 条记录，{need_count} 条需要补全")

    success = 0
    fail = 0
    skip = 0
    for i, media in enumerate(need_enrich):
        try:
            name = media.name
            metadata = None

            # 通过 Bangumi subject_id 精确查
            if media.subject_id:
                metadata = fetch_metadata_by_subject_id(media.subject_id)

            # subject_id 查不到时，回退到按标题搜索
            if not metadata:
                metadata = fetch_real_anime_metadata(name)

            if not metadata:
                skip += 1
                if skip % 50 == 0:
                    print(f"[{i+1}/{need_count}] 跳过 {skip} 条，成功 {success} 条，失败 {fail} 条")
                continue

            cover = str(media.cover or "")
            desc = str(media.desc or "")
            need_cover = not cover or "data:image/svg+xml" in cover or "via.placeholder.com" in cover
            need_desc = not desc or "是一部值得一看的动漫作品" in desc
            need_tags = not str(media.genre_tags or "").strip()

            updated = False
            if need_cover and metadata.get("cover"):
                media.cover = metadata["cover"]
                updated = True
            if need_desc and metadata.get("description"):
                media.desc = metadata["description"]
                updated = True
            if need_tags and metadata.get("tags"):
                media.genre_tags = ",".join(metadata["tags"])
                updated = True

            if updated:
                db.add(media)
                db.commit()
                success += 1
                if success % 50 == 0:
                    print(f"[{i+1}/{need_count}] 已成功 {success} 条，跳过 {skip} 条，失败 {fail} 条，当前: {name}")
            else:
                skip += 1

            time.sleep(0.3)  # Bangumi API 限流，间隔 0.3 秒
        except Exception as e:
            fail += 1
            db.rollback()
            time.sleep(1)
            if fail % 10 == 0:
                print(f"[{i+1}/{need_count}] 失败 {fail} 条，错误: {e}")

    print(f"\n完成！成功 {success} 条，跳过 {skip} 条，失败 {fail} 条")
finally:
    db.close()
