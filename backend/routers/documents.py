"""文档相关 API 路由"""
import os
import hashlib
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from ..config import settings
from ..models import TextInput, DocumentUploadResponse, BatchDeleteRequest, DocumentType
from ..database import (
    insert_document, get_document, list_documents,
    delete_document, delete_documents_batch,
    log_operation,
)
from ..parsers import parse_markdown, parse_docx, parse_openapi, PDF_AVAILABLE
if PDF_AVAILABLE:
    from ..parsers import parse_pdf
from ._shared import _stats_cache, invalidate_stats_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """上传文档文件（支持 .md, .docx, .json, .pdf, .txt）"""
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()

    content_bytes = await file.read()
    file_size = len(content_bytes)

    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小超过50MB限制")

    content = ""

    if ext in (".md", ".json", ".txt"):
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="文件编码不支持，请使用 UTF-8 编码")
        doc_type = DocumentType.MARKDOWN if ext != ".json" else DocumentType.OPENAPI
        if ext == ".json":
            try:
                parsed = parse_openapi(content)
                if not parsed.get("endpoints"):
                    doc_type = DocumentType.MARKDOWN
            except Exception:
                doc_type = DocumentType.MARKDOWN
        save_path = os.path.join(settings.upload_dir, filename)
        with open(save_path, "wb") as f:
            f.write(content_bytes)

    elif ext == ".docx":
        doc_type = DocumentType.DOCX
        save_path = os.path.join(settings.upload_dir, filename)
        with open(save_path, "wb") as f:
            f.write(content_bytes)
        try:
            parsed = parse_docx(save_path)
            content = parsed["raw_content"]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"解析 Word 文档失败: {e}")

    elif ext == ".pdf":
        if not PDF_AVAILABLE:
            raise HTTPException(status_code=400, detail="PDF 解析库未安装，请运行: pip install PyMuPDF")
        doc_type = DocumentType.PDF
        save_path = os.path.join(settings.upload_dir, filename)
        with open(save_path, "wb") as f:
            f.write(content_bytes)
        try:
            parsed = parse_pdf(save_path)
            content = parsed["raw_content"]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"解析 PDF 文档失败: {e}")
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，请上传 .md/.docx/.json/.txt{'/.pdf' if PDF_AVAILABLE else ''} 文件"
        )

    if not content:
        raise HTTPException(status_code=400, detail="文档内容为空")

    # 内容去重检查
    content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
    existing_docs = await list_documents(page_size=100000)
    for existing in existing_docs.get("documents", []):
        existing_doc = await get_document(existing["id"])
        if existing_doc:
            existing_hash = hashlib.md5(existing_doc["content"].encode("utf-8")).hexdigest()
            if existing_hash == content_hash:
                logger.warning(f"文档内容重复: {filename} 与已有文档 {existing_doc['filename']} (ID: {existing_doc['id']}) 内容相同")
                raise HTTPException(status_code=409, detail=f"文档内容已存在：与「{existing_doc['filename']}」(ID: {existing_doc['id']}) 内容相同，已跳过上传")

    doc_id = await insert_document(filename, doc_type.value, content, file_size)
    logger.info(f"文档上传成功: {filename} (ID: {doc_id}, 类型: {doc_type.value}, 大小: {file_size})")
    invalidate_stats_cache()
    await log_operation("upload", "document", doc_id, f"上传文档: {filename}")

    return DocumentUploadResponse(
        id=doc_id,
        filename=filename,
        doc_type=doc_type.value,
        content_preview=content[:200] + ("..." if len(content) > 200 else ""),
        file_size=file_size,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


@router.post("/documents/text", response_model=DocumentUploadResponse)
async def create_text_document(text_input: TextInput):
    """直接提交文本内容创建文档"""
    content = text_input.content
    file_size = len(content.encode("utf-8"))
    doc_id = await insert_document(text_input.title, text_input.doc_type.value, content, file_size)
    logger.info(f"文本文档创建成功: {text_input.title} (ID: {doc_id})")
    invalidate_stats_cache()

    return DocumentUploadResponse(
        id=doc_id,
        filename=text_input.title,
        doc_type=text_input.doc_type.value,
        content_preview=content[:200] + ("..." if len(content) > 200 else ""),
        file_size=file_size,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


@router.get("/documents")
async def get_documents(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str = Query("", description="搜索关键词"),
):
    """获取文档列表（支持分页和搜索）"""
    return await list_documents(page=page, page_size=page_size, search=search)


@router.get("/documents/{doc_id}")
async def get_document_detail(doc_id: int):
    """获取文档详情"""
    doc = await get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.get("/documents/{doc_id}/preview")
async def preview_document(doc_id: int):
    """获取文档内容预览"""
    doc = await get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {
        "id": doc["id"],
        "filename": doc["filename"],
        "doc_type": doc["doc_type"],
        "content": doc["content"],
        "content_length": len(doc["content"]),
    }


@router.delete("/documents/{doc_id}")
async def delete_document_api(doc_id: int):
    """删除文档及其关联的测试用例"""
    success = await delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")
    invalidate_stats_cache()
    await log_operation("delete", "document", doc_id, f"删除文档 ID:{doc_id}")
    return {"message": "删除成功", "id": doc_id}


@router.post("/documents/batch-delete")
async def batch_delete_documents(request: BatchDeleteRequest):
    """批量删除文档"""
    count = await delete_documents_batch(request.ids)
    invalidate_stats_cache()
    return {"message": f"成功删除 {count} 个文档", "deleted": count}


@router.post("/documents/batch-upload")
async def batch_upload_documents(files: List[UploadFile] = File(...)):
    """批量上传文档文件"""
    results = []
    for file in files:
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        try:
            content_bytes = await file.read()
            file_size = len(content_bytes)

            if file_size > 50 * 1024 * 1024:
                results.append({"filename": filename, "success": False, "error": "文件大小超过50MB限制"})
                continue

            content = ""
            if ext in (".md", ".json", ".txt"):
                try:
                    content = content_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    results.append({"filename": filename, "success": False, "error": "文件编码不支持，请使用 UTF-8 编码"})
                    continue
                doc_type = DocumentType.MARKDOWN if ext != ".json" else DocumentType.OPENAPI
                if ext == ".json":
                    try:
                        parsed = parse_openapi(content)
                        if not parsed.get("endpoints"):
                            doc_type = DocumentType.MARKDOWN
                    except Exception:
                        doc_type = DocumentType.MARKDOWN
                save_path = os.path.join(settings.upload_dir, filename)
                with open(save_path, "wb") as f:
                    f.write(content_bytes)
            elif ext == ".docx":
                doc_type = DocumentType.DOCX
                save_path = os.path.join(settings.upload_dir, filename)
                with open(save_path, "wb") as f:
                    f.write(content_bytes)
                try:
                    parsed = parse_docx(save_path)
                    content = parsed["raw_content"]
                except Exception as e:
                    results.append({"filename": filename, "success": False, "error": f"解析 Word 文档失败: {e}"})
                    continue
            elif ext == ".pdf":
                if not PDF_AVAILABLE:
                    results.append({"filename": filename, "success": False, "error": "PDF 解析库未安装"})
                    continue
                doc_type = DocumentType.PDF
                save_path = os.path.join(settings.upload_dir, filename)
                with open(save_path, "wb") as f:
                    f.write(content_bytes)
                try:
                    parsed = parse_pdf(save_path)
                    content = parsed["raw_content"]
                except Exception as e:
                    results.append({"filename": filename, "success": False, "error": f"解析 PDF 文档失败: {e}"})
                    continue
            else:
                results.append({"filename": filename, "success": False, "error": f"不支持的文件格式: {ext}"})
                continue

            if not content:
                results.append({"filename": filename, "success": False, "error": "文档内容为空"})
                continue

            # Dedup check
            content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
            existing_docs = await list_documents(page_size=100000)
            duplicate = False
            for existing in existing_docs.get("documents", []):
                existing_doc = await get_document(existing["id"])
                if existing_doc:
                    existing_hash = hashlib.md5(existing_doc["content"].encode("utf-8")).hexdigest()
                    if existing_hash == content_hash:
                        results.append({"filename": filename, "success": False, "error": f"文档内容已存在：与「{existing_doc['filename']}」内容相同"})
                        duplicate = True
                        break
            if duplicate:
                continue

            doc_id = await insert_document(filename, doc_type.value, content, file_size)
            invalidate_stats_cache()
            await log_operation("upload", "document", doc_id, f"批量上传文档: {filename}")
            results.append({
                "filename": filename, "success": True, "id": doc_id,
                "doc_type": doc_type.value, "file_size": file_size
            })
        except HTTPException as e:
            results.append({"filename": filename, "success": False, "error": e.detail})
        except Exception as e:
            results.append({"filename": filename, "success": False, "error": str(e)})

    success_count = sum(1 for r in results if r["success"])
    return {"total": len(files), "success": success_count, "failed": len(files) - success_count, "results": results}
