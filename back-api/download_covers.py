"""
在【主机】运行（需挂 VPN，否则连不到 lain.bgm.tv）。
读取 media_enriched.csv 里的封面 URL，下载到本地 covers/ 目录，
并生成 covers_mapping.csv（原始URL,本地文件名），供服务器 import_covers.py 使用。

用法（在 back-api 目录下，用昨天跑 enrich 的同一环境，例如 venv_back）：
    python download_covers.py
"""
import csv
import hashlib
import os
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_IN = os.path.join(HERE, "media_enriched.csv")
COVERS_DIR = os.path.join(HERE, "covers")
MAP_OUT = os.path.join(HERE, "covers_mapping.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://bgm.tv/",
}


def local_filename(url):
    ext = os.path.splitext(url.split("?")[0])[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".jpg"
    return f"{hashlib.md5(url.encode('utf-8')).hexdigest()}{ext}"


def main():
    os.makedirs(COVERS_DIR, exist_ok=True)
    rows = list(csv.DictReader(open(CSV_IN, encoding="utf-8")))
    print(f"读取 {len(rows)} 条，开始下载到 {COVERS_DIR}")

    mapping = []
    ok = skip = fail = 0
    for i, r in enumerate(rows, 1):
        url = (r.get("cover") or "").strip()
        if not url or not url.startswith("http"):
            continue
        sid = r.get("subject_id", "")
        fname = local_filename(url)
        fpath = os.path.join(COVERS_DIR, fname)

        if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
            skip += 1
            mapping.append((url, fname, sid))
        else:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=20)
                if resp.status_code == 200 and resp.content:
                    with open(fpath, "wb") as f:
                        f.write(resp.content)
                    ok += 1
                    mapping.append((url, fname, sid))
                else:
                    fail += 1
                    print(f"  [{resp.status_code}] 失败: {url}")
            except Exception as e:
                fail += 1
                print(f"  [ERR] {type(e).__name__}: {url}")
            time.sleep(0.1)

        if i % 200 == 0:
            print(f"进度 {i}/{len(rows)}  成功{ok} 跳过{skip} 失败{fail}")

    with open(MAP_OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["orig_url", "fname", "subject_id"])
        w.writerows(mapping)

    print(f"\n完成：下载{ok} 跳过{skip} 失败{fail}")
    print(f"图片→ {COVERS_DIR}（{len(os.listdir(COVERS_DIR))} 个文件）")
    print(f"映射→ {MAP_OUT}")


if __name__ == "__main__":
    main()
