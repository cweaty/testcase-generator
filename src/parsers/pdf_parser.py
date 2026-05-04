"""
PDF 文档解析器
使用 PyMuPDF (fitz) 提取文本和结构信息
"""
import os
import re


def parse_pdf(file_path: str) -> dict:
    """
    解析 PDF 文档，提取文本和结构化信息
    
    参数:
        file_path: .pdf 文件路径
    
    返回:
        {
            "title": 文档标题,
            "sections": [{"heading": 标题, "level": 级别, "content": 内容}],
            "raw_content": 纯文本内容,
            "page_count": 页数
        }
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("请安装 PyMuPDF: pip install PyMuPDF")

    doc = fitz.open(file_path)
    title = ""
    sections = []
    all_text = []
    current_section = None
    current_content = []
    page_count = len(doc)

    for page_num in range(page_count):
        page = doc.load_page(page_num)
        
        # 提取文本块（带格式信息）
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if block["type"] == 0:  # 文本块
                for line in block["lines"]:
                    text = ""
                    max_font_size = 0
                    is_bold = False
                    
                    for span in line["spans"]:
                        text += span["text"]
                        max_font_size = max(max_font_size, span["size"])
                        if span["flags"] & 16:  # Bold flag
                            is_bold = True
                    
                    text = text.strip()
                    if not text:
                        continue
                    
                    all_text.append(text)
                    
                    # 判断是否为标题（基于字体大小和粗体）
                    if max_font_size >= 16 or (is_bold and max_font_size >= 14 and len(text) < 100):
                        # 保存上一个 section
                        if current_section:
                            current_section["content"] = "\n".join(current_content).strip()
                            if current_section["content"]:
                                sections.append(current_section)
                        
                        level = 1
                        if max_font_size >= 20:
                            level = 1
                        elif max_font_size >= 16:
                            level = 2
                        else:
                            level = 3
                        
                        if not title and level == 1:
                            title = text
                        
                        current_section = {
                            "heading": text,
                            "level": level,
                            "content": ""
                        }
                        current_content = []
                    else:
                        current_content.append(text)
    
    doc.close()

    # 保存最后一个 section
    if current_section:
        current_section["content"] = "\n".join(current_content).strip()
        if current_section["content"]:
            sections.append(current_section)

    if not title:
        title = os.path.basename(file_path)

    return {
        "title": title,
        "sections": sections,
        "raw_content": "\n".join(all_text),
        "page_count": page_count
    }
