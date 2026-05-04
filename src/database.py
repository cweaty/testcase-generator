"""
数据库操作模块
使用 SQLite + aiosqlite 异步操作，支持连接池
"""
import aiosqlite
import os
import shutil
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from .config import settings

DB_PATH = settings.db_path


class ConnectionPool:
    """简单的连接池"""
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self._connections: List[aiosqlite.Connection] = []
        self._in_use: set = set()
    
    async def acquire(self) -> aiosqlite.Connection:
        """获取连接"""
        for conn in self._connections:
            if id(conn) not in self._in_use:
                self._in_use.add(id(conn))
                return conn
        
        if len(self._connections) < self.max_connections:
            conn = await aiosqlite.connect(DB_PATH)
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA busy_timeout=5000")
            self._connections.append(conn)
            self._in_use.add(id(conn))
            return conn
        
        # 等待并重试
        import asyncio
        await asyncio.sleep(0.1)
        return await self.acquire()
    
    async def release(self, conn: aiosqlite.Connection):
        """释放连接"""
        self._in_use.discard(id(conn))
    
    async def close_all(self):
        """关闭所有连接"""
        for conn in self._connections:
            await conn.close()
        self._connections.clear()
        self._in_use.clear()


# 全局连接池
pool = ConnectionPool()


@asynccontextmanager
async def get_db():
    """获取数据库连接的上下文管理器"""
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        await pool.release(conn)


