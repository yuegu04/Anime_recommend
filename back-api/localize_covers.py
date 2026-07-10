"""
办法 B：把远程 Bangumi 封面（lain.bgm.tv）下载到服务器本地，改库指向本地路径，
由 Nginx 直接静态返回，绕过 lain.bgm.tv 的防盗链（Referer 校验）。

在服务器上运行：
    cd /opt/anime/back-api && source venv/bin/activate
    COVERS_DIR=/var/www/covers python localize_covers.py

- 只处理 cover 以 http 开头的记录（已本地化的 /covers/... 会自动跳过）
- 幂等：图片文件已存在则不重复下载；中断后可重跑
- 下载失败的记录保留原 URL，不影响其它
"""
import hashlib
import os
import sys
import time

import requests

from app.database import SessionLocal
from app.models.media import Media

# 图片落地目录（需与 Nginx 的 location /covers/ 对应）
COVERS_DIR = os.getenv("COVERS_DIR", "/var/www/covers")
# 库里保存的相对访问路径前缀
URL_PREFIX = "/covers"

# 下载请求头：带 Referer 通过 lain.bgm.tv 的防盗链
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://bgm.tv/",
}


def is_remote(url: str) -> bool:
    return bool(url) and url.strip().lower().startswith("http")


def local_filename(url: str) -> str:
    """用 URL 的 md5 + 原扩展名生成唯一文件名，保证幂等且不冲突。"""
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".jpg"
    h = hashlib.md5(url.encode("utf-8")).hexdigest()
    return f"{h}{ext}"


def main():
    os.makedirs(COVERS_DIR, exist_ok=True)

    db = SessionLocal()
    ok = skip = fail = 0
    try:
        rows = db.query(Media).filter(Media.cover.like("http%")).all()
        total = len(rows)
        print(f"待处理远程封面 {total} 条，落地目录 {COVERS_DIR}")

        for i, media in enumerate(rows, 1):
            url = media.cover.strip()
            if not is_remote(url):
                skip += 1
                continue

            fname = local_filename(url)
            fpath = os.path.join(COVERS_DIR, fname)
            rel = f"{URL_PREFIX}/{fname}"

            # 文件已存在 → 只改库，不重复下载
            if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
                media.cover = rel
                db.commit()
                skip += 1
            else:
                try:
                    resp = requests.get(url, headers=HEADERS, timeout=20, stream=True)
                    if resp.status_code == 200 and resp.content:
                        with open(fpath, "wb") as f:
                            f.write(resp.content)
                        media.cover = rel
                        db.commit()
                        ok += 1
                    else:
                        fail += 1
                        print(f"  [{resp.status_code}] 下载失败，保留原URL: {url}")
                except Exception as e:
                    fail += 1
                    print(f"  [ERR] {type(e).__name__} 保留原URL: {url}")
                time.sleep(0.15)  # 轻微限速，避免被封

            if i % 200 == 0:
                print(f"进度 {i}/{total}  成功{ok} 跳过{skip} 失败{fail}")

        print(f"\n完成：成功下载 {ok}，跳过 {skip}（已存在/已本地化），失败 {fail}")
        print(f"图片已存到 {COVERS_DIR}，库中 cover 已指向 {URL_PREFIX}/...")
    finally:
        db.close()


if __name__ == "__main__":
    main()
