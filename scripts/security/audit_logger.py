#!/usr/bin/env python3
"""
审计日志系统
记录项目分析操作日志，支持追溯和审计

特性：
- 结构化日志记录
- 日志轮转
- 敏感操作追踪
- 查询和过滤
"""

import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import threading


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class OperationType(Enum):
    """操作类型"""
    SCAN = "scan"                    # 项目扫描
    ANALYZE = "analyze"              # 代码分析
    DETECT = "detect"                # 项目检测
    CACHE_UPDATE = "cache_update"    # 缓存更新
    CACHE_CLEAR = "cache_clear"      # 缓存清除
    QA_QUERY = "qa_query"            # 问答查询
    QA_CACHE = "qa_cache"            # 问答缓存
    SENSITIVE_ACCESS = "sensitive_access"  # 敏感文件访问
    SENSITIVE_MASK = "sensitive_mask"      # 敏感信息脱敏
    FILE_READ = "file_read"          # 文件读取
    FILE_WRITE = "file_write"        # 文件写入
    CONFIG_CHANGE = "config_change"  # 配置变更
    EXPORT = "export"                # 数据导出
    IMPORT = "import"                # 数据导入


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: str
    level: str
    operation: str
    user: str = "system"
    details: Dict[str, Any] = field(default_factory=dict)
    file_path: str = ""
    duration_ms: int = 0
    success: bool = True
    error_message: str = ""
    session_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'level': self.level,
            'operation': self.operation,
            'user': self.user,
            'details': self.details,
            'file_path': self.file_path,
            'duration_ms': self.duration_ms,
            'success': self.success,
            'error_message': self.error_message,
            'session_id': self.session_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        return cls(
            timestamp=data.get('timestamp', ''),
            level=data.get('level', 'info'),
            operation=data.get('operation', ''),
            user=data.get('user', 'system'),
            details=data.get('details', {}),
            file_path=data.get('file_path', ''),
            duration_ms=data.get('duration_ms', 0),
            success=data.get('success', True),
            error_message=data.get('error_message', ''),
            session_id=data.get('session_id', ''),
        )


