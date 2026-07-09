import os
import redis
import json

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    client.ping()
    print("Redis连接成功")
except Exception as e:
    print("Redis未启动或不可用", e)
    client = None


def get_cache(key: str):
    if client is None:
        return None
    try:
        value = client.get(key)
        if value:
            return json.loads(value)
    except Exception:
        return None
    return None


def set_cache(key: str, value, ttl: int = 300):
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
    except Exception:
        pass
