"""
本地数据库模块
使用SQLite存储项目和章节数据

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class LocalDatabase:
    """本地数据库管理器"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        if db_path is None:
            # 默认使用用户目录
            home = Path.home()
            db_dir = home / '.ai_novel_generator'
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / 'novels.db'

        self.db_path = Path(db_path)
        self.conn = None
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute('PRAGMA foreign_keys = ON')
            self._create_tables()
            logger.info(f"[数据库] 数据库初始化成功: {self.db_path}")
        except Exception as e:
            logger.error(f"[数据库] 初始化失败: {e}")
            raise

    def _create_tables(self):
        """创建数据表"""
        cursor = self.conn.cursor()

        # 小说项目表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS novels (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                genre TEXT,
                topic TEXT,
                number_of_chapters INTEGER,
                word_number INTEGER,
                user_guidance TEXT,
                architecture TEXT,
                chapter_blueprint TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 章节表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                id TEXT PRIMARY KEY,
                novel_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                title TEXT,
                content TEXT,
                word_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
            )
        ''')

        # 生成日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT NOT NULL,
                message TEXT,
                level TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
            )
        ''')

        # 质量报告表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quality_reports (
                id TEXT PRIMARY KEY,
                novel_id TEXT NOT NULL,
                report_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
            )
        ''')

        self.conn.commit()

    # ========== 小说项目操作 ==========

    def save_novel(self, novel_id: str, novel_data: Dict[str, Any]) -> bool:
        """
        保存小说项目

        Args:
            novel_id: 项目ID
            novel_data: 项目数据

        Returns:
            是否保存成功
        """
        try:
            cursor = self.conn.cursor()

            # 检查是否已存在
            cursor.execute('SELECT id FROM novels WHERE id = ?', (novel_id,))
            exists = cursor.fetchone()

            if exists:
                # 更新
                cursor.execute('''
                    UPDATE novels SET
                        title = ?,
                        genre = ?,
                        topic = ?,
                        number_of_chapters = ?,
                        word_number = ?,
                        user_guidance = ?,
                        architecture = ?,
                        chapter_blueprint = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    novel_data.get('title', ''),
                    novel_data.get('genre', ''),
                    novel_data.get('topic', ''),
                    novel_data.get('number_of_chapters', 0),
                    novel_data.get('word_number', 0),
                    novel_data.get('user_guidance', ''),
                    json.dumps(novel_data.get('architecture', {})),
                    json.dumps(novel_data.get('chapter_blueprint', {})),
                    novel_id
                ))
            else:
                # 插入
                cursor.execute('''
                    INSERT INTO novels (
                        id, title, genre, topic, number_of_chapters,
                        word_number, user_guidance, architecture, chapter_blueprint
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    novel_id,
                    novel_data.get('title', ''),
                    novel_data.get('genre', ''),
                    novel_data.get('topic', ''),
                    novel_data.get('number_of_chapters', 0),
                    novel_data.get('word_number', 0),
                    novel_data.get('user_guidance', ''),
                    json.dumps(novel_data.get('architecture', {})),
                    json.dumps(novel_data.get('chapter_blueprint', {}))
                ))

            self.conn.commit()
            logger.info(f"[数据库] 小说项目已保存: {novel_id}")
            return True

        except Exception as e:
            logger.error(f"[数据库] 保存小说失败: {e}")
            return False

    def load_novel(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """
        加载小说项目

        Args:
            novel_id: 项目ID

        Returns:
            项目数据或None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM novels WHERE id = ?', (novel_id,))
            row = cursor.fetchone()

            if not row:
                return None

            columns = [desc[0] for desc in cursor.description]
            novel = dict(zip(columns, row))

            # 解析JSON字段
            novel['architecture'] = json.loads(novel.get('architecture', '{}'))
            novel['chapter_blueprint'] = json.loads(novel.get('chapter_blueprint', '{}'))

            return novel

        except Exception as e:
            logger.error(f"[数据库] 加载小说失败: {e}")
            return None

    def list_novels(self) -> List[Dict[str, Any]]:
        """
        列出所有小说项目

        Returns:
            项目列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT id, title, genre, topic, created_at, updated_at FROM novels ORDER BY updated_at DESC')
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"[数据库] 列出小说失败: {e}")
            return []

    def delete_novel(self, novel_id: str) -> bool:
        """
        删除小说项目

        Args:
            novel_id: 项目ID

        Returns:
            是否删除成功
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM novels WHERE id = ?', (novel_id,))
            self.conn.commit()
            logger.info(f"[数据库] 小说项目已删除: {novel_id}")
            return True

        except Exception as e:
            logger.error(f"[数据库] 删除小说失败: {e}")
            return False

    # ========== 章节操作 ==========

    def save_chapter(self, novel_id: str, chapter_number: int,
                     title: str, content: str, word_count: int = 0) -> bool:
        """
        保存章节

        Args:
            novel_id: 项目ID
            chapter_number: 章节号
            title: 标题
            content: 内容
            word_count: 字数

        Returns:
            是否保存成功
        """
        try:
            cursor = self.conn.cursor()
            chapter_id = f"{novel_id}_chapter_{chapter_number}"

            cursor.execute('''
                INSERT OR REPLACE INTO chapters
                (id, novel_id, chapter_number, title, content, word_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (chapter_id, novel_id, chapter_number, title, content, word_count))

            self.conn.commit()
            logger.debug(f"[数据库] 章节已保存: {chapter_id}")
            return True

        except Exception as e:
            logger.error(f"[数据库] 保存章节失败: {e}")
            return False

    def load_chapter(self, novel_id: str, chapter_number: int) -> Optional[Dict[str, Any]]:
        """
        加载章节

        Args:
            novel_id: 项目ID
            chapter_number: 章节号

        Returns:
            章节数据或None
        """
        try:
            cursor = self.conn.cursor()
            chapter_id = f"{novel_id}_chapter_{chapter_number}"
            cursor.execute('SELECT * FROM chapters WHERE id = ?', (chapter_id,))
            row = cursor.fetchone()

            if not row:
                return None

            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))

        except Exception as e:
            logger.error(f"[数据库] 加载章节失败: {e}")
            return None

    def list_chapters(self, novel_id: str) -> List[Dict[str, Any]]:
        """
        列出所有章节

        Args:
            novel_id: 项目ID

        Returns:
            章节列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'SELECT * FROM chapters WHERE novel_id = ? ORDER BY chapter_number',
                (novel_id,)
            )
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"[数据库] 列出章节失败: {e}")
            return []

    # ========== 日志操作 ==========

    def add_log(self, novel_id: str, message: str, level: str = 'info') -> bool:
        """
        添加日志

        Args:
            novel_id: 项目ID
            message: 日志消息
            level: 日志级别

        Returns:
            是否添加成功
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO generation_logs (novel_id, message, level)
                VALUES (?, ?, ?)
            ''', (novel_id, message, level))

            self.conn.commit()
            return True

        except Exception as e:
            logger.error(f"[数据库] 添加日志失败: {e}")
            return False

    def get_logs(self, novel_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取日志

        Args:
            novel_id: 项目ID
            limit: 限制数量

        Returns:
            日志列表
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT * FROM generation_logs
                WHERE novel_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (novel_id, limit))

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            logger.error(f"[数据库] 获取日志失败: {e}")
            return []

    # ========== 质量报告操作 ==========

    def save_quality_report(self, novel_id: str, report_data: Dict[str, Any]) -> bool:
        """
        保存质量报告

        Args:
            novel_id: 项目ID
            report_data: 报告数据

        Returns:
            是否保存成功
        """
        try:
            cursor = self.conn.cursor()
            report_id = f"{novel_id}_quality_report"

            cursor.execute('''
                INSERT OR REPLACE INTO quality_reports (id, novel_id, report_data)
                VALUES (?, ?, ?)
            ''', (report_id, novel_id, json.dumps(report_data)))

            self.conn.commit()
            logger.info(f"[数据库] 质量报告已保存: {report_id}")
            return True

        except Exception as e:
            logger.error(f"[数据库] 保存质量报告失败: {e}")
            return False

    def get_quality_report(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """
        获取质量报告

        Args:
            novel_id: 项目ID

        Returns:
            报告数据或None
        """
        try:
            cursor = self.conn.cursor()
            report_id = f"{novel_id}_quality_report"
            cursor.execute('SELECT report_data FROM quality_reports WHERE id = ?', (report_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return json.loads(row[0])

        except Exception as e:
            logger.error(f"[数据库] 获取质量报告失败: {e}")
            return None

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("[数据库] 数据库连接已关闭")

    def __del__(self):
        """析构函数"""
        self.close()


# 便捷函数
def create_database(db_path: str = None) -> LocalDatabase:
    """创建数据库实例"""
    return LocalDatabase(db_path)
