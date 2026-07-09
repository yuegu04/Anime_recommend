"""从 Bangumi API 获取动漫元数据（封面、简介）"""
import re
import time
from typing import Optional

import requests

BANGUMI_API = "https://api.bgm.tv/v0"


def _strip_html(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"<[^>]+>", "", str(value)).strip()


def _build_cover_url(image_path: Optional[str]) -> str:
    """拼接封面完整 URL"""
    if not image_path:
        return ""
    # Bangumi 图片路径需要拼接 base URL
    if image_path.startswith("http"):
        return image_path
    return f"https://lain.bgm.tv{image_path}"


def _is_placeholder_cover(cover: Optional[str]) -> bool:
    """判断封面是否是占位图"""
    if not cover or not str(cover).strip():
        return True
    cover_str = str(cover)
    if "data:image/svg+xml" in cover_str:
        return True
    if "via.placeholder.com" in cover_str:
        return True
    return False


def _is_placeholder_desc(desc: Optional[str]) -> bool:
    """判断简介是否是自动生成的占位文本"""
    if not desc or not str(desc).strip():
        return True
    desc_str = str(desc)
    if "是一部值得一看的动漫作品" in desc_str:
        return True
    if "是一部由公开动漫资料库记录的作品" in desc_str:
        return True
    return False


def fetch_metadata_by_subject_id(subject_id: int) -> Optional[dict]:
    """通过 Bangumi 作品 ID 获取精确元数据（封面、简介）"""
    if not subject_id:
        return None

    url = f"{BANGUMI_API}/subjects/{subject_id}"
    try:
        response = requests.get(url, timeout=15, headers={
            "User-Agent": "media-recommend/1.0 (personal project)"
        })
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()

        # 封面
        images = data.get("images") or {}
        cover_path = images.get("large") or images.get("medium") or images.get("common") or ""
        cover = _build_cover_url(cover_path)

        # 简介
        desc = _strip_html(data.get("summary")) or ""

        # 真实题材标签（Bangumi 返回 [{name, count, type}]）
        tag_list = data.get("tags") or []
        tags = [t.get("name") for t in tag_list if isinstance(t, dict) and t.get("name")]

        # 标题（优先中文名）
        title = data.get("name_cn") or data.get("name") or ""

        return {
            "title": title,
            "cover": cover,
            "description": desc,
            "tags": tags,
            "source": "bangumi",
        }
    except Exception:
        return None


def fetch_real_anime_metadata(title: str) -> Optional[dict]:
    """通过搜索获取元数据（备用方案）"""
    if not title:
        return None

    url = f"{BANGUMI_API}/search/subject/{requests.utils.quote(title)}"
    params = {
        "type": 2,  # 类型=动画
        "responseGroup": "small",
        "max_results": 5,
    }
    try:
        response = requests.get(url, params=params, timeout=15, headers={
            "User-Agent": "media-recommend/1.0 (personal project)"
        })
        response.raise_for_status()
        data = response.json()
        results = data.get("list") or []

        if not results:
            return None

        # 取第一个结果
        best = results[0]
        sid = best.get("id")
        if sid:
            return fetch_metadata_by_subject_id(sid)

        return None
    except Exception:
        return None


def enrich_media_record(media, db=None) -> bool:
    """如果媒体记录缺少真实封面或简介，则从 Bangumi 补齐"""
    if not media:
        return False

    cover = str(getattr(media, "cover", "") or "")
    desc = str(getattr(media, "desc", "") or "")

    need_cover = not cover or "data:image/svg+xml" in cover or "via.placeholder.com" in cover
    need_desc = not desc or "是一部值得一看的动漫作品" in desc or "是一部由公开动漫资料库记录的作品" in desc
    need_tags = not getattr(media, "genre_tags", None)

    if not need_cover and not need_desc and not need_tags:
        return False

    # 优先用 subject_id 精确查
    subject_id = getattr(media, "subject_id", None)
    metadata = None
    if subject_id:
        metadata = fetch_metadata_by_subject_id(subject_id)

    # 没有 subject_id 或 ID 查不到时，回退到搜索
    if not metadata:
        name = getattr(media, "name", "") or ""
        metadata = fetch_real_anime_metadata(name)

    if not metadata:
        return False

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

    if updated and db is not None:
        try:
            db.add(media)
            db.commit()
            db.refresh(media)
        except Exception:
            db.rollback()
            return False

    return updated