class AuditLogger:
    """审计日志记录器"""

    DEFAULT_LOG_FILE = '.projmeta/audit.log'
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    ROTATION_COUNT = 5

    # 日志级别权重
    LEVEL_WEIGHTS = {
        'debug': 0,
        'info': 1,
        'warn': 2,
        'error': 3,
    }

    def __init__(self, project_dir: str, config: Dict[str, Any] = None):
        """初始化审计日志器

        Args:
            project_dir: 项目目录
            config: 审计配置
        """
        self.project_dir = Path(project_dir).resolve()
        config = config or {}

        self.enabled = config.get('enabled', True)
        self.log_level = config.get('log_level', 'info')
        self.max_log_size = config.get('max_log_size_mb', 10) * 1024 * 1024
        self.rotation_count = config.get('log_rotation_count', 5)

        self._log_file = self.project_dir / config.get('log_file', self.DEFAULT_LOG_FILE)
        self._lock = threading.Lock()
        self._session_id = self._generate_session_id()

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]

    @property
    def log_file(self) -> Path:
        return self._log_file

    def _should_log(self, level: str) -> bool:
        """判断是否应记录日志"""
        level_weight = self.LEVEL_WEIGHTS.get(level, 0)
        min_weight = self.LEVEL_WEIGHTS.get(self.log_level, 1)
        return level_weight >= min_weight

    def log_operation(self, operation: str, details: Dict[str, Any] = None,
                      file_path: str = "", duration_ms: int = 0,
                      success: bool = True, error_message: str = "",
                      level: str = "info", user: str = "system") -> None:
        """记录操作日志

        Args:
            operation: 操作类型
            details: 操作详情
            file_path: 涉及的文件路径
            duration_ms: 操作耗时（毫秒）
            success: 是否成功
            error_message: 错误信息
            level: 日志级别
            user: 操作用户
        """
        if not self.enabled:
            return

        if not self._should_log(level):
            return

        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            operation=operation,
            user=user,
            details=details or {},
            file_path=file_path,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            session_id=self._session_id,
        )

        self._write_entry(entry)

    def _write_entry(self, entry: LogEntry) -> None:
        """写入日志条目"""
        with self._lock:
            # 确保目录存在
            self._log_file.parent.mkdir(parents=True, exist_ok=True)

            # 检查日志轮转
            self._check_rotation()

            # 写入日志
            try:
                with open(self._log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + '\n')
            except Exception as e:
                print(f"Warning: Failed to write audit log: {e}")

    def _check_rotation(self) -> None:
        """检查并执行日志轮转"""
        if not self._log_file.exists():
            return

        try:
            size = self._log_file.stat().st_size
            if size >= self.max_log_size:
                self._rotate_logs()
        except Exception:
            pass

    def _rotate_logs(self) -> None:
        """执行日志轮转"""
        # 删除最旧的日志
        oldest = self._log_file.with_suffix(f'.log.{self.rotation_count}')
        if oldest.exists():
            oldest.unlink()

        # 重命名现有日志
        for i in range(self.rotation_count - 1, 0, -1):
            old_file = self._log_file.with_suffix(f'.log.{i}')
            new_file = self._log_file.with_suffix(f'.log.{i + 1}')
            if old_file.exists():
                old_file.rename(new_file)

        # 重命名当前日志
        if self._log_file.exists():
            rotated = self._log_file.with_suffix('.log.1')
            self._log_file.rename(rotated)

    def log_sensitive_access(self, file: str, action: str,
                             masked: bool = True) -> None:
        """记录敏感文件访问

        Args:
            file: 文件路径
            action: 操作（read/write/delete）
            masked: 是否已脱敏
        """
        self.log_operation(
            operation=OperationType.SENSITIVE_ACCESS.value,
            file_path=file,
            level="warn",
            details={
                'action': action,
                'masked': masked,
            }
        )

    def log_scan(self, scanned_files: int, sensitive_found: int,
                 duration_ms: int) -> None:
        """记录扫描操作"""
        self.log_operation(
            operation=OperationType.SCAN.value,
            level="info",
            details={
                'scanned_files': scanned_files,
                'sensitive_found': sensitive_found,
            },
            duration_ms=duration_ms,
        )

    def log_analyze(self, analyzer: str, files: int,
                    duration_ms: int, success: bool = True) -> None:
        """记录分析操作"""
        self.log_operation(
            operation=OperationType.ANALYZE.value,
            level="info",
            details={
                'analyzer': analyzer,
                'files': files,
            },
            duration_ms=duration_ms,
            success=success,
        )

    def log_qa_query(self, question: str, cached: bool,
                     similarity: float = 0.0) -> None:
        """记录问答查询"""
        self.log_operation(
            operation=OperationType.QA_QUERY.value,
            level="info",
            details={
                'question_hash': hashlib.md5(question.encode()).hexdigest()[:8],
                'cached': cached,
                'similarity': similarity,
            }
        )

    def get_audit_trail(self, filters: Dict[str, Any] = None,
                        limit: int = 100) -> List[LogEntry]:
        """获取审计记录

        Args:
            filters: 过滤条件
            limit: 最大数量

        Returns:
            日志条目列表
        """
        filters = filters or {}
        entries = []

        if not self._log_file.exists():
            return entries

        try:
            with open(self._log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-limit * 2:]  # 多读一些以应对过滤

            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    entry = LogEntry.from_dict(data)

                    # 应用过滤条件
                    if self._matches_filter(entry, filters):
                        entries.append(entry)

                    if len(entries) >= limit:
                        break

                except json.JSONDecodeError:
                    continue

        except Exception as e:
            print(f"Warning: Failed to read audit log: {e}")

        return entries

    def _matches_filter(self, entry: LogEntry, filters: Dict[str, Any]) -> bool:
        """判断日志条目是否匹配过滤条件"""
        if 'operation' in filters:
            if entry.operation != filters['operation']:
                return False

        if 'level' in filters:
            if entry.level != filters['level']:
                return False

        if 'success' in filters:
            if entry.success != filters['success']:
                return False

        if 'file_path' in filters:
            if filters['file_path'] not in entry.file_path:
                return False

        if 'since' in filters:
            try:
                entry_time = datetime.fromisoformat(entry.timestamp)
                since_time = datetime.fromisoformat(filters['since'])
                if entry_time < since_time:
                    return False
            except Exception:
                pass

        return True

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """获取审计统计

        Args:
            days: 统计天数

        Returns:
            统计数据
        """
        since = (datetime.now() - timedelta(days=days)).isoformat()
        entries = self.get_audit_trail({'since': since}, limit=10000)

        stats = {
            'total_operations': len(entries),
            'by_operation': {},
            'by_level': {},
            'success_rate': 0,
            'unique_users': set(),
            'unique_files': set(),
        }

        success_count = 0
        for entry in entries:
            # 按操作统计
            stats['by_operation'][entry.operation] = \
                stats['by_operation'].get(entry.operation, 0) + 1

            # 按级别统计
            stats['by_level'][entry.level] = \
                stats['by_level'].get(entry.level, 0) + 1

            # 成功率
            if entry.success:
                success_count += 1

            # 唯一用户
            stats['unique_users'].add(entry.user)

            # 唯一文件
            if entry.file_path:
                stats['unique_files'].add(entry.file_path)

        stats['success_rate'] = success_count / len(entries) if entries else 1.0
        stats['unique_users'] = len(stats['unique_users'])
        stats['unique_files'] = len(stats['unique_files'])

        return stats

    def cleanup_old_logs(self, days: int = 90) -> int:
        """清理旧日志

        Args:
            days: 保留天数

        Returns:
            清理的条目数
        """
        cutoff = datetime.now() - timedelta(days=days)
        entries = self.get_audit_trail(limit=100000)
        removed = 0

        new_entries = []
        for entry in entries:
            try:
                entry_time = datetime.fromisoformat(entry.timestamp)
                if entry_time >= cutoff:
                    new_entries.append(entry)
                else:
                    removed += 1
            except Exception:
                new_entries.append(entry)

        # 重写日志文件
        if removed > 0:
            with self._lock:
                try:
                    with open(self._log_file, 'w', encoding='utf-8') as f:
                        for entry in reversed(new_entries):
                            f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + '\n')
                except Exception as e:
                    print(f"Warning: Failed to cleanup audit log: {e}")

        return removed


