"""
OpenAPI/Swagger 接口文档解析器
支持 JSON 格式的 OpenAPI 3.x 和 Swagger 2.x
"""
import json
from typing import Any, Dict, List, Optional


def parse_openapi(content: str) -> dict:
    """
    解析 OpenAPI/Swagger JSON 文档
    
    参数:
        content: JSON 格式的接口文档内容
    
    返回:
        {
            "title": API 标题,
            "version": API 版本,
            "endpoints": [接口列表],
            "raw_content": 原始内容
        }
    """
    try:
        spec = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"无效的 JSON 格式: {e}")

    # 提取基本信息
    info = spec.get("info", {})
    title = info.get("title", "未知 API")
    version = info.get("version", "unknown")
    description = info.get("description", "")

    # 提取接口信息
    endpoints = []
    paths = spec.get("paths", {})

    for path, path_item in paths.items():
        for method in ["get", "post", "put", "delete", "patch", "head", "options"]:
            operation = path_item.get(method)
            if not operation:
                continue

            endpoint = _parse_operation(path, method, operation, spec)
            endpoints.append(endpoint)

    return {
        "title": title,
        "version": version,
        "description": description,
        "endpoints": endpoints,
        "raw_content": content
    }


def _parse_operation(path: str, method: str, operation: Dict, spec: Dict) -> Dict:
    """解析单个接口操作"""
    summary = operation.get("summary", "")
    description = operation.get("description", "")
    operation_id = operation.get("operationId", "")
    tags = operation.get("tags", [])

    # 解析参数
    parameters = []
    for param in operation.get("parameters", []):
        param_info = {
            "name": param.get("name", ""),
            "in": param.get("in", ""),
            "required": param.get("required", False),
            "description": param.get("description", ""),
            "type": _get_param_type(param),
            "example": param.get("example", ""),
        }
        parameters.append(param_info)

    # 解析请求体（OpenAPI 3.x）
    request_body = None
    if "requestBody" in operation:
        rb = operation["requestBody"]
        content_type = rb.get("content", {})
        for ct, media in content_type.items():
            schema = media.get("schema", {})
            request_body = {
                "content_type": ct,
                "required": rb.get("required", False),
                "schema": _resolve_ref(schema, spec),
                "description": rb.get("description", "")
            }
            break

    # 解析响应
    responses = []
    for status_code, resp in operation.get("responses", {}).items():
        resp_info = {
            "status_code": status_code,
            "description": resp.get("description", ""),
        }
        # 提取响应 schema
        if "content" in resp:
            for ct, media in resp["content"].items():
                resp_info["schema"] = _resolve_ref(media.get("schema", {}), spec)
                break
        responses.append(resp_info)

    return {
        "path": path,
        "method": method.upper(),
        "summary": summary,
        "description": description,
        "operation_id": operation_id,
        "tags": tags,
        "parameters": parameters,
        "request_body": request_body,
        "responses": responses,
    }


def _get_param_type(param: Dict) -> str:
    """获取参数类型"""
    if "schema" in param:
        schema = param["schema"]
        return schema.get("type", "string")
    return param.get("type", "string")


def _resolve_ref(schema: Dict, spec: Dict) -> Dict:
    """解析 $ref 引用"""
    if "$ref" in schema:
        ref_path = schema["$ref"]
        # 解析 #/components/schemas/xxx
        parts = ref_path.lstrip("#/").split("/")
        resolved = spec
        for part in parts:
            resolved = resolved.get(part, {})
        return resolved
    # 解析嵌套属性
    if schema.get("type") == "object" and "properties" in schema:
        props = {}
        for name, prop in schema["properties"].items():
            props[name] = _resolve_ref(prop, spec)
        return {"type": "object", "properties": props}
    if schema.get("type") == "array" and "items" in schema:
        return {"type": "array", "items": _resolve_ref(schema["items"], spec)}
    return schema