async def init_db():
    """初始化数据库表"""
    async with get_db() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                content TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS testcases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL DEFAULT '',
                document_id INTEGER,
                module TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                precondition TEXT NOT NULL DEFAULT '',
                steps TEXT NOT NULL,
                expected_result TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'P2',
                case_type TEXT NOT NULL DEFAULT '功能测试',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );

            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_testcases_document_id ON testcases(document_id);
            CREATE INDEX IF NOT EXISTS idx_testcases_priority ON testcases(priority);
            CREATE INDEX IF NOT EXISTS idx_testcases_case_type ON testcases(case_type);
            CREATE TABLE IF NOT EXISTS deleted_testcases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_id INTEGER,
                case_id TEXT NOT NULL DEFAULT '',
                document_id INTEGER,
                module TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                precondition TEXT NOT NULL DEFAULT '',
                steps TEXT NOT NULL,
                expected_result TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'P2',
                case_type TEXT NOT NULL DEFAULT '功能测试',
                created_at TEXT NOT NULL,
                deleted_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS prompt_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                content TEXT NOT NULL,
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                target_type TEXT NOT NULL DEFAULT '',
                target_id INTEGER,
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_op_logs_created ON operation_logs(created_at);

            CREATE TABLE IF NOT EXISTS testcase_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                testcase_id INTEGER NOT NULL,
                case_id TEXT, module TEXT, title TEXT, precondition TEXT,
                steps TEXT, expected_result TEXT, priority TEXT, case_type TEXT,
                edited_by TEXT DEFAULT 'user', edit_reason TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_tc_history_tid ON testcase_history(testcase_id);

            CREATE TABLE IF NOT EXISTS generation_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL DEFAULT 'pending',
                task_type TEXT NOT NULL DEFAULT 'generate',
                document_id INTEGER,
                progress INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0,
                result TEXT DEFAULT '',
                error TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS test_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL DEFAULT '',
                tc_id INTEGER,
                title TEXT NOT NULL DEFAULT '',
                passed INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                steps_completed INTEGER DEFAULT 0,
                steps_total INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                run_dir TEXT DEFAULT '',
                code TEXT DEFAULT '',
                stdout TEXT DEFAULT '',
                stderr TEXT DEFAULT '',
                screenshots TEXT DEFAULT '[]',
                executed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_exec_tc_id ON test_executions(tc_id);
            CREATE INDEX IF NOT EXISTS idx_exec_passed ON test_executions(passed);
            CREATE INDEX IF NOT EXISTS idx_exec_at ON test_executions(executed_at);

            CREATE TABLE IF NOT EXISTS test_suites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                base_url TEXT DEFAULT 'http://localhost:3000',
                timeout INTEGER DEFAULT 30000,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS suite_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suite_id INTEGER NOT NULL,
                testcase_id INTEGER NOT NULL,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (suite_id) REFERENCES test_suites(id) ON DELETE CASCADE,
                FOREIGN KEY (testcase_id) REFERENCES testcases(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_sm_suite ON suite_members(suite_id);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sm_unique ON suite_members(suite_id, testcase_id);

            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suite_id INTEGER,
                cron_expr TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                last_run TEXT,
                next_run TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (suite_id) REFERENCES test_suites(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS execution_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suite_id INTEGER,
                suite_name TEXT DEFAULT '',
                total INTEGER DEFAULT 0,
                passed INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                report_html TEXT DEFAULT '',
                base_url TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
        """)

        # ---- FTS5 Full-Text Search (safe mode: standalone table, no triggers) ----
        # Triggers on content-sync FTS5 tables cause "malformed" on Windows.
        # We use a standalone FTS table rebuilt on-demand instead.
        try:
            await db.execute("DROP TRIGGER IF EXISTS tc_ai")
            await db.execute("DROP TRIGGER IF EXISTS tc_ad")
            await db.execute("DROP TRIGGER IF EXISTS tc_au")
            await db.execute("DROP TABLE IF EXISTS testcases_fts")
            await db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS testcases_fts USING fts5(
                title, module, steps, expected_result, precondition
            )""")
            # Populate if empty
            cursor = await db.execute("SELECT COUNT(*) as cnt FROM testcases_fts")
            cnt = (await cursor.fetchone())["cnt"]
            if cnt == 0:
                cursor2 = await db.execute("SELECT COUNT(*) as cnt FROM testcases")
                tc_cnt = (await cursor2.fetchone())["cnt"]
                if tc_cnt > 0:
                    await db.execute('''INSERT INTO testcases_fts(rowid, title, module, steps, expected_result, precondition)
                        SELECT id, title, module, steps, expected_result, precondition FROM testcases''')
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"FTS5 setup skipped (not supported): {e}")

        # ---- Migration: add missing columns ----
        try:
            await db.execute("ALTER TABLE documents ADD COLUMN file_size INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass  # column already exists

        # 初始化默认配置
        defaults = {
            "ai_base_url": settings.ai_base_url,
            "ai_api_key": settings.ai_api_key,
            "ai_model": settings.ai_model,
        }
        for key, value in defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)",
                (key, value)
            )

        # 初始化默认 Prompt 模板
        seed_templates = [
            ("默认模板", "默认系统内置模板", 1),
            ("详细用例", "你是一位资深的软件测试工程师。请生成详细的测试用例，要求：\n1. 每条用例步骤不少于5步\n2. 预期结果要精确到具体数值或状态\n3. 覆盖所有边界条件\n4. 包含性能和安全相关用例\n\n输出 JSON 数组格式。", 0),
            ("精简用例", "你是一位测试工程师。请生成精简的测试用例，要求：\n1. 每条用例步骤2-3步\n2. 聚焦核心功能\n3. 忽略边界场景\n\n输出 JSON 数组格式，字段同默认模板。", 0),
            ("接口专项", "你是一位接口测试专家。请专注于生成 API 接口测试用例，要求：\n1. 覆盖所有 HTTP 方法\n2. 测试参数校验（必填、类型、范围）\n3. 测试错误码和异常响应\n4. 包含权限和并发测试\n\n输出 JSON 数组格式，字段同默认模板。", 0),
            ("安全测试", "你是一位安全测试专家。请生成安全测试用例，要求：\n1. 覆盖 XSS、CSRF、SQL 注入等常见漏洞\n2. 测试越权访问和权限提升\n3. 测试输入验证和特殊字符处理\n4. 测试会话管理和认证机制\n\n输出 JSON 数组格式，字段同默认模板。", 0),
            ("性能测试", "你是一位性能测试专家。请生成性能测试用例，要求：\n1. 贺盖负载测试、压力测试、稳定性测试\n2. 测试并发访问和资源竞争\n3. 测试大数据量处理\n4. 测试响应时间和吞吐量指标\n\n输出 JSON 数组格式，字段同默认模板。", 0),
            ("兼容性测试", "你是一位兼容性测试专家。请生成兼容性测试用例，要求：\n1. 覆盖主流浏览器兼容性\n2. 测试不同分辨率和屏幕尺寸\n3. 测试移动端和桌面端差异\n4. 测试不同操作系统环境\n\n输出 JSON 数组格式，字段同默认模板。", 0),
        ]
        for name, content, is_default in seed_templates:
            exists = await db.execute("SELECT id FROM prompt_templates WHERE name = ?", (name,))
            if not await exists.fetchone():
                await db.execute(
                    "INSERT INTO prompt_templates (name, content, is_default) VALUES (?, ?, ?)",
                    (name, content, 1 if is_default else 0)
                )

        await db.commit()




