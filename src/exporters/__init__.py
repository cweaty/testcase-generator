"""
导出模块
支持 Excel、CSV、JSON、Markdown、PDF 多格式导出
"""
from .excel_exporter import export_to_excel
from .pdf_exporter import export_to_pdf


def export_to_csv(test_cases: list) -> bytes:
    """将测试用例导出为 CSV 文件"""
    import io
    import csv

    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel Chinese support

    writer = csv.writer(output)
    writer.writerow(["用例编号", "所属模块", "用例标题", "优先级", "用例类型", "前置条件", "测试步骤", "预期结果"])

    for tc in test_cases:
        writer.writerow([
            tc.get("case_id", ""),
            tc.get("module", ""),
            tc.get("title", ""),
            tc.get("priority", ""),
            tc.get("case_type", ""),
            tc.get("precondition", ""),
            tc.get("steps", ""),
            tc.get("expected_result", ""),
        ])

    return output.getvalue().encode("utf-8")


def export_to_json(test_cases: list, title: str = "测试用例") -> bytes:
    """将测试用例导出为 JSON 文件"""
    import json
    from datetime import datetime

    data = {
        "title": title,
        "exported_at": datetime.now().isoformat(),
        "total": len(test_cases),
        "testcases": []
    }

    for tc in test_cases:
        data["testcases"].append({
            "case_id": tc.get("case_id", ""),
            "module": tc.get("module", ""),
            "title": tc.get("title", ""),
            "priority": tc.get("priority", ""),
            "case_type": tc.get("case_type", ""),
            "precondition": tc.get("precondition", ""),
            "steps": tc.get("steps", ""),
            "expected_result": tc.get("expected_result", ""),
        })

    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def export_to_markdown(test_cases: list, title: str = "测试用例") -> bytes:
    """将测试用例导出为 Markdown 文件"""
    from collections import Counter

    lines = [f"# {title}\n"]

    # 统计信息
    priorities = Counter(tc.get("priority", "") for tc in test_cases)
    lines.append(f"**总计: {len(test_cases)} 条**\n")
    lines.append(f"| 优先级 | 数量 |")
    lines.append(f"|--------|------|")
    for p in ["P0", "P1", "P2", "P3"]:
        if priorities.get(p):
            lines.append(f"| {p} | {priorities[p]} |")
    lines.append("")

    # 按模块分组
    modules: dict = {}
    for tc in test_cases:
        mod = tc.get("module", "未分类")
        modules.setdefault(mod, []).append(tc)

    for mod, cases in modules.items():
        lines.append(f"## {mod}\n")
        lines.append("| 编号 | 标题 | 优先级 | 类型 |")
        lines.append("|------|------|--------|------|")
        for tc in cases:
            lines.append(f"| {tc.get('case_id', '')} | {tc.get('title', '')} | {tc.get('priority', '')} | {tc.get('case_type', '')} |")
        lines.append("")

        for tc in cases:
            lines.append(f"### {tc.get('case_id', '')} - {tc.get('title', '')}\n")
            lines.append(f"- **优先级**: {tc.get('priority', '')}")
            lines.append(f"- **类型**: {tc.get('case_type', '')}")
            if tc.get("precondition"):
                lines.append(f"- **前置条件**: {tc['precondition']}")
            lines.append(f"\n**测试步骤**:\n")
            lines.append(tc.get("steps", ""))
            lines.append(f"\n**预期结果**:\n")
            lines.append(tc.get("expected_result", ""))
            lines.append("\n---\n")

    return "\n".join(lines).encode("utf-8")


__all__ = ["export_to_excel", "export_to_csv", "export_to_json", "export_to_markdown", "export_to_pdf"]
