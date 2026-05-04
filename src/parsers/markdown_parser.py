"""
Markdown 文档解析器
提取标题、段落、列表等结构化内容
"""
import re


def parse_markdown(content: str) -> dict:
    """
    解析 Markdown 文档，提取结构化信息
    
    返回:
        {
            "title": 文档标题,
            "sections": [{"heading": 标题, "level": 级别, "content": 内容}],
            "raw_content": 原始内容
        }
    """
    lines = content.strip().split("\n")
    title = ""
    sections = []
    current_section = None
    current_content = []

    for line in lines:
        # 匹配标题
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            # 保存上一个 section
            if current_section:
                current_section["content"] = "\n".join(current_content).strip()
                sections.append(current_section)

            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            if not title and level == 1:
                title = heading_text

            current_section = {
                "heading": heading_text,
                "level": level,
                "content": ""
            }
            current_content = []
        else:
            current_content.append(line)

    # 保存最后一个 section
    if current_section:
        current_section["content"] = "\n".join(current_content).strip()
        sections.append(current_section)

    # 如果没有找到标题，用第一行作为标题
    if not title and lines:
        title = lines[0].strip()[:100]

    return {
        "title": title,
        "sections": sections,
        "raw_content": content
    }
