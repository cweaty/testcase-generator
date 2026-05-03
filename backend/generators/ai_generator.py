"""
AI 测试用例生成器核心模块
使用 OpenAI 兼容 API 生成测试用例，支持流式和非流式
"""
import json
import re
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from openai import AsyncOpenAI

from ..database import get_config

logger = logging.getLogger(__name__)


# 测试用例类型对应的 prompt 片段
TYPE_PROMPTS = {
    "功能测试": """功能测试（Happy Path）：验证正常业务流程是否符合预期，覆盖主要功能点的正常使用场景。""",
    "边界测试": """边界条件测试：验证输入边界值、临界条件下的系统行为，包括最大值、最小值、空值、特殊字符等。""",
    "异常测试": """异常场景测试：验证错误输入、非法操作、异常状态下的系统容错能力，包括错误提示、异常恢复等。""",
    "流程测试": """用户流程测试（E2E）：验证完整的用户操作流程，覆盖多步骤、多页面的完整业务场景。""",
    "接口测试": """接口测试：验证 API 接口的参数校验、请求/响应格式、状态码、错误码、权限控制等。""",
}

SYSTEM_PROMPT = """你是一位资深的软件测试工程师，擅长根据需求文档或接口文档编写高质量的测试用例。

你需要根据用户提供的文档内容，生成结构化的测试用例。

## 输出格式要求
请严格以 JSON 数组格式输出，每个测试用例包含以下字段：
```json
[
  {
    "case_id": "TC-001",
    "module": "模块名称",
    "title": "测试用例标题（简洁明了，描述测试什么）",
    "priority": "P0/P1/P2/P3",
    "case_type": "功能测试/边界测试/异常测试/流程测试/接口测试",
    "precondition": "前置条件（执行此用例前需要满足的条件）",
    "steps": "1. 步骤一\\n2. 步骤二\\n3. 步骤三",
    "expected_result": "预期结果（详细的预期行为描述）"
  }
]
```

## 优先级定义
- P0：核心功能冒烟测试，阻塞级
- P1：重要功能测试，必须通过
- P2：一般功能测试
- P3：边界/低优先级场景

## 质量要求
1. 每条用例的测试步骤要详细、可执行
2. 预期结果要具体、可验证
3. 用例之间不重复、不遗漏
4. 按模块和优先级合理分组
5. 覆盖正向、反向、边界多种场景

## 重要
- 只输出 JSON 数组，不要输出其他任何文字、解释或标题
- 确保 JSON 格式正确，可以被直接解析
- 用例数量要充足，覆盖要全面"""


def _build_user_prompt(content: str, test_types: List[str], doc_type: str = "text", count: int = None) -> str:
    """构建用户提示词"""
    type_desc = "\n".join(f"- {TYPE_PROMPTS.get(t, t)}" for t in test_types)

    doc_label = {
        "markdown": "需求文档",
        "docx": "需求文档",
        "openapi": "API 接口文档",
        "text": "文档",
        "pdf": "文档",
    }.get(doc_type, "文档")

    count_hint = ""
    if count:
        count_hint = f"\n## 指定数量\n请只生成恰好 {count} 条测试用例。"

    return f"""请根据以下{doc_label}内容，生成测试用例。

## 需要生成的测试用例类型
{type_desc}
{count_hint}

## {doc_label}内容
{content}

请严格按照系统提示中的 JSON 格式输出测试用例。只输出 JSON 数组，不要有其他内容。"""


def _parse_response(text: str) -> List[Dict[str, Any]]:
    """解析 AI 返回的 JSON — 增强版，处理各种格式"""
    text = text.strip()

    # 1. 直接解析
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return _validate_cases(result)
    except json.JSONDecodeError:
        pass

    # 2. 提取 ```json ... ``` 块
    json_block_patterns = [
        r'```json\s*\n?(.*?)\s*```',
        r'```\s*\n?(.*?)\s*```',
    ]
    for pattern in json_block_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1).strip())
                if isinstance(result, list):
                    return _validate_cases(result)
            except json.JSONDecodeError:
                continue

    # 3. 贪婪匹配最外层的 [ ... ] 数组
    bracket_start = text.find('[')
    bracket_end = text.rfind(']')
    if bracket_start != -1 and bracket_end > bracket_start:
        candidate = text[bracket_start:bracket_end + 1]
        try:
            result = json.loads(candidate)
            if isinstance(result, list):
                return _validate_cases(result)
        except json.JSONDecodeError:
            pass

    # 4. 逐行尝试修复常见的 JSON 问题（尾部逗号、缺少括号等）
    if bracket_start != -1 and bracket_end > bracket_start:
        candidate = text[bracket_start:bracket_end + 1]
        # 移除尾部逗号
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        try:
            result = json.loads(candidate)
            if isinstance(result, list):
                return _validate_cases(result)
        except json.JSONDecodeError:
            pass

    # 5. 尝试将 AI 输出按行分段提取 JSON 对象
    objects = []
    obj_pattern = r'\{[^{}]*\}'
    for match in re.finditer(obj_pattern, text, re.DOTALL):
        try:
            obj = json.loads(match.group())
            if isinstance(obj, dict) and obj.get("title"):
                objects.append(obj)
        except json.JSONDecodeError:
            continue
    if objects:
        return _validate_cases(objects)

    raise ValueError("无法解析 AI 返回的测试用例，请重试")


def _validate_cases(cases: list) -> List[Dict[str, Any]]:
    """验证和清洗测试用例数据"""
    valid_cases = []
    for i, tc in enumerate(cases):
        if not isinstance(tc, dict):
            continue
        # 确保必要字段存在
        if not tc.get("title") or not tc.get("steps"):
            continue

        # 设置默认值
        tc.setdefault("case_id", f"TC-{i+1:03d}")
        tc.setdefault("module", "")
        tc.setdefault("precondition", "")
        tc.setdefault("expected_result", "")
        tc.setdefault("priority", "P2")
        tc.setdefault("case_type", "功能测试")

        valid_cases.append(tc)

    return valid_cases


