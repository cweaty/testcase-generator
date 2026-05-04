"""
配置管理模块
支持环境变量和 .env 文件配置
"""
import os
import base64
import hashlib
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """应用配置"""
    # AI 配置
    ai_base_url: str = Field(default="https://api.openai.com/v1", description="AI API 基础地址")
    ai_api_key: str = Field(default="", description="AI API 密钥")
    ai_model: str = Field(default="gpt-4o", description="AI 模型名称")

    # 数据库配置
    database_url: str = Field(default=f"sqlite+aiosqlite:///{BASE_DIR / 'data.db'}", description="数据库地址")
    db_path: str = Field(default=str(BASE_DIR / "data.db"), description="SQLite 数据库文件路径")

    # 上传配置
    upload_dir: str = Field(default=str(BASE_DIR / "uploads"), description="上传文件目录")

    # 服务配置
    host: str = Field(default="0.0.0.0", description="服务地址")
    port: int = Field(default=8088, description="服务端口")

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"

# 全局配置实例
settings = Settings()

# 确保上传目录存在
os.makedirs(settings.upload_dir, exist_ok=True)


# ========== API Key 加密工具 ==========

def _get_fernet():
    """Get Fernet instance for encryption (requires cryptography package)"""
    try:
        from cryptography.fernet import Fernet
        key = hashlib.sha256(os.environ.get('TCG_SECRET', 'testcase-generator-default-key').encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key[:32]))
    except ImportError:
        return None


def encrypt_value(value: str) -> str:
    """Encrypt a value with Fernet. Returns 'enc:...' prefix on success."""
    f = _get_fernet()
    if f and value:
        return 'enc:' + f.encrypt(value.encode()).decode()
    return value


def decrypt_value(value: str) -> str:
    """Decrypt a value prefixed with 'enc:'. Falls back to plain text."""
    f = _get_fernet()
    if f and value and value.startswith('enc:'):
        return f.decrypt(value[4:].encode()).decode()
    return value