# ========== 操作日志 ==========

async def log_operation(action: str, target_type: str = "", target_id: int = None, detail: str = ""):
    """记录操作日志"""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO operation_logs (action, target_type, target_id, detail) VALUES (?, ?, ?, ?)",
            (action, target_type, target_id, detail)
        )
        await db.commit()


async def get_operation_logs(page: int = 1, page_size: int = 50, action: str = "") -> Dict[str, Any]:
    """获取操作日志"""
    async with get_db() as db:
        where_clause = "WHERE 1=1"
        params = []
        if action:
            where_clause += " AND action = ?"
            params.append(action)

        cursor = await db.execute(f"SELECT COUNT(*) as total FROM operation_logs {where_clause}", params)
        total = (await cursor.fetchone())["total"]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM operation_logs {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()

        return {
            "logs": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }


async def get_testcases_by_ids(tc_ids: List[int]) -> List[Dict[str, Any]]:
    """批量获取测试用例"""
    async with get_db() as db:
        placeholders = ",".join(["?" for _ in tc_ids])
        cursor = await db.execute(f"SELECT * FROM testcases WHERE id IN ({placeholders})", tc_ids)
        return [dict(r) for r in await cursor.fetchall()]


# ========== 更多 Prompt 模板种子 ==========

# ========== 文档操作 ==========

async def insert_document(filename: str, doc_type: str, content: str, file_size: int = 0) -> int:
    """插入文档记录"""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO documents (filename, doc_type, content, file_size) VALUES (?, ?, ?, ?)",
            (filename, doc_type, content, file_size)
        )
        await db.commit()
        return cursor.lastrowid


async def get_document(doc_id: int) -> Optional[Dict[str, Any]]:
    """获取单个文档"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def list_documents(page: int = 1, page_size: int = 20, search: str = "") -> Dict[str, Any]:
    """获取文档列表（支持分页和搜索）"""
    async with get_db() as db:
        offset = (page - 1) * page_size
        
        # 构建查询
        where_clause = "WHERE 1=1"
        params = []
        
        if search:
            where_clause += " AND (filename LIKE ? OR content LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        # 获取总数
        count_query = f"SELECT COUNT(*) as total FROM documents {where_clause}"
        cursor = await db.execute(count_query, params)
        total = (await cursor.fetchone())["total"]
        
        # 获取数据
        data_query = f"""
            SELECT id, filename, doc_type, file_size, created_at,
                   SUBSTR(content, 1, 200) as content_preview
            FROM documents {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        cursor = await db.execute(data_query, params)
        rows = await cursor.fetchall()
        
        return {
            "documents": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }


async def delete_document(doc_id: int) -> bool:
    """删除文档及其关联的测试用例"""
    async with get_db() as db:
        # 先删除关联的测试用例
        await db.execute("DELETE FROM testcases WHERE document_id = ?", (doc_id,))
        # 再删除文档
        cursor = await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        await db.commit()
        return cursor.rowcount > 0


async def delete_documents_batch(doc_ids: List[int]) -> int:
    """批量删除文档"""
    async with get_db() as db:
        placeholders = ",".join(["?" for _ in doc_ids])
        # 先删除关联的测试用例
        await db.execute(f"DELETE FROM testcases WHERE document_id IN ({placeholders})", doc_ids)
        # 再删除文档
        cursor = await db.execute(f"DELETE FROM documents WHERE id IN ({placeholders})", doc_ids)
        await db.commit()
        return cursor.rowcount


# ========== 测试用例操作 ==========

async def insert_testcase(tc: Dict[str, Any]) -> int:
    """插入测试用例"""
    async with get_db() as db:
        cursor = await db.execute(
            """INSERT INTO testcases (case_id, document_id, module, title, precondition,
               steps, expected_result, priority, case_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tc.get("case_id", ""), tc.get("document_id"), tc.get("module", ""),
             tc["title"], tc.get("precondition", ""), tc["steps"],
             tc["expected_result"], tc.get("priority", "P2"), tc.get("case_type", "功能测试"))
        )
        await db.commit()
        return cursor.lastrowid


async def insert_testcases_batch(tcs: List[Dict[str, Any]]) -> int:
    """批量插入测试用例"""
    async with get_db() as db:
        count = 0
        for tc in tcs:
            await db.execute(
                """INSERT INTO testcases (case_id, document_id, module, title, precondition,
                   steps, expected_result, priority, case_type)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tc.get("case_id", ""), tc.get("document_id"), tc.get("module", ""),
                 tc["title"], tc.get("precondition", ""), tc["steps"],
                 tc["expected_result"], tc.get("priority", "P2"), tc.get("case_type", "功能测试"))
            )
            count += 1
        await db.commit()
        return count


