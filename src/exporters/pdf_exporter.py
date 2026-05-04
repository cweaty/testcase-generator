"""
PDF 导出器
使用 fpdf2 将测试用例导出为 PDF 格式，支持中文
"""
import os


def _find_cjk_font():
    """查找系统中的中文字体"""
    candidates = [
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        'C:/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/simsun.ttc',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def export_to_pdf(cases: list, title: str = '测试用例') -> bytes:
    """Export test cases to PDF using fpdf2 with CJK support"""
    from fpdf import FPDF

    font_path = _find_cjk_font()

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)

    if font_path:
        pdf.add_font('CJK', '', font_path)
        pdf.set_font('CJK', '', 16)
    else:
        pdf.set_font('Helvetica', 'B', 16)

    # Title
    pdf.add_page()
    pdf.cell(w=0, h=12, text=title, new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(4)

    # Subtitle with count
    if font_path:
        pdf.set_font('CJK', '', 9)
    else:
        pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(w=0, h=8, text=f'共 {len(cases)} 条测试用例', new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # Table header
    effective_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_widths = [8, 15, effective_width - 23]  # No, Priority, Title

    def _set_font(size):
        if font_path:
            pdf.set_font('CJK', '', size)
        else:
            pdf.set_font('Helvetica', '', size)

    # Header row
    _set_font(8)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    headers = ['序号', '优先级', '用例标题']
    for j, hdr in enumerate(headers):
        pdf.cell(w=col_widths[j], h=7, text=hdr, border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    # Data rows
    for i, tc in enumerate(cases, 1):
        # Check if we need a new page
        if pdf.get_y() > 265:
            pdf.add_page()
            # Re-print header
            _set_font(8)
            pdf.set_fill_color(50, 50, 50)
            pdf.set_text_color(255, 255, 255)
            for j, hdr in enumerate(headers):
                pdf.cell(w=col_widths[j], h=7, text=hdr, border=1, fill=True, align='C')
            pdf.ln()
            pdf.set_text_color(0, 0, 0)

        priority = tc.get('priority', 'P2')
        title_text = tc.get('title', '')
        row_h = 7

        # Alternating row color
        if i % 2 == 0:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)

        # Priority color
        priority_colors = {'P0': (220, 50, 50), 'P1': (230, 130, 50), 'P2': (50, 130, 200), 'P3': (128, 128, 128)}
        pc = priority_colors.get(priority, (128, 128, 128))

        _set_font(8)
        # Row number
        pdf.cell(w=col_widths[0], h=row_h, text=str(i), border=1, fill=True, align='C')
        # Priority with color
        pdf.set_text_color(*pc)
        pdf.cell(w=col_widths[1], h=row_h, text=priority, border=1, fill=True, align='C')
        pdf.set_text_color(0, 0, 0)
        # Title
        _set_font(8)
        # Truncate if too long
        max_title_chars = int(col_widths[2] / 2.5)  # rough estimate
        display_title = title_text[:max_title_chars] + '...' if len(title_text) > max_title_chars else title_text
        pdf.cell(w=col_widths[2], h=row_h, text=display_title, border=1, fill=True)
        pdf.ln()

        # Details row (collapsed by default, expand for first few or on demand)
        module = tc.get('module', '')
        steps = tc.get('steps', '')
        expected = tc.get('expected_result', '')

        if module or steps or expected:
            _set_font(7)
            pdf.set_fill_color(250, 250, 250)
            detail_x = pdf.l_margin + col_widths[0]
            detail_w = effective_width - col_widths[0]

            # Move to detail area
            pdf.cell(w=col_widths[0], h=0, text='', new_x="LMARGIN", new_y="TOP")
            pdf.set_x(detail_x)

            detail_lines = []
            if module:
                detail_lines.append(f'模块: {module}')
            if steps:
                step_text = steps.replace('\n', ' | ')
                if len(step_text) > 120:
                    step_text = step_text[:120] + '...'
                detail_lines.append(f'步骤: {step_text}')
            if expected:
                exp_text = expected.replace('\n', ' | ')
                if len(exp_text) > 120:
                    exp_text = exp_text[:120] + '...'
                detail_lines.append(f'预期: {exp_text}')

            detail_text = '  |  '.join(detail_lines)
            # Wrap in multi_cell
            y_before = pdf.get_y()
            pdf.set_x(detail_x)
            pdf.multi_cell(w=detail_w, h=4, text=detail_text, border='LRB', fill=True)
            pdf.ln(1)

    # Footer
    pdf.ln(10)
    _set_font(7)
    pdf.set_text_color(160, 160, 160)
    from datetime import datetime
    pdf.cell(w=0, h=5, text=f'Generated by AI 测试用例生成器 v3.4 | {datetime.now().strftime("%Y-%m-%d %H:%M")}',
             new_x="LMARGIN", new_y="NEXT", align='C')

    return bytes(pdf.output())
