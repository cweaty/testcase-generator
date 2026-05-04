"""
Playwright 自动化测试执行模块
- AI 代码生成：将测试用例转为 Playwright Python 脚本
- 脚本执行：运行生成的脚本并收集结果
- 截图管理：保存测试过程截图
- 测试套件：管理用例集合，一键执行
- 环境检测：检查 Playwright/PyMuPDF 依赖
- 报告生成：HTML 测试报告
"""
from .runner import (
    generate_code,
    generate_batch_code,
    run_script,
    execute_testcase,
    execute_testcases_batch,
    RESULTS_DIR,
)
from .suites import (
    create_suite, update_suite, delete_suite, get_suite, list_suites,
    add_suite_member, add_suite_members_batch, remove_suite_member, clear_suite_members,
)
from .report import generate_report_html
from .env_check import check_all
