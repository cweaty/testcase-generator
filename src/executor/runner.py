"""
Playwright 测试脚本执行器
负责生成、运行、收集结果和截图
"""
import os
import sys
import re
import json
import uuid
import asyncio
import logging
import tempfile
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List, AsyncIterator

from openai import AsyncOpenAI
from ..database import get_config
from .prompts import (
    CODE_GENERATION_SYSTEM_PROMPT,
    CODE_GENERATION_USER_PROMPT,
    BATCH_CODE_GENERATION_PROMPT,
)

logger = logging.getLogger(__name__)

# 执行结果存储目录
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "test_results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def _make_run_dir(case_id: str = None) -> str:
    """为一次执行创建唯一的目录"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = case_id or uuid.uuid4().hex[:6]
    run_id = f"{ts}_{tag}"
    run_dir = os.path.join(RESULTS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


async def _get_ai_client() -> tuple:
    """获取 AI 客户端"""
    base_url = await get_config("ai_base_url") or "https://api.openai.com/v1"
    api_key = await get_config("ai_api_key") or ""
    model = await get_config("ai_model") or "gpt-4o"

    if not api_key:
        raise ValueError("未配置 AI API Key，请在设置页面配置")

    temp_str = await get_config("ai_temperature")
    temperature = float(temp_str) if temp_str else 0.3

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    return client, model, temperature


async def generate_code(testcase: dict, base_url: str = "http://localhost:3000", timeout: int = 30000) -> str:
    """
    用 AI 将单个测试用例转为 Playwright Python 脚本
    返回生成的 Python 代码
    """
    client, model, temperature = await _get_ai_client()

    steps_text = testcase.get("steps", "")
    expected = testcase.get("expected_result", "")

    user_prompt = CODE_GENERATION_USER_PROMPT.format(
        case_id=testcase.get("case_id", "TC-001"),
        module=testcase.get("module", ""),
        title=testcase.get("title", ""),
        priority=testcase.get("priority", "P2"),
        case_type=testcase.get("case_type", "功能测试"),
        precondition=testcase.get("precondition", "无"),
        steps=steps_text,
        expected_result=expected or "无",
        base_url=base_url,
        timeout=timeout,
    )

    logger.info(f"正在为用例 [{testcase.get('case_id')}] 生成 Playwright 代码...")

    max_retries = 2
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                await asyncio.sleep(2)

            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": CODE_GENERATION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=8000,
                ),
                timeout=120,
            )

            code = response.choices[0].message.content.strip()
            code = _clean_code(code)

            # 基本语法检查
            compile(code, "<generated>", "exec")
            logger.info(f"代码生成成功，长度 {len(code)} 字符")
            return code

        except SyntaxError as e:
            logger.warning(f"生成的代码语法错误 (尝试 {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise ValueError(f"AI 生成的代码语法错误: {e}")
        except asyncio.TimeoutError:
            logger.warning(f"代码生成超时 (尝试 {attempt}/{max_retries})")
            if attempt == max_retries:
                raise RuntimeError("代码生成超时（120秒），请检查 AI 服务是否正常")
        except Exception as e:
            logger.warning(f"代码生成失败 (尝试 {attempt}/{max_retries}): {e}")
            if attempt == max_retries:
                raise RuntimeError(f"代码生成失败: {e}")

    raise RuntimeError("代码生成失败")


async def generate_batch_code(testcases: list, base_url: str = "http://localhost:3000", timeout: int = 30000) -> str:
    """
    用 AI 将多个测试用例合并为一个 Playwright 测试脚本
    """
    client, model, temperature = await _get_ai_client()

    cases_text = json.dumps(
        [
            {
                "case_id": tc.get("case_id", ""),
                "title": tc.get("title", ""),
                "module": tc.get("module", ""),
                "priority": tc.get("priority", "P2"),
                "case_type": tc.get("case_type", "功能测试"),
                "precondition": tc.get("precondition", ""),
                "steps": tc.get("steps", ""),
                "expected_result": tc.get("expected_result", ""),
            }
            for tc in testcases
        ],
        ensure_ascii=False,
        indent=2,
    )

    user_prompt = BATCH_CODE_GENERATION_PROMPT.format(
        count=len(testcases),
        test_cases_json=cases_text,
        base_url=base_url,
        timeout=timeout,
    )

    logger.info(f"正在为 {len(testcases)} 个用例生成批量 Playwright 代码...")

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CODE_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=16000,
    )

    code = response.choices[0].message.content.strip()
    code = _clean_code(code)
    compile(code, "<generated>", "exec")
    return code


def _clean_code(code: str) -> str:
    """清理 AI 生成的代码，去掉 markdown 标记等"""
    # 去掉 ```python ... ``` 块
    match = re.match(r"```(?:python)?\s*\n?(.*?)\s*```", code, re.DOTALL)
    if match:
        code = match.group(1)

    # 去掉开头多余的 ``` 行
    lines = code.split("\n")
    while lines and lines[0].strip().startswith("```"):
        lines.pop(0)
    while lines and lines[-1].strip() == "```":
        lines.pop()

    return "\n".join(lines).strip()


async def run_script(code: str, screenshot_dir: str, base_url: str = "http://localhost:3000", timeout: int = 30000) -> Dict[str, Any]:
    """
    执行生成的 Playwright Python 脚本

    Args:
        code: Python 脚本内容
        screenshot_dir: 截图保存目录
        base_url: 目标网址
        timeout: 超时时间（ms）

    Returns:
        {passed, message, steps_completed, steps_total, screenshots, duration_ms}
    """
    os.makedirs(screenshot_dir, exist_ok=True)

    # 写入临时脚本文件（统一 LF 换行，避免 Windows \r\n 问题）
    script_path = os.path.join(screenshot_dir, "test_script.py")
    with open(script_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(code)

    # 构建执行环境变量
    env = os.environ.copy()
    env["SCREENSHOT_DIR"] = screenshot_dir
    env["BASE_URL"] = base_url
    env["TIMEOUT"] = str(timeout)
    env["PYTHONIOENCODING"] = "utf-8"  # 强制子进程使用 UTF-8 输出

    start_time = asyncio.get_event_loop().time()

    try:
        # cwd 必须用项目根目录，不能用 screenshot_dir（Playwright Node.js 驱动不支持）
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 检测 venv 中的 Python（确保 playwright 模块可用）
        venv_python = None
        if sys.platform == "win32":
            candidate = os.path.join(project_root, ".venv", "Scripts", "python.exe")
        else:
            candidate = os.path.join(project_root, ".venv", "bin", "python")
        if os.path.exists(candidate):
            venv_python = candidate
        
        python_exe = venv_python or sys.executable
        logger.info(f"执行脚本使用 Python: {python_exe}")
        
        process = await asyncio.create_subprocess_exec(
            python_exe, script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=project_root,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return {
                "passed": False,
                "message": "脚本执行超时（120秒限制）",
                "steps_completed": 0,
                "steps_total": 0,
                "screenshots": [],
                "duration_ms": 120000,
                "script_path": script_path,
                "stdout": "",
                "stderr": "执行超时",
            }

        duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        # 修复常见编码乱码（Windows GBK 输出被 UTF-8 解码）
        if "����" in stderr_text or "׷" in stderr_text:
            try:
                stderr_text = stderr.decode("gbk", errors="replace").strip()
            except Exception:
                pass
        if "����" in stdout_text:
            try:
                stdout_text = stdout.decode("gbk", errors="replace").strip()
            except Exception:
                pass

        # 解析结果
        result = _parse_test_result(stdout_text)

        # 收集截图
        screenshots = []
        if os.path.exists(screenshot_dir):
            for f in sorted(os.listdir(screenshot_dir)):
                if f.endswith(".png"):
                    screenshots.append(f)

        result["screenshots"] = screenshots
        result["duration_ms"] = duration_ms
        result["script_path"] = script_path
        result["stdout"] = stdout_text
        result["stderr"] = stderr_text

        if process.returncode != 0 and not result.get("message"):
            result["passed"] = False
            result["message"] = f"脚本退出码: {process.returncode}"

        # 如果脚本没有输出 ###TEST_RESULT###，把 stderr 信息加入 message
        if not result.get("passed") and stderr_text and "###TEST_RESULT###" not in stdout_text:
            # 取 stderr 最后 500 字符作为错误详情
            err_summary = stderr_text[-500:].strip()
            if err_summary:
                result["message"] = f"{result.get('message', '脚本执行失败')} | {err_summary}"

        return result

    except Exception as e:
        duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        return {
            "passed": False,
            "message": f"执行异常: {str(e)}",
            "steps_completed": 0,
            "steps_total": 0,
            "screenshots": [],
            "duration_ms": duration_ms,
            "script_path": script_path,
            "stdout": "",
            "stderr": str(e),
        }


def _parse_test_result(stdout: str) -> Dict[str, Any]:
    """从脚本 stdout 中解析 ###TEST_RESULT### 标记的结果"""
    # 查找 ###TEST_RESULT### 标记
    pattern = r"###TEST_RESULT###\s*(\{.*\})"
    match = re.search(pattern, stdout)
    if match:
        try:
            result = json.loads(match.group(1))
            result.setdefault("passed", False)
            result.setdefault("message", "")
            result.setdefault("steps_completed", 0)
            result.setdefault("steps_total", 0)
            return result
        except json.JSONDecodeError:
            pass

    # 没有标记，尝试判断整体成功/失败
    return {
        "passed": False,
        "message": "脚本未输出结果标记（###TEST_RESULT###）",
        "steps_completed": 0,
        "steps_total": 0,
    }