class AITestCaseGenerator:
    """AI 测试用例生成器"""

    def __init__(self, base_url: str = None, api_key: str = None, model: str = None, custom_prompt: str = None):
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._custom_prompt = custom_prompt
        self._temperature = 0.3
        self._max_tokens = 16000

    async def _get_client(self) -> tuple:
        """获取 AI 客户端配置"""
        base_url = self._base_url or await get_config("ai_base_url") or "https://api.openai.com/v1"
        api_key = self._api_key or await get_config("ai_api_key") or ""
        model = self._model or await get_config("ai_model") or "gpt-4o"

        if not api_key:
            raise ValueError("未配置 AI API Key，请在设置页面配置")

        temp_str = await get_config("ai_temperature")
        tokens_str = await get_config("ai_max_tokens")
        self._temperature = float(temp_str) if temp_str else 0.3
        self._max_tokens = int(tokens_str) if tokens_str else 16000

        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        return client, model

    async def generate(
        self,
        content: str,
        test_types: List[str],
        doc_type: str = "text",
        document_id: int = None,
        count: int = None
    ) -> List[Dict[str, Any]]:
        """
        非流式生成测试用例
        """
        client, model = await self._get_client()
        user_prompt = _build_user_prompt(content, test_types, doc_type, count=count)
        system_prompt = self._custom_prompt if self._custom_prompt else SYSTEM_PROMPT

        logger.info(f"开始调用 AI 生成测试用例，模型: {model}，文档类型: {doc_type}，温度: {self._temperature}，最大Token: {self._max_tokens}，自定义Prompt: {'是' if self._custom_prompt else '否'}")

        max_retries = 3
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    logger.info(f"第 {attempt} 次重试...")
                    import asyncio
                    await asyncio.sleep(2 * attempt)

                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                )

                result_text = response.choices[0].message.content.strip()
                logger.info(f"AI 响应长度: {len(result_text)} 字符 (尝试 {attempt}/{max_retries})")

                # 保存原始响应用于调试
                if attempt == 1:
                    logger.debug(f"AI 原始响应前 500 字符: {result_text[:500]}")

                test_cases = _parse_response(result_text)

                for tc in test_cases:
                    tc["document_id"] = document_id

                logger.info(f"成功生成 {len(test_cases)} 条测试用例")
                return test_cases

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(f"AI 返回解析失败 (尝试 {attempt}/{max_retries}): {e}")
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"AI 调用失败 (尝试 {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    continue
                break

        logger.error(f"AI 生成测试用例在 {max_retries} 次重试后仍然失败")
        raise RuntimeError(f"AI 生成失败（已重试 {max_retries} 次）: {str(last_error)}")

    async def generate_stream(
        self,
        content: str,
        test_types: List[str],
        doc_type: str = "text",
        document_id: int = None,
        count: int = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式生成测试用例 — 通过 SSE 逐条返回结果

        Yields:
            {'type': 'start', ...}
            {'type': 'chunk', 'text': '...'}   — AI 原始输出片段
            {'type': 'testcase', 'data': {...}} — 每解析出一条用例立即返回
            {'type': 'complete', ...}
            {'type': 'error', ...}
        """
        import asyncio

        client, model = await self._get_client()
        user_prompt = _build_user_prompt(content, test_types, doc_type, count=count)
        system_prompt = self._custom_prompt if self._custom_prompt else SYSTEM_PROMPT

        logger.info(f"开始流式生成，模型: {model}")

        yield {"type": "start", "message": "正在连接 AI 服务..."}

        max_retries = 3
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    yield {"type": "retry", "message": f"第 {attempt} 次尝试...", "attempt": attempt}
                    await asyncio.sleep(2 * attempt)

                yield {"type": "progress", "message": f"AI 正在分析文档并生成用例 (尝试 {attempt})..."}

                # 使用 stream=True 获取真正的流式响应
                full_text = ""
                chunk_count = 0
                stream = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                    stream=True,
                )
                async for chunk in stream:
                    if not chunk.choices or not chunk.choices[0].delta:
                        continue
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_text += delta.content
                        chunk_count += 1
                        # 每 20 个 chunk 发送一次进度
                        if chunk_count % 20 == 0:
                            yield {"type": "chunk_progress", "length": len(full_text)}

                logger.info(f"流式响应完成，总长度: {len(full_text)} 字符")

                # 解析完整响应
                test_cases = _parse_response(full_text)

                for tc in test_cases:
                    tc["document_id"] = document_id

                # 逐条返回解析出的用例
                for i, tc in enumerate(test_cases):
                    yield {"type": "testcase", "data": tc, "index": i + 1, "total": len(test_cases)}

                yield {"type": "complete", "total": len(test_cases), "message": f"成功生成 {len(test_cases)} 条测试用例！"}
                return  # 成功，退出

            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(f"流式生成解析失败 (尝试 {attempt}/{max_retries}): {e}")
                yield {"type": "parse_error", "message": f"解析失败: {str(e)}", "attempt": attempt, "raw_length": len(full_text) if 'full_text' in dir() else 0}
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"流式生成失败 (尝试 {attempt}/{max_retries}): {e}")
                yield {"type": "error", "message": f"生成失败: {str(e)}", "attempt": attempt}
                if attempt < max_retries:
                    continue
                break

        yield {"type": "fatal", "message": f"AI 生成失败（已重试 {max_retries} 次）: {str(last_error)}"}