async def get_testcases(
    document_id: Optional[int] = None,
    priority: Optional[str] = None,
    case_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    **kwargs
) -> Dict[str, Any]:
    """获取测试用例列表（支持筛选、搜索、分页）"""
    async with get_db() as db:
        where_clause = "WHERE 1=1"
        params = []
        
        if document_id:
            where_clause += " AND document_id = ?"
            params.append(document_id)
        if priority:
            where_clause += " AND priority = ?"
            params.append(priority)
        if case_type:
            where_clause += " AND case_type = ?"
            params.append(case_type)
        
        use_fts = False
        if search:
            # Try FTS5 first, fallback to LIKE
            try:
                fts_query = '"' + search.replace('"', '""') + '"*'
                fts_count = await db.execute(
                    f"SELECT COUNT(*) as cnt FROM testcases_fts WHERE testcases_fts MATCH ?",
                    (fts_query,)
                )
                _ = await fts_count.fetchone()  # test if FTS works
                use_fts = True
                where_clause += " AND testcases.id IN (SELECT rowid FROM testcases_fts WHERE testcases_fts MATCH ?)"
                params.append(fts_query)
            except Exception:
                where_clause += " AND (title LIKE ? OR steps LIKE ? OR expected_result LIKE ? OR module LIKE ?)"
                params.extend([f"%{search}%"] * 4)
        
        # 获取总数
        count_query = f"SELECT COUNT(*) as total FROM testcases {where_clause}"
        cursor = await db.execute(count_query, params)
        total = (await cursor.fetchone())["total"]
        
        # 获取统计数据
        stats_query = f"""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN priority = 'P0' THEN 1 ELSE 0 END) as p0_count,
                SUM(CASE WHEN priority = 'P1' THEN 1 ELSE 0 END) as p1_count,
                SUM(CASE WHEN priority = 'P2' THEN 1 ELSE 0 END) as p2_count,
                SUM(CASE WHEN priority = 'P3' THEN 1 ELSE 0 END) as p3_count
            FROM testcases {where_clause}
        """
        cursor = await db.execute(stats_query, params)
        stats = dict(await cursor.fetchone())
        
        # 排序
        sort_by = kwargs.get("sort_by", "priority")
        sort_order = kwargs.get("sort_order", "asc")
        order_dir = "DESC" if sort_order == "desc" else "ASC"

        sort_map = {
            "priority": f"""CASE priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 WHEN 'P2' THEN 3 WHEN 'P3' THEN 4 ELSE 5 END {'DESC' if sort_order == 'desc' else 'ASC'}""",
            "id": f"id {order_dir}",
            "title": f"title {order_dir}",
            "module": f"module {order_dir}",
            "case_type": f"case_type {order_dir}",
            "created_at": f"created_at {order_dir}",
        }
        order_clause = sort_map.get(sort_by, sort_map["priority"])

        # 获取数据
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT * FROM testcases {where_clause}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        cursor = await db.execute(data_query, params)
        rows = await cursor.fetchall()
        
        return {
            "testcases": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "stats": stats
        }


