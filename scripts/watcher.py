#!/usr/bin/env python3
"""
项目文件监控器
实时监控项目文件变更，触发增量分析

特性：
- 基于 watchdog 的实时监控
- 智能过滤（排除构建目录、依赖等）
- 变更类型识别（创建/修改/删除）
- 防抖处理
- 回调机制
"""

import os
import sys
import time
import threading
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from enum import Enum
from collections import defaultdict


class ChangeType(Enum):
    """变更类型"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileChange:
    """文件变更事件"""
    file_path: str
    change_type: ChangeType
    timestamp: str
    old_path: str = ""  # 用于 MOVED 类型

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_path': self.file_path,
            'change_type': self.change_type.value,
            'timestamp': self.timestamp,
            'old_path': self.old_path,
        }


@dataclass
class ChangeBatch:
    """变更批次"""
    changes: List[FileChange] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""

    def add(self, change: FileChange) -> None:
        if not self.start_time:
            self.start_time = change.timestamp
        self.end_time = change.timestamp
        self.changes.append(change)

    @property
    def file_count(self) -> int:
        return len(self.changes)

    def get_files_by_type(self, change_type: ChangeType) -> List[str]:
        return [c.file_path for c in self.changes if c.change_type == change_type]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'changes': [c.to_dict() for c in self.changes],
            'start_time': self.start_time,
            'end_time': self.end_time,
            'file_count': self.file_count,
        }


# 默认排除目录
DEFAULT_EXCLUDE_DIRS = {
    '.git', '.svn', '.hg',
    'node_modules', 'venv', '.venv', 'env',
    '__pycache__', '.pytest_cache', '.mypy_cache',
    'dist', 'build', 'out', 'bin', 'obj', 'target',
    '.gradle', '.idea', '.vscode',
    'CMakeFiles', '_deps',
    'Pods', 'DerivedData',
    '.projmeta',  # 项目元数据目录
}

# 默认排除文件
DEFAULT_EXCLUDE_FILES = {
    '*.pyc', '*.pyo', '*.pyd',
    '*.so', '*.dll', '*.dylib',
    '*.min.js', '*.min.css',
    '*.map',
    '*.log', '*.tmp',
    '.DS_Store', 'Thumbs.db',
}


class ProjectWatcher:
    """项目文件监控器"""

    def __init__(self, project_dir: str,
                 callback: Callable[[ChangeBatch], None] = None,
                 config: Dict[str, Any] = None):
        """初始化监控器

        Args:
            project_dir: 项目目录
            callback: 变更回调函数
            config: 配置选项
        """
        self.project_dir = Path(project_dir).resolve()
        self.callback = callback
        self.config = config or {}

        # 排除规则
        self.exclude_dirs = DEFAULT_EXCLUDE_DIRS | set(
            self.config.get('exclude_dirs', [])
        )
        self.exclude_files = DEFAULT_EXCLUDE_FILES | set(
            self.config.get('exclude_files', [])
        )

        # 防抖配置
        self.debounce_ms = self.config.get('debounce_ms', 500)

        # 状态
        self._running = False
        self._observer = None
        self._change_buffer: List[FileChange] = []
        self._buffer_lock = threading.Lock()
        self._debounce_timer: Optional[threading.Timer] = None

        # 文件扩展名过滤
        self.watch_extensions = self.config.get('watch_extensions', None)  # None = 全部监控

    def start(self) -> None:
        """启动监控"""
        if self._running:
            return

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileSystemEvent
        except ImportError:
            print("Warning: watchdog not installed. File monitoring disabled.")
            print("Install with: pip install watchdog")
            return

        self._running = True

        class Handler(FileSystemEventHandler):
            def __init__(handler, watcher: 'ProjectWatcher'):
                handler.watcher = watcher

            def on_created(handler, event: FileSystemEvent):
                if not event.is_directory:
                    handler.watcher._on_file_change(
                        event.src_path, ChangeType.CREATED
                    )

            def on_modified(handler, event: FileSystemEvent):
                if not event.is_directory:
                    handler.watcher._on_file_change(
                        event.src_path, ChangeType.MODIFIED
                    )

            def on_deleted(handler, event: FileSystemEvent):
                if not event.is_directory:
                    handler.watcher._on_file_change(
                        event.src_path, ChangeType.DELETED
                    )

            def on_moved(handler, event: FileSystemEvent):
                if not event.is_directory:
                    handler.watcher._on_file_change(
                        event.dest_path, ChangeType.MOVED, event.src_path
                    )

        self._observer = Observer()
        self._observer.schedule(
            Handler(self),
            str(self.project_dir),
            recursive=True
        )
        self._observer.start()

    def stop(self) -> None:
        """停止监控"""
        if not self._running:
            return

        self._running = False

        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None

    def _on_file_change(self, file_path: str, change_type: ChangeType,
                        old_path: str = "") -> None:
        """文件变更处理"""
        rel_path = self._get_relative_path(file_path)

        # 检查是否应排除
        if self._should_exclude(rel_path):
            return

        # 检查扩展名过滤
        if self.watch_extensions:
            ext = Path(file_path).suffix.lower()
            if ext not in self.watch_extensions:
                return

        # 创建变更事件
        change = FileChange(
            file_path=rel_path,
            change_type=change_type,
            timestamp=datetime.now().isoformat(),
            old_path=old_path,
        )

        # 添加到缓冲区
        with self._buffer_lock:
            self._change_buffer.append(change)

        # 防抖处理
        self._schedule_callback()

    def _should_exclude(self, rel_path: str) -> bool:
        """判断是否应排除"""
        import fnmatch

        # 检查目录
        parts = Path(rel_path).parts
        for part in parts[:-1]:  # 排除最后一级（文件名）
            if part in self.exclude_dirs:
                return True

        # 检查文件名
        filename = parts[-1] if parts else ""
        for pattern in self.exclude_files:
            if fnmatch.fnmatch(filename, pattern):
                return True

        return False

    def _get_relative_path(self, file_path: str) -> str:
        """获取相对路径"""
        try:
            return str(Path(file_path).relative_to(self.project_dir)).replace('\\', '/')
        except ValueError:
            return file_path

    def _schedule_callback(self) -> None:
        """调度回调"""
        if self._debounce_timer:
            self._debounce_timer.cancel()

        self._debounce_timer = threading.Timer(
            self.debounce_ms / 1000,
            self._invoke_callback
        )
        self._debounce_timer.start()

    def _invoke_callback(self) -> None:
        """调用回调"""
        with self._buffer_lock:
            if not self._change_buffer:
                return

            batch = ChangeBatch()
            for change in self._change_buffer:
                batch.add(change)
            self._change_buffer.clear()

        if self.callback:
            try:
                self.callback(batch)
            except Exception as e:
                print(f"Warning: Callback error: {e}")

    def get_changed_files(self) -> List[str]:
        """获取变更文件列表（同步方式，用于轮询）"""
        # 尝试使用 Git 获取变更
        git_changes = self._get_git_changes()
        if git_changes is not None:
            return git_changes

        # 回退到文件时间戳比较
        return self._get_timestamp_changes()

    def _get_git_changes(self) -> Optional[List[str]]:
        """通过 Git 获取变更文件"""
        import subprocess

        try:
            # 检查是否是 Git 仓库
            r = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.project_dir,
                capture_output=True,
                timeout=5,
            )
            if r.returncode != 0:
                return None

            # 获取变更文件
            r = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if r.returncode == 0:
                files = []
                for line in r.stdout.strip().split('\n'):
                    if line and not self._should_exclude(line):
                        files.append(line)
                return files

        except Exception:
            pass

        return None

    def _get_timestamp_changes(self, cache_file: str = ".projmeta/file_timestamps.json") -> List[str]:
        """通过时间戳比较获取变更文件"""
        cache_path = self.project_dir / cache_file
        old_timestamps = {}

        # 加载旧时间戳
        if cache_path.exists():
            try:
                import json
                with open(cache_path, 'r', encoding='utf-8') as f:
                    old_timestamps = json.load(f)
            except Exception:
                pass

        # 获取当前时间戳
        new_timestamps = {}
        changed_files = []

        for root, dirs, files in os.walk(self.project_dir):
            # 排除目录
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for f in files:
                file_path = Path(root) / f
                rel_path = str(file_path.relative_to(self.project_dir)).replace('\\', '/')

                if self._should_exclude(rel_path):
                    continue

                try:
                    mtime = file_path.stat().st_mtime
                    new_timestamps[rel_path] = mtime

                    # 检查是否变更
                    if rel_path in old_timestamps:
                        if abs(mtime - old_timestamps[rel_path]) > 1:  # 1秒误差
                            changed_files.append(rel_path)
                    else:
                        changed_files.append(rel_path)  # 新文件

                except Exception:
                    continue

        # 保存新时间戳
        try:
            import json
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(new_timestamps, f)
        except Exception:
            pass

        return changed_files

    def get_change_type(self, file: str) -> ChangeType:
        """获取文件变更类型"""
        full_path = self.project_dir / file

        if full_path.exists():
            return ChangeType.MODIFIED
        else:
            return ChangeType.DELETED

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def watch_project(project_dir: str,
                  callback: Callable[[ChangeBatch], None] = None,
                  **config) -> ProjectWatcher:
    """创建并启动项目监控器的便捷函数"""
    watcher = ProjectWatcher(project_dir, callback, config)
    watcher.start()
    return watcher


def main():
    """命令行接口"""
    import json

    if len(sys.argv) < 2:
        print("Usage: watcher.py <project_dir> [--daemon] [--interval=N]")
        print("\nOptions:")
        print("  --daemon      Run as daemon (continuous monitoring)")
        print("  --interval=N  Check interval in seconds (default: 5)")
        print("  --json        Output as JSON")
        sys.exit(1)

    project_dir = sys.argv[1]
    daemon_mode = '--daemon' in sys.argv
    output_json = '--json' in sys.argv

    interval = 5
    for arg in sys.argv:
        if arg.startswith('--interval='):
            interval = int(arg.split('=')[1])

    def on_change(batch: ChangeBatch):
        if output_json:
            print(json.dumps(batch.to_dict(), ensure_ascii=False))
        else:
            print(f"\n[{datetime.now().isoformat()}] 检测到 {batch.file_count} 个文件变更:")
            for change in batch.changes[:10]:
                print(f"  - {change.change_type.value}: {change.file_path}")
            if len(batch.changes) > 10:
                print(f"  ... 还有 {len(batch.changes) - 10} 个")

    watcher = ProjectWatcher(project_dir, callback=on_change)

    if daemon_mode:
        print(f"开始监控项目: {project_dir}")
        print("按 Ctrl+C 停止...")

        watcher.start()
        try:
            while True:
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n停止监控...")
        finally:
            watcher.stop()
    else:
        # 单次检查
        changes = watcher.get_changed_files()
        if output_json:
            print(json.dumps({'changed_files': changes}, ensure_ascii=False))
        else:
            print(f"变更文件 ({len(changes)}):")
            for f in changes:
                print(f"  - {f}")


if __name__ == '__main__':
    main()