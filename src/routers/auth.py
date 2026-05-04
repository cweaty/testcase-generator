"""用户认证路由"""
import logging

from fastapi import APIRouter, HTTPException, Depends

from ..models import UserRegister, UserLogin
from ..database import create_user, get_user_by_username
from ..auth import hash_password, verify_password, create_access_token, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(data: UserRegister):
    """用户注册"""
    try:
        # 检查用户名是否已存在
        existing = await get_user_by_username(data.username)
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")

        # 创建用户
        password_hash = hash_password(data.password)
        user_id = await create_user(data.username, password_hash)

        # 自动登录，返回 token
        token = create_access_token(user_id, data.username)
        logger.info(f"新用户注册: {data.username} (id={user_id})")

        return {
            "message": "注册成功",
            "token": token,
            "user": {"id": user_id, "username": data.username},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册失败: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.post("/login")
async def login(data: UserLogin):
    """用户登录"""
    user = await get_user_by_username(data.username)
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(user["id"], user["username"])
    logger.info(f"用户登录: {data.username} (id={user['id']})")

    return {
        "message": "登录成功",
        "token": token,
        "user": {"id": user["id"], "username": user["username"]},
    }


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user["id"],
        "username": current_user["username"],
    }