async def get_testcase(tc_id: int) -> Optional[Dict[str, Any]]:
    """获取单个测试用例"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM testcases WHERE id = ?", (tc_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_testcase(tc_id: int, updates: Dict[str, Any]) -> bool:
    """更新测试用例"""
    if not updates:
        return False
    
    async with get_db() as db:
        updates["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [tc_id]
        cursor = await db.execute(f"UPDATE testcases SET {set_clause} WHERE id = ?", values)
        await db.commit()
        return cursor.rowcount > 0


async def delete_testcase(tc_id: int) -> bool:
    """删除测试用例（移入回收站）"""
    async with get_db() as db:
        # 先获取用例数据
        cursor = await db.execute("SELECT * FROM testcases WHERE id = ?", (tc_id,))
        row = await cursor.fetchone()
        if not row:
            return False
        tc = dict(row)
        # 移入回收站
        await db.execute(
            """INSERT INTO deleted_testcases (original_id, case_id, document_id, module, title,
               precondition, steps, expected_result, priority, case_type, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tc["id"], tc.get("case_id", ""), tc.get("document_id"),
             tc.get("module", ""), tc["title"], tc.get("precondition", ""),
             tc["steps"], tc["expected_result"], tc.get("priority", "P2"),
             tc.get("case_type", "功能测试"), tc.get("created_at", ""))
        )
        # 删除原记录
        await db.execute("DELETE FROM testcases WHERE id = ?", (tc_id,))
        await db.commit()
        return True


async def delete_testcases_batch(tc_ids: List[int]) -> int:
    """批量删除测试用例（移入回收站）"""
    async with get_db() as db:
        placeholders = ",".join(["?" for _ in tc_ids])
        # 获取待删除数据
        cursor = await db.execute(f"SELECT * FROM testcases WHERE id IN ({placeholders})", tc_ids)
        rows = [dict(r) for r in await cursor.fetchall()]
        # 移入回收站
        for tc in rows:
            await db.execute(
                """INSERT INTO deleted_testcases (original_id, case_id, document_id, module, title,
                   precondition, steps, expected_result, priority, case_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tc["id"], tc.get("case_id", ""), tc.get("document_id"),
                 tc.get("module", ""), tc["title"], tc.get("precondition", ""),
                 tc["steps"], tc["expected_result"], tc.get("priority", "P2"),
                 tc.get("case_type", "功能测试"), tc.get("created_at", ""))
            )
        # 删除原记录
        cursor = await db.execute(f"DELETE FROM testcases WHERE id IN ({placeholders})", tc_ids)
        await db.commit()
        return cursor.rowcount


async def delete_testcases_by_document(document_id: int) -> int:
    """删除某文档下的所有测试用例（移入回收站）"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM testcases WHERE document_id = ?", (document_id,))
        rows = [dict(r) for r in await cursor.fetchall()]
        for tc in rows:
            await db.execute(
                """INSERT INTO deleted_testcases (original_id, case_id, document_id, module, title,
                   precondition, steps, expected_result, priority, case_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tc["id"], tc.get("case_id", ""), tc.get("document_id"),
                 tc.get("module", ""), tc["title"], tc.get("precondition", ""),
                 tc["steps"], tc["expected_result"], tc.get("priority", "P2"),
                 tc.get("case_type", "功能测试"), tc.get("created_at", ""))
            )
        cursor = await db.execute("DELETE FROM testcases WHERE document_id = ?", (document_id,))
        await db.commit()
        return cursor.rowcount


# ========== 回收站操作 ==========

async def get_deleted_testcases(
    page: int = 1,
    page_size: int = 50,
    search: str = ""
) -> Dict[str, Any]:
    """获取回收站中的测试用例"""
    async with get_db() as db:
        where_clause = "WHERE 1=1"
        params = []
        if search:
            where_clause += " AND (title LIKE ? OR steps LIKE ? OR module LIKE ?)"
            params.extend([f"%{search}%"] * 3)

        # 总数
        cursor = await db.execute(f"SELECT COUNT(*) as total FROM deleted_testcases {where_clause}", params)
        total = (await cursor.fetchone())["total"]

        # 数据
        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM deleted_testcases {where_clause} ORDER BY deleted_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()

        return {
            "testcases": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }


async def restore_testcase(trash_id: int) -> bool:
    """从回收站恢复测试用例"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM deleted_testcases WHERE id = ?", (trash_id,))
        row = await cursor.fetchone()
        if not row:
            return False
        tc = dict(row)
        # 恢复到原表
        await db.execute(
            """INSERT INTO testcases (case_id, document_id, module, title, precondition,
               steps, expected_result, priority, case_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tc.get("case_id", ""), tc.get("document_id"), tc.get("module", ""),
             tc["title"], tc.get("precondition", ""), tc["steps"],
             tc["expected_result"], tc.get("priority", "P2"), tc.get("case_type", "功能测试"))
        )
        # 从回收站删除
        await db.execute("DELETE FROM deleted_testcases WHERE id = ?", (trash_id,))
        await db.commit()
        return True


async def restore_testcases_batch(trash_ids: List[int]) -> int:
    """批量从回收站恢复"""
    count = 0
    for tid in trash_ids:
        if await restore_testcase(tid):
            count += 1
    return count


async def permanently_delete_testcase(trash_id: int) -> bool:
    """永久删除回收站中的测试用例"""
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM deleted_testcases WHERE id = ?", (trash_id,))
        await db.commit()
        return cursor.rowcount > 0


async def permanently_delete_batch(trash_ids: List[int]) -> int:
    """批量永久删除"""
    async with get_db() as db:
        placeholders = ",".join(["?" for _ in trash_ids])
        cursor = await db.execute(f"DELETE FROM deleted_testcases WHERE id IN ({placeholders})", trash_ids)
        await db.commit()
        return cursor.rowcount


async def empty_trash() -> int:
    """清空回收站"""
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM deleted_testcases")
        await db.commit()
        return cursor.rowcount


# ========== Prompt 模板操作 ==========

async def get_prompt_templates() -> List[Dict[str, Any]]:
    """获取所有 Prompt 模板"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM prompt_templates ORDER BY is_default DESC, id ASC")
        return [dict(r) for r in await cursor.fetchall()]


