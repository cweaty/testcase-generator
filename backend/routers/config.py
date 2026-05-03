"""配置 API 路由"""
import logging

from fastapi import APIRouter

from ..models import AIConfig
from ..database import get_all_config, set_config, log_operation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
async def get_config_api():
    """获取当前 AI 配置"""
    config = await get_all_config()
    api_key = config.get("ai_api_key", "")
    masked_key = api_key[:8] + "****" + api_key[-4:] if len(api_key) > 12 else "****"
    return {
        "ai_base_url": config.get("ai_base_url", ""),
        "ai_api_key": api_key,
        "ai_api_key_masked": masked_key,
        "ai_api_key_set": bool(api_key),
        "ai_model": config.get("ai_model", "gpt-4o"),
        "ai_temperature": float(config.get("ai_temperature", "0.3")),
        "ai_max_tokens": int(config.get("ai_max_tokens", "16000")),
    }


@router.put("/config")
async def update_config_api(config: AIConfig):
    """更新 AI 配置"""
    await set_config("ai_base_url", config.ai_base_url)
    await set_config("ai_api_key", config.ai_api_key)
    await set_config("ai_model", config.ai_model)
    if config.ai_temperature is not None:
        await set_config("ai_temperature", str(config.ai_temperature))
    if config.ai_max_tokens is not None:
        await set_config("ai_max_tokens", str(config.ai_max_tokens))
    logger.info(f"AI 配置已更新: model={config.ai_model}, base_url={config.ai_base_url}")
    await log_operation("config", "settings", None, f"更新AI配置: model={config.ai_model}")
    return {"message": "配置更新成功"}


@router.post("/config/test")
async def test_config_connection(data: dict):
    """测试 AI API 连接配置"""
    base_url = data.get("ai_base_url", "")
    api_key = data.get("ai_api_key", "")
    model = data.get("ai_model", "")

    if not base_url or not api_key or not model:
        return {"success": False, "error": "请填写完整的配置信息（base_url、api_key、model）"}

    try:
        import httpx
        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, respond with 'ok' only."}],
            "max_tokens": 10
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                result = resp.json()
                return {"success": True, "model": model, "message": "连接成功", "response_preview": str(result.get("choices", [{}])[0].get("message", {}).get("content", ""))[:100]}
            else:
                return {"success": False, "error": f"API 返回状态码 {resp.status_code}: {resp.text[:200]}"}
    except httpx.ConnectError:
        return {"success": False, "error": f"无法连接到 {base_url}，请检查地址是否正确"}
    except httpx.TimeoutException:
        return {"success": False, "error": "连接超时，请检查网络或 API 地址"}
    except Exception as e:
        return {"success": False, "error": f"连接测试失败: {str(e)}"}
