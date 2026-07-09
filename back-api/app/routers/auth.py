"""用户认证路由：注册、登录、个人信息"""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_DAYS
from app.models.user import User
from app.models.rating import Rating

router = APIRouter(tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    nickname: str = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    nickname: str
    token: str = ""


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user_id: int, username: str) -> str:
    """生成 JWT token"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解析 JWT token，返回 payload"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token 已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="token 无效，请重新登录")


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """从请求头中解析当前登录用户"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证信息")
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="认证格式错误")
    except ValueError:
        raise HTTPException(status_code=401, detail="认证格式错误")

    payload = decode_token(token)
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


@router.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(req.username) < 2 or len(req.username) > 50:
        raise HTTPException(status_code=400, detail="用户名长度需在 2-50 之间")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="密码长度至少 4 位")

    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=req.username,
        password=hash_password(req.password),
        nickname=req.nickname or req.username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.username)
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "token": token,
    }


@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录"""
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if not verify_password(req.password, user.password):
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    token = create_token(user.id, user.username)
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "token": token,
    }


@router.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "nickname": current_user.nickname,
    }


@router.get("/auth/favorites")
def get_my_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的收藏列表（基于评分记录）"""
    from app.models.media import Media

    ratings = (
        db.query(Rating, Media)
        .join(Media, Rating.media_id == Media.id)
        .filter(Rating.user_id == current_user.id)
        .order_by(Rating.create_time.desc())
        .all()
    )
    items = []
    for rating, media in ratings:
        items.append({
            "id": media.id,
            "name": media.name,
            "cover": media.cover,
            "score": media.score,
            "tags": media.tags,
            "desc": media.desc,
            "year": media.year,
            "my_score": rating.score,
            "create_time": rating.create_time.isoformat() if rating.create_time else None,
        })
    return {"items": items}