async def execute_testcase(testcase: dict, base_url: str = "http://localhost:3000", timeout: int = 30000) -> Dict[str, Any]:
    """
    完整流程：为一个测试用例生成代码并执行

    Returns:
        完整的执行结果字典
    """
    case_id = testcase.get("case_id", "unknown")

    # 1. 生成代码
    code = await generate_code(testcase, base_url=base_url, timeout=timeout)

    # 2. 创建执行目录
    run_dir = _make_run_dir(case_id)

    # 3. 保存生成的代码
    with open(os.path.join(run_dir, "test_script.py"), "w", encoding="utf-8") as f:
        f.write(code)

    # 4. 执行脚本
    result = await run_script(code, screenshot_dir=run_dir, base_url=base_url, timeout=timeout)
    result["run_dir"] = run_dir
    result["case_id"] = case_id
    result["code"] = code

    return result


async def execute_testcases_batch(
    testcases: list,
    base_url: str = "http://localhost:3000",
    timeout: int = 30000,
) -> Dict[str, Any]:
    """
    为多个测试用例生成代码并逐个执行

    Returns:
        {
            total, passed, failed, duration_ms,
            results: [{case_id, passed, message, screenshots, duration_ms, ...}]
        }
    """
    overall_start = asyncio.get_event_loop().time()
    results = []

    for tc in testcases:
        try:
            result = await execute_testcase(tc, base_url=base_url, timeout=timeout)
            results.append(result)
        except Exception as e:
            results.append({
                "case_id": tc.get("case_id", "unknown"),
                "passed": False,
                "message": f"执行失败: {str(e)}",
                "screenshots": [],
                "duration_ms": 0,
                "code": "",
                "steps_completed": 0,
                "steps_total": 0,
            })

    total_ms = int((asyncio.get_event_loop().time() - overall_start) * 1000)
    passed_count = sum(1 for r in results if r.get("passed"))

    return {
        "total": len(testcases),
        "passed": passed_count,
        "failed": len(testcases) - passed_count,
        "duration_ms": total_ms,
        "results": results,
    }
