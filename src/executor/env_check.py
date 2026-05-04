"""
自动环境检测 — 检查 Playwright、PyMuPDF 等依赖是否安装
"""
import os
import sys
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _get_project_python() -> str:
    """获取项目 venv 中的 Python 路径（非 sys.executable）"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if sys.platform == "win32":
        candidate = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    else:
        candidate = os.path.join(project_root, ".venv", "bin", "python")
    if os.path.exists(candidate):
        return candidate
    return sys.executable


def check_playwright() -> Dict[str, Any]:
    """检测 Playwright 及浏览器状态"""
    result = {"installed": False, "browsers": [], "error": None}
    try:
        import playwright
        result["installed"] = True
        result["version"] = getattr(playwright, "__version__", "unknown")
    except ImportError:
        result["error"] = "playwright 未安装"
        return result

    # 检查 chromium 浏览器
    try:
        if sys.platform == "win32":
            base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
        else:
            base = os.path.expanduser("~/.cache/ms-playwright")
        if os.path.exists(base):
            for d in os.listdir(base):
                if d.startswith("chromium"):
                    result["browsers"].append(d)
    except Exception as e:
        result["error"] = str(e)

    return result


def check_pymupdf() -> Dict[str, Any]:
    """检测 PyMuPDF"""
    result = {"installed": False, "version": None, "error": None}
    try:
        import fitz
        result["installed"] = True
        result["version"] = fitz.version[0]
    except ImportError:
        result["error"] = "PyMuPDF 未安装"
    return result


def check_cryptography() -> Dict[str, Any]:
    """检测 cryptography (用于 API Key 加密)"""
    result = {"installed": False, "version": None}
    try:
        import cryptography
        result["installed"] = True
        result["version"] = cryptography.__version__
    except ImportError:
        pass
    return result


def check_all() -> Dict[str, Dict[str, Any]]:
    """检测所有可选依赖"""
    py = _get_project_python()
    return {
        "playwright": check_playwright(),
        "pymupdf": check_pymupdf(),
        "cryptography": check_cryptography(),
        "python": {"version": sys.version, "executable": sys.executable, "project_python": py},
    }


def install_package(package_name: str) -> Dict[str, Any]:
    """安装 Python 包（使用项目 venv 的 Python）"""
    py = _get_project_python()
    logger.info(f"使用 Python 安装 {package_name}: {py}")
    try:
        subprocess.check_call([py, "-m", "pip", "install", package_name], timeout=120)
        return {"success": True, "message": f"{package_name} 安装成功"}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"安装失败: {e}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "安装超时"}


def install_playwright_browser() -> Dict[str, Any]:
    """安装 Playwright Chromium 浏览器（使用项目 venv 的 Python）"""
    py = _get_project_python()
    logger.info(f"使用 Python 安装 Chromium: {py}")
    try:
        subprocess.check_call([py, "-m", "playwright", "install", "chromium"], timeout=300)
        return {"success": True, "message": "Chromium 浏览器安装成功"}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"浏览器安装失败: {e}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "安装超时（300秒）"}
