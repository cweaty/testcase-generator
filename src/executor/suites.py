"""
测试套件管理 — 创建/编辑/删除套件，管理成员用例，一键执行
"""
import json
import logging
from typing import List, Dict, Any, Optional
from ..database import get_db, log_operation

logger = logging.getLogger(__name__)


async def create_suite(name: str, description: str = "", base_url: str = "http://localhost:3000", timeout: int = 30000) -> int:
    """创建测试套件，返回 ID"""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO test_suites (name, description, base_url, timeout) VALUES (?, ?, ?, ?)",
            (name, description, base_url, timeout)
        )
        await db.commit()
        suite_id = cursor.lastrowid
    await log_operation("create", "suite", suite_id, f"创建套件: {name}")
    return suite_id


async def update_suite(suite_id: int, **kwargs) -> bool:
    """更新套件信息"""
    allowed = {"name", "description", "base_url", "timeout"}
    fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [suite_id]
    async with get_db() as db:
        cursor = await db.execute(
            f"UPDATE test_suites SET {set_clause}, updated_at = datetime('now', 'localtime') WHERE id = ?",
            values
        )
        await db.commit()
        return cursor.rowcount > 0


async def delete_suite(suite_id: int) -> bool:
    """删除套件及成员关系"""
    async with get_db() as db:
        await db.execute("DELETE FROM suite_members WHERE suite_id = ?", (suite_id,))
        cursor = await db.execute("DELETE FROM test_suites WHERE id = ?", (suite_id,))
        await db.commit()
        deleted = cursor.rowcount > 0
    if deleted:
        await log_operation("delete", "suite", suite_id, "删除套件")
    return deleted


async def get_suite(suite_id: int) -> Optional[Dict[str, Any]]:
    """获取单个套件详情（含成员用例列表）"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM test_suites WHERE id = ?", (suite_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        suite = dict(row)

        cursor = await db.execute(
            """SELECT sm.id as member_id, sm.sort_order, t.*
               FROM suite_members sm
               JOIN testcases t ON sm.testcase_id = t.id
               WHERE sm.suite_id = ?
               ORDER BY sm.sort_order, t.id""",
            (suite_id,)
        )
        suite["members"] = [dict(r) for r in await cursor.fetchall()]
        suite["member_count"] = len(suite["members"])
    return suite


async def list_suites() -> List[Dict[str, Any]]:
    """列出所有套件（含成员数量）"""
    async with get_db() as db:
        cursor = await db.execute(
            """SELECT s.*, COUNT(sm.id) as member_count
               FROM test_suites s
               LEFT JOIN suite_members sm ON sm.suite_id = s.id
               GROUP BY s.id
               ORDER BY s.updated_at DESC"""
        )
        return [dict(r) for r in await cursor.fetchall()]


async def add_suite_member(suite_id: int, testcase_id: int, sort_order: int = 0) -> bool:
    """向套件添加用例"""
    async with get_db() as db:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO suite_members (suite_id, testcase_id, sort_order) VALUES (?, ?, ?)",
                (suite_id, testcase_id, sort_order)
            )
            await db.commit()
            await db.execute(
                "UPDATE test_suites SET updated_at = datetime('now', 'localtime') WHERE id = ?",
                (suite_id,)
            )
            await db.commit()
            return True
        except Exception:
            return False


async def add_suite_members_batch(suite_id: int, testcase_ids: List[int]) -> int:
    """批量添加用例到套件"""
    added = 0
    async with get_db() as db:
        for i, tc_id in enumerate(testcase_ids):
            try:
                await db.execute(
                    "INSERT OR IGNORE INTO suite_members (suite_id, testcase_id, sort_order) VALUES (?, ?, ?)",
                    (suite_id, tc_id, i)
                )
                added += 1
            except Exception:
                pass
        await db.commit()
        await db.execute(
            "UPDATE test_suites SET updated_at = datetime('now', 'localtime') WHERE id = ?",
            (suite_id,)
        )
        await db.commit()
    return added


async def remove_suite_member(suite_id: int, testcase_id: int) -> bool:
    """从套件移除用例"""
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM suite_members WHERE suite_id = ? AND testcase_id = ?",
            (suite_id, testcase_id)
        )
        await db.commit()
        return cursor.rowcount > 0


async def clear_suite_members(suite_id: int) -> int:
    """清空套件所有成员"""
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM suite_members WHERE suite_id = ?", (suite_id,))
        await db.commit()
        return cursor.rowcount