async def get_prompt_template(template_id: int) -> Optional[Dict[str, Any]]:
    """获取单个 Prompt 模板"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM prompt_templates WHERE id = ?", (template_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_prompt_template(name: str, content: str, is_default: bool = False) -> int:
    """创建 Prompt 模板"""
    async with get_db() as db:
        if is_default:
            await db.execute("UPDATE prompt_templates SET is_default = 0")
        cursor = await db.execute(
            "INSERT INTO prompt_templates (name, content, is_default) VALUES (?, ?, ?)",
            (name, content, 1 if is_default else 0)
        )
        await db.commit()
        return cursor.lastrowid


async def update_prompt_template(template_id: int, name: str = None, content: str = None, is_default: bool = None) -> bool:
    """更新 Prompt 模板"""
    async with get_db() as db:
        updates = {}
        if name is not None:
            updates["name"] = name
        if content is not None:
            updates["content"] = content
        if is_default is not None:
            if is_default:
                await db.execute("UPDATE prompt_templates SET is_default = 0")
            updates["is_default"] = 1 if is_default else 0
        if not updates:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        cursor = await db.execute(f"UPDATE prompt_templates SET {set_clause} WHERE id = ?", list(updates.values()) + [template_id])
        await db.commit()
        return cursor.rowcount > 0


async def delete_prompt_template(template_id: int) -> bool:
    """删除 Prompt 模板"""
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM prompt_templates WHERE id = ?", (template_id,))
        await db.commit()
        return cursor.rowcount > 0


# ========== 配置操作 ==========

async def get_config(key: str) -> Optional[str]:
    """获取配置项"""
    async with get_db() as db:
        cursor = await db.execute("SELECT value FROM app_config WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else None


async def get_all_config() -> Dict[str, str]:
    """获取所有配置"""
    async with get_db() as db:
        cursor = await db.execute("SELECT key, value FROM app_config")
        rows = await cursor.fetchall()
        return {r["key"]: r["value"] for r in rows}


async def set_config(key: str, value: str):
    """设置配置项"""
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)", (key, value)
        )
        await db.commit()


# ========== 版本历史操作 ==========

async def save_testcase_history(tc_id: int, tc_data: Dict[str, Any], edit_reason: str = ""):
    """保存测试用例当前状态到历史记录"""
    async with get_db() as db:
        await db.execute(
            """INSERT INTO testcase_history
               (testcase_id, case_id, module, title, precondition,
                steps, expected_result, priority, case_type, edited_by, edit_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tc_id, tc_data.get("case_id", ""), tc_data.get("module", ""),
             tc_data.get("title", ""), tc_data.get("precondition", ""),
             tc_data.get("steps", ""), tc_data.get("expected_result", ""),
             tc_data.get("priority", "P2"), tc_data.get("case_type", "功能测试"),
             tc_data.get("edited_by", "user"), edit_reason)
        )
        await db.commit()


