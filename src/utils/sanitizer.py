"""
输入清理工具
用于防止 XSS 攻击和路径遍历
"""
import os
import re
import html


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input to prevent XSS and enforce length limits"""
    if not text:
        return ''
    text = text.strip()
    text = text[:max_length]
    # Remove potential script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    return text


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\s\-.]', '', filename)
    return filename[:255] if filename else 'unnamed'
