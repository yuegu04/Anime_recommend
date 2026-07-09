import base64
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.media import Media
from app.recommend import recommender
from app.redis_cache import get_cache, set_cache
from app.metadata import enrich_media_record, _is_placeholder_cover, _is_placeholder_desc
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter(tags=["recommendation"])

# ---- 标签分类映射 ----
# 类型代码 -> 中文大类（Bangumi 类型：2=动画 4=游戏 3=音乐 6=三次元 1=书籍）
TYPE_CODE_MAP = {
    "2": "动漫",
    "4": "游戏",
    "3": "音乐",
    "6": "日剧",
    "1": None,  # 书籍，按子类型细分
}
# 仅保留这些常见形式子类型作为标签，过滤掉无意义的（游戏/其他/扩展包等）
FORM_SUBTYPES = {
    "TV", "OVA", "剧场版", "WEB", "电影", "日剧", "欧美剧",
    "华语剧", "漫画", "小说", "动态漫画", "电视剧",
}


def _classify_tags(tags) -> set:
    """把 DB 里的 `类型,子类型,年份` 解析成易懂的中文分类标签集合"""
    parts = [p.strip() for p in str(tags).split(",") if p.strip()]
    if not parts:
        return set()
    code = parts[0]
    subtype = parts[1] if len(parts) > 1 else ""
    labels = set()
    if code in TYPE_CODE_MAP:
        big = TYPE_CODE_MAP[code]
        if big is None:
            # 类型1 书籍：按子类型细分
            if subtype == "漫画":
                labels.add("漫画")
            elif subtype == "小说":
                labels.add("小说")
            else:
                labels.add("书籍")
        else:
            labels.add(big)
    if subtype in FORM_SUBTYPES:
        labels.add(subtype)
    labels.discard("")
    return labels


def _apply_tag_filter(query, tag: str):
    """根据中文分类标签反查并过滤（兼容大类与子类型）"""
    code_map = {v: k for k, v in TYPE_CODE_MAP.items() if v}
    if tag in code_map:
        code = code_map[tag]
        return query.filter(Media.tags.like(f"{code},%"))
    # 子类型匹配（带逗号防止误匹配，如“电视剧”不会误命中“日剧”的年月）
    return query.filter(Media.tags.like(f"%,{tag},%"))