async def get_testcase_history(tc_id: int) -> List[Dict[str, Any]]:
    """获取测试用例的版本历史"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM testcase_history WHERE testcase_id = ? ORDER BY created_at DESC",
            (tc_id,)
        )
        return [dict(r) for r in await cursor.fetchall()]


async def restore_from_history(history_id: int) -> Optional[Dict[str, Any]]:
    """从历史版本恢复测试用例"""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM testcase_history WHERE id = ?", (history_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        h = dict(row)
        tc_id = h["testcase_id"]
        # Check the test case still exists
        cursor = await db.execute("SELECT * FROM testcases WHERE id = ?", (tc_id,))
        if not await cursor.fetchone():
            return None
        # Save current state as a new history entry before restoring
        cursor = await db.execute("SELECT * FROM testcases WHERE id = ?", (tc_id,))
        current = dict(await cursor.fetchone())
        await db.execute(
            """INSERT INTO testcase_history
               (testcase_id, case_id, module, title, precondition,
                steps, expected_result, priority, case_type, edited_by, edit_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'system', 'auto-save before restore')""",
            (tc_id, current.get("case_id", ""), current.get("module", ""),
             current.get("title", ""), current.get("precondition", ""),
             current.get("steps", ""), current.get("expected_result", ""),
             current.get("priority", "P2"), current.get("case_type", "功能测试"))
        )
        # Restore the fields from history
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await db.execute(
            """UPDATE testcases SET
               case_id = ?, module = ?, title = ?, precondition = ?,
               steps = ?, expected_result = ?, priority = ?, case_type = ?,
               updated_at = ?
               WHERE id = ?""",
            (h.get("case_id", ""), h.get("module", ""), h.get("title", ""),
             h.get("precondition", ""), h.get("steps", ""),
             h.get("expected_result", ""), h.get("priority", "P2"),
             h.get("case_type", "功能测试"), now, tc_id)
        )
        await db.commit()
        return {"id": tc_id, "restored_from_history_id": history_id}


# ========== 任务队列操作 ==========

async def create_task(task_type: str, document_id: int = None) -> int:
    """创建生成任务"""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO generation_tasks (task_type, document_id) VALUES (?, ?)",
            (task_type, document_id)
        )
        await db.commit()
        return cursor.lastrowid


async def update_task(task_id: int, **kwargs):
    """更新任务状态/进度"""
    if not kwargs:
        return
    async with get_db() as db:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [task_id]
        await db.execute(f"UPDATE generation_tasks SET {set_clause} WHERE id = ?", values)
        await db.commit()


async def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    """获取任务状态"""
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM generation_tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_task(task_id: int) -> bool:
    """删除任务"""
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM generation_tasks WHERE id = ?", (task_id,))
        await db.commit()
        return cursor.rowcount > 0


async def list_tasks(page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    """列出所有任务"""
    async with get_db() as db:
        offset = (page - 1) * page_size
        cursor = await db.execute("SELECT COUNT(*) as total FROM generation_tasks")
        total = (await cursor.fetchone())["total"]
        cursor = await db.execute(
            "SELECT * FROM generation_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset)
        )
        rows = await cursor.fetchall()
        return {
            "tasks": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }


# ========== FTS 索引重建 ==========

async def rebuild_fts_index():
    """重建 FTS5 全文搜索索引"""
    async with get_db() as db:
        try:
            await db.execute('DROP TABLE IF EXISTS testcases_fts')
            await db.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS testcases_fts USING fts5(
                title, module, steps, expected_result, precondition,
                content='testcases', content_rowid='id')''')
            await db.execute('''INSERT INTO testcases_fts(rowid, title, module, steps, expected_result, precondition)
                SELECT id, title, module, steps, expected_result, precondition FROM testcases''')
            await db.commit()
        except Exception as e:
            raise Exception(f"FTS 索引重建失败: {e}")


# ========== 数据库备份与统计 ==========

async def backup_database(backup_path: str) -> str:
    """Create a backup of the database using file copy"""
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


async def get_database_stats() -> dict:
    """Get database size and table stats"""
    async with get_db() as db:
        stats = {}
        for table in ['documents', 'testcases', 'deleted_testcases', 'app_config', 'prompt_templates', 'operation_logs', 'testcase_history', 'generation_tasks']:
            cursor = await db.execute(f'SELECT COUNT(*) as cnt FROM {table}')
            row = await cursor.fetchone()
            stats[table] = row['cnt']
        stats['db_size_bytes'] = os.path.getsize(DB_PATH)
        return stats