def get_audit_logger(project_dir: str, config: Dict[str, Any] = None) -> AuditLogger:
    """获取审计日志器的便捷函数"""
    return AuditLogger(project_dir, config)


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: audit_logger.py <command> <project_dir> [args]")
        print("\nCommands:")
        print("  tail [project_dir] [-n N]  Show last N log entries")
        print("  stats [project_dir]        Show audit statistics")
        print("  cleanup [project_dir]      Cleanup old logs")
        sys.exit(1)

    command = sys.argv[1]
    project_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    logger = AuditLogger(project_dir)

    if command == 'tail':
        limit = 20
        if '-n' in sys.argv:
            idx = sys.argv.index('-n')
            if idx + 1 < len(sys.argv):
                limit = int(sys.argv[idx + 1])

        entries = logger.get_audit_trail(limit=limit)
        for entry in entries:
            status = "OK" if entry.success else "FAIL"
            print(f"[{entry.timestamp}] [{entry.level.upper()}] [{status}] "
                  f"{entry.operation} {entry.file_path}")

    elif command == 'stats':
        stats = logger.get_statistics()
        print("\n=== 审计统计 ===")
        print(f"总操作数: {stats['total_operations']}")
        print(f"成功率: {stats['success_rate']:.1%}")
        print(f"唯一用户: {stats['unique_users']}")
        print(f"唯一文件: {stats['unique_files']}")
        print("\n按操作类型:")
        for op, count in stats['by_operation'].items():
            print(f"  {op}: {count}")
        print("\n按日志级别:")
        for level, count in stats['by_level'].items():
            print(f"  {level}: {count}")

    elif command == 'cleanup':
        removed = logger.cleanup_old_logs()
        print(f"Cleaned up {removed} old log entries")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()