def _build_cover_image(name: str, tags: str = ""):
    safe_name = (name or "动漫").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_tags = (tags or "推荐").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='800' height='1120'>
      <rect width='100%' height='100%' fill='#1f163d'/>
      <rect x='32' y='32' width='736' height='1056' rx='36' fill='url(#g)'/>
      <circle cx='620' cy='240' r='180' fill='rgba(255,255,255,0.16)'/>
      <text x='64' y='300' fill='#ffffff' font-size='56' font-family='Microsoft YaHei, Arial, sans-serif'>{safe_name}</text>
      <text x='64' y='380' fill='#ffe0ef' font-size='26' font-family='Microsoft YaHei, Arial, sans-serif'>{safe_tags}</text>
      <text x='64' y='980' fill='#ffffff' font-size='34' font-family='Microsoft YaHei, Arial, sans-serif'>动漫推荐</text>
      <defs><linearGradient id='g' x1='0%' y1='0%' x2='100%' y2='100%'><stop offset='0%' stop-color='#ff8bc5'/><stop offset='100%' stop-color='#6f5cff'/></linearGradient></defs>
    </svg>"""
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode('utf-8')).decode('ascii')}"


def _read_media_from_csv():
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "filtered_anime.csv")
    if not os.path.exists(csv_path):
        return []

    import pandas as pd

    # 违禁词和排除类型，与 import_media.py 保持一致
    forbidden_keywords = ["乳", "淫", "色情", "性"]
    exclude_types = ["游戏", "扩展包", "桌游"]

    df = pd.read_csv(csv_path, encoding="gbk")
    df.columns = df.columns.str.strip()
    items = []
    for idx, row in df.iterrows():
        sub_type = str(row.get("子类型", ""))
        if sub_type in exclude_types:
            continue

        name = row.get("中文标题") or row.get("标题") or str(row.get("subject", ""))
        name_str = str(name).strip()
        if not name_str:
            continue
        if any(kw in name_str for kw in forbidden_keywords):
            continue

        score = row.get("VIB评分", 0)
        tags = ",".join([str(x) for x in [row.get("类型", ""), row.get("子类型", ""), row.get("年份", "")] if str(x).strip()])
        year = row.get("年份数值") if "年份数值" in df.columns else row.get("年份")
        try:
            media_id = int(row.get("subject", idx + 1))
        except Exception:
            media_id = idx + 1
        safe_name = str(name) if str(name).strip() else f"动漫 {media_id}"
        safe_tags = str(tags) if str(tags).strip() else "热门作品"
        desc = f"《{safe_name}》是一部值得一看的动漫作品，标签包括 {safe_tags}。"
        items.append({
            "id": media_id,
            "name": safe_name,
            "cover": _build_cover_image(safe_name, safe_tags),
            "score": float(score) if str(score).replace(".", "", 1).isdigit() else 0.0,
            "tags": safe_tags,
            "desc": desc,
            "year": year,
        })
    return items


def _normalize_media_items(items, db=None, enrich=False):
    """将 media 对象列表转为 dict 列表。
    enrich=True 时才尝试获取远程元数据（仅限详情页等少量场景），列表接口传 False 以快速返回。"""
    payload = []
    for item in items:
        media_name = item.name if hasattr(item, "name") else item.get("name")
        cover = item.cover if hasattr(item, "cover") else item.get("cover", "")
        desc = item.desc if hasattr(item, "desc") else item.get("desc", "")

        if enrich and db is not None and hasattr(item, "id"):
            if _is_placeholder_cover(cover) or _is_placeholder_desc(desc):
                try:
                    enrich_media_record(item, db=db)
                    cover = item.cover
                    desc = item.desc
                except Exception:
                    pass

        payload.append({
            "id": item.id if hasattr(item, "id") else item.get("id"),
            "name": media_name,
            "cover": cover,
            "score": float(item.score if hasattr(item, "score") else item.get("score", 0) or 0),
            "tags": item.tags if hasattr(item, "tags") else item.get("tags", ""),
            "desc": desc,
            "year": item.year if hasattr(item, "year") else item.get("year"),
        })
    return payload


def _filter_media_items(items, search: str = "", tag: str = ""):
    filtered = []
    keyword = (search or "").strip().lower()
    selected_tag = (tag or "").strip().lower()
    for item in items:
        name = str(item.get("name") or "")
        tags = str(item.get("tags") or "")
        desc = str(item.get("desc") or "")
        if keyword and keyword not in name.lower() and keyword not in tags.lower() and keyword not in desc.lower():
            continue
        if selected_tag and selected_tag != "全部" and selected_tag not in tags.lower():
            continue
        filtered.append(item)
    return filtered


@router.get("/media/list")
def list_media(
    search: Optional[str] = Query(default=""),
    tag: Optional[str] = Query(default=""),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """获取动漫列表，支持搜索与标签筛选、分页，并在数据库不可用时自动回退到本地 CSV 数据。"""
    # 输入校验：防止异常/超大参数
    search = (search or "").strip()[:50]
    tag = (tag or "").strip()[:20]
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))

    try:
        query = db.query(Media)
        if search:
            keyword = f"%{search}%"
            query = query.filter(or_(Media.name.ilike(keyword), Media.tags.ilike(keyword), Media.desc.ilike(keyword)))
        if tag and tag != "全部":
            query = _apply_tag_filter(query, tag)
        query = query.order_by(Media.score.desc(), Media.id.asc())
        items = query.limit(limit).offset(offset).all()
        payload = _normalize_media_items(items, db=db, enrich=False)
        if payload:
            labels = set()
            for item in payload:
                labels.update(_classify_tags(item["tags"]))
            tags = sorted(labels, key=str.lower)
            return {"items": payload, "tags": tags, "total": len(payload)}
    except Exception:
        pass

    fallback_items = _read_media_from_csv()
    filtered_items = _filter_media_items(fallback_items, search=search, tag=tag)
    payload = filtered_items[offset:offset + limit]
    labels = set()
    for item in payload:
        labels.update(_classify_tags(item.get("tags", "")))
    tags = sorted(labels, key=str.lower)
    return {"items": payload, "tags": tags, "total": len(payload)}


def _invalidate_recommend_cache(user_id: int):
    """清除该用户的推荐缓存，使行为变更后立即生效。"""
    for n in (8, 10, 12, 20):
        set_cache(f"recommend:{user_id}:{n}", None, ttl=1)


@router.post("/recommend/behavior")
def record_behavior(
    media_id: int,
    score: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """记录用户行为（收藏/评分），需要登录。"""
    from app.models.rating import Rating

    # 输入校验
    media_id = int(media_id)
    score = float(score)

    # 检查是否已有记录，有则更新分数，无则新增
    existing = (
        db.query(Rating)
        .filter(Rating.user_id == current_user.id, Rating.media_id == media_id)
        .first()
    )
    if existing:
        existing.score = score
        db.commit()
        _invalidate_recommend_cache(current_user.id)
        return {"msg": "behavior updated", "data": {"id": existing.id}}

    record = Rating(user_id=current_user.id, media_id=media_id, score=score)
    db.add(record)
    db.commit()
    db.refresh(record)
    _invalidate_recommend_cache(current_user.id)
    return {"msg": "behavior recorded", "data": {"id": record.id}}


@router.get("/recommend/list")
def get_recommendations(
    user_id: str = Query(default="want"),
    top_n: int = 10,
    db: Session = Depends(get_db),
    authorization: str = Header(None),
):
    """根据用户 ID 获取推荐列表。如果用户已登录，优先使用真实用户 ID。"""
    top_n = max(1, min(int(top_n), 50))
    # 如果已登录，使用真实用户 ID
    actual_user_id = user_id
    if authorization:
        try:
            from app.routers.auth import decode_token

            scheme, token = authorization.split(" ", 1)
            if scheme.lower() == "bearer":
                payload = decode_token(token)
                actual_user_id = str(payload["user_id"])
        except Exception:
            pass

    cache_key = f"recommend:{actual_user_id}:{top_n}"
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    # 已登录的真实用户走个性化推荐；未登录/虚拟用户走通用推荐
    if authorization and actual_user_id.isdigit():
        try:
            results = recommender.recommend_for_user(int(actual_user_id), db, top_n=top_n)
        except Exception:
            results = []
        # 冷启动（暂无行为）回退到 doing 通用推荐
        if not results:
            results = recommender.recommend(user_id="doing", top_n=top_n)
    else:
        results = recommender.recommend(user_id=actual_user_id, top_n=top_n)

    if not results:
        payload = {"user_id": actual_user_id, "items": []}
        set_cache(cache_key, payload, ttl=60)
        return payload

    media_names = [item["item"] for item in results]
    items = db.query(Media).filter(Media.name.in_(media_names)).all()
    media_map = {item.name: item for item in items}

    payload = []
    for item in results:
        media = media_map.get(item["item"])
        if media and (not str(media.cover or "").strip() or not str(media.desc or "").strip()):
            enrich_media_record(media, db=db)
        payload.append({
            "name": item["item"],
            "score": item["score"],
            "media_id": media.id if media else None,
            "cover": media.cover if media else "",
            "tags": media.tags if media else "",
            "desc": media.desc if media else "",
        })

    response = {"user_id": actual_user_id, "items": payload}
    # 登录用户的结果缓存较短，保证个性化相对及时
    ttl = 120 if (authorization and actual_user_id.isdigit()) else 300
    set_cache(cache_key, response, ttl=ttl)
    return response


@router.get("/recommend/{media_id}")
def get_media_detail(media_id: int, db: Session = Depends(get_db)):
    try:
        media = db.query(Media).filter(Media.id == media_id).first()
        if media:
            if not str(media.cover or "").strip() or not str(media.desc or "").strip():
                enrich_media_record(media, db=db)
            return {
                "id": media.id,
                "name": media.name,
                "cover": media.cover,
                "score": media.score,
                "tags": media.tags,
                "desc": media.desc,
                "year": media.year,
            }
    except Exception:
        pass

    fallback_items = _read_media_from_csv()
    media = next((item for item in fallback_items if int(item.get("id", 0)) == media_id), None)
    if not media:
        raise HTTPException(status_code=404, detail="media not found")

    return {
        "id": media.get("id"),
        "name": media.get("name"),
        "cover": media.get("cover", ""),
        "score": media.get("score", 0),
        "tags": media.get("tags", ""),
        "desc": media.get("desc", ""),
        "year": media.get("year"),
    }
