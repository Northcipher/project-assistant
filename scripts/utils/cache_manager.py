#!/usr/bin/env python3
"""
缓存管理器
管理项目分析缓存，检测缓存有效性

特性：
- 可配置 TTL
- 缓存清理策略
- 懒加载支持
- 增量更新
"""

import os
import sys
import json
import hashlib
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加日志支持
try:
    from utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """缓存配置"""
    default_ttl: int = 86400  # 默认 TTL: 24小时
    max_cache_size: int = 100 * 1024 * 1024  # 最大缓存大小: 100MB
    max_cache_age_days: int = 7  # 最大缓存天数
    lazy_check: bool = True  # 懒加载检查
    incremental_update: bool = True  # 增量更新


# 默认配置
DEFAULT_CONFIG = CacheConfig()

# 关键配置文件列表
KEY_CONFIG_FILES = [
    # JavaScript/TypeScript
    'package.json',
    'package-lock.json',
    'yarn.lock',
    'pnpm-lock.yaml',

    # Rust
    'Cargo.toml',
    'Cargo.lock',

    # Go
    'go.mod',
    'go.sum',

    # Python
    'requirements.txt',
    'pyproject.toml',
    'poetry.lock',
    'Pipfile.lock',

    # Java/Kotlin
    'pom.xml',
    'build.gradle',
    'build.gradle.kts',
    'settings.gradle',
    'settings.gradle.kts',

    # C/C++
    'CMakeLists.txt',
    'Makefile',

    # Android
    'AndroidManifest.xml',
    'gradle.properties',

    # Flutter/Dart
    'pubspec.yaml',
    'pubspec.lock',

    # iOS
    'Podfile',
    'Podfile.lock',
    'Gemfile',
    'Gemfile.lock',

    # Embedded
    '.ioc',
    'sdkconfig',
    'Kconfig',
    'defconfig',
    'prj.conf',

    # Config
    '.env',
    '.env.local',
    '.env.development',
    '.env.production',
]


@dataclass
class CacheEntry:
    """缓存条目"""
    version: str = "1.0"
    timestamp: str = ""
    project_hash: str = ""
    file_hashes: Dict[str, str] = field(default_factory=dict)
    git_status: Dict[str, Any] = field(default_factory=dict)
    analysis_cache: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 大型项目支持
    scale: str = "small"  # small/medium/large
    subsystems: List[str] = field(default_factory=list)
    modules: List[str] = field(default_factory=list)
    processes: List[str] = field(default_factory=list)
    ipc_protocols: List[str] = field(default_factory=list)


class CacheManager:
    """缓存管理器"""

    def __init__(self, project_dir: str, config: CacheConfig = None):
        self.project_dir = Path(project_dir).resolve()
        self.config = config or DEFAULT_CONFIG
        self._cache_path = self.project_dir / '.projmeta' / 'cache.json'
        self._cache: Optional[CacheEntry] = None
        self._dirty = False
        # 子系统缓存管理
        self._subsystem_caches: Dict[str, 'CacheManager'] = {}

    @property
    def cache_path(self) -> Path:
        """缓存文件路径"""
        return self._cache_path

    def load(self) -> CacheEntry:
        """加载缓存"""
        if self._cache is not None:
            return self._cache

        logger.debug(f"加载缓存: {self._cache_path}")
        if self._cache_path.exists():
            try:
                with open(self._cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._cache = CacheEntry(
                    version=data.get('version', '1.0'),
                    timestamp=data.get('timestamp', ''),
                    project_hash=data.get('project_hash', ''),
                    file_hashes=data.get('file_hashes', {}),
                    git_status=data.get('git_status', {}),
                    analysis_cache=data.get('analysis_cache', {}),
                    metadata=data.get('metadata', {}),
                    scale=data.get('scale', 'small'),
                    subsystems=data.get('subsystems', []),
                    modules=data.get('modules', []),
                    processes=data.get('processes', []),
                    ipc_protocols=data.get('ipc_protocols', []),
                )
                logger.debug(f"缓存加载成功, 版本: {self._cache.version}")
            except Exception as e:
                logger.warning(f"缓存加载失败: {e}")
                self._cache = CacheEntry()
        else:
            logger.debug("缓存文件不存在，创建新缓存")
            self._cache = CacheEntry()

        return self._cache

    def save(self) -> None:
        """保存缓存"""
        if not self._dirty and self._cache is None:
            return

        cache = self._cache or CacheEntry()

        # 确保目录存在
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'version': cache.version,
            'timestamp': cache.timestamp or datetime.now().isoformat(),
            'project_hash': cache.project_hash,
            'file_hashes': cache.file_hashes,
            'git_status': cache.git_status,
            'analysis_cache': cache.analysis_cache,
            'metadata': cache.metadata,
            'scale': cache.scale,
            'subsystems': cache.subsystems,
            'modules': cache.modules,
            'processes': cache.processes,
            'ipc_protocols': cache.ipc_protocols,
        }

        with open(self._cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self._dirty = False

    def get_subsystem_cache(self, subsystem: str) -> 'CacheManager':
        """获取子系统缓存管理器"""
        if subsystem not in self._subsystem_caches:
            subsystem_path = self._cache_path.parent / 'subsystems' / subsystem / 'cache.json'
            manager = CacheManager(str(self.project_dir))
            manager._cache_path = subsystem_path
            self._subsystem_caches[subsystem] = manager
        return self._subsystem_caches[subsystem]

    def get_module_cache(self, module: str) -> 'CacheManager':
        """获取模块缓存管理器"""
        if module not in self._subsystem_caches:
            module_path = self._cache_path.parent / 'modules' / f'{module}.json'
            manager = CacheManager(str(self.project_dir))
            manager._cache_path = module_path
            self._subsystem_caches[module] = manager
        return self._subsystem_caches[module]

    def mark_subsystem_analyzed(self, subsystem: str) -> None:
        """标记子系统已分析"""
        cache = self.load()
        if subsystem not in cache.subsystems:
            cache.subsystems.append(subsystem)
            self._dirty = True

    def is_subsystem_analyzed(self, subsystem: str) -> bool:
        """检查子系统是否已分析"""
        cache = self.load()
        return subsystem in cache.subsystems

    def mark_process_analyzed(self, process: str) -> None:
        """标记进程已分析"""
        cache = self.load()
        if process not in cache.processes:
            cache.processes.append(process)
            self._dirty = True

    def clear(self) -> None:
        """清除缓存"""
        if self._cache_path.exists():
            self._cache_path.unlink()
        self._cache = None
        self._dirty = False

    def compute_file_hash(self, file_path: Path) -> Optional[str]:
        """计算文件哈希"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None

    def compute_project_hashes(self) -> Dict[str, str]:
        """计算关键文件的哈希"""
        hashes = {}
        for config_file in KEY_CONFIG_FILES:
            file_path = self.project_dir / config_file
            if file_path.exists():
                h = self.compute_file_hash(file_path)
                if h:
                    hashes[config_file] = h
        return hashes

    def get_git_status(self) -> Dict[str, Any]:
        """获取 Git 状态（并行执行多个 git 命令）"""
        logger.debug(f"获取 Git 状态: {self.project_dir}")
        result = {
            'is_git_repo': False,
            'branch': '',
            'has_changes': False,
            'has_uncommitted': False,
            'has_untracked': False,
            'last_commit': '',
            'last_commit_time': '',
            'last_commit_message': '',
            'ahead': 0,
            'behind': 0,
        }

        def run_git_command(cmd: List[str], timeout: int = 5) -> tuple:
            """运行单个 git 命令"""
            try:
                r = subprocess.run(
                    cmd,
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                return (cmd[1], r.returncode, r.stdout.strip())
            except Exception as e:
                logger.debug(f"Git 命令失败 {' '.join(cmd)}: {e}")
                return (cmd[1], -1, '')

        try:
            # 首先检查是否是 Git 仓库
            r = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode != 0:
                return result

            result['is_git_repo'] = True

            # 并行执行其他 git 命令
            git_commands = [
                (['git', 'branch', '--show-current'], 5),
                (['git', 'status', '--porcelain'], 10),
                (['git', 'log', '-1', '--format=%H|%ci|%s'], 5),
                (['git', 'rev-list', '--left-right', '--count', '@{upstream}...HEAD'], 5),
            ]

            results = {}
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(run_git_command, cmd, timeout): name
                    for cmd, timeout in git_commands
                    for name in [cmd[1]]
                }
                for future in as_completed(futures):
                    try:
                        cmd_name, returncode, output = future.result()
                        results[cmd_name] = (returncode, output)
                    except Exception as e:
                        logger.debug(f"Git 并行命令异常: {e}")

            # 处理 branch 结果
            if 'branch' in results and results['branch'][0] == 0:
                result['branch'] = results['branch'][1]

            # 处理 status 结果
            if 'status' in results and results['status'][0] == 0:
                output = results['status'][1]
                lines = output.split('\n') if output else []
                result['has_changes'] = len(lines) > 0
                for line in lines:
                    if line:
                        status = line[0]
                        if status in ('M', 'A', 'D', 'R', 'C'):
                            result['has_uncommitted'] = True
                        if status == '?':
                            result['has_untracked'] = True

            # 处理 log 结果
            if 'log' in results and results['log'][0] == 0 and results['log'][1]:
                parts = results['log'][1].split('|', 2)
                if len(parts) >= 1:
                    result['last_commit'] = parts[0][:7]
                if len(parts) >= 2:
                    result['last_commit_time'] = parts[1]
                if len(parts) >= 3:
                    result['last_commit_message'] = parts[2][:50]

            # 处理 rev-list 结果
            if 'rev-list' in results and results['rev-list'][0] == 0 and results['rev-list'][1]:
                parts = results['rev-list'][1].split()
                if len(parts) == 2:
                    result['behind'] = int(parts[0])
                    result['ahead'] = int(parts[1])

        except Exception as e:
            logger.debug(f"获取 Git 状态异常: {e}")

        return result

    def check_validity(self, quick: bool = False) -> Dict[str, Any]:
        """检查缓存有效性

        Args:
            quick: 快速检查模式，只检查时间戳
        """
        result = {
            'cache_exists': False,
            'is_valid': False,
            'reason': '',
            'needs_update': False,
            'changed_files': [],
            'lazy_skip': False,
        }

        cache = self.load()

        if not cache.timestamp:
            result['reason'] = '缓存不存在'
            result['needs_update'] = True
            return result

        result['cache_exists'] = True

        # 检查版本
        if cache.version != "1.0":
            result['reason'] = '缓存版本过期'
            result['needs_update'] = True
            return result

        # 检查 TTL
        try:
            cache_time = datetime.fromisoformat(cache.timestamp)
            elapsed = (datetime.now() - cache_time).total_seconds()
            if elapsed > self.config.default_ttl:
                result['reason'] = f'缓存已过期 ({int(elapsed/60)}分钟前)'
                result['needs_update'] = True
                return result
        except Exception:
            pass

        # 快速模式：只检查时间戳
        if quick:
            result['is_valid'] = True
            result['reason'] = '缓存有效 (快速检查)'
            return result

        # 懒加载检查：根据问题类型决定是否需要深入检查
        if self.config.lazy_check:
            # 检查是否有简单的文件变更
            current_hashes = self.compute_project_hashes()
            cached_hashes = cache.file_hashes

            # 只比较顶层配置文件
            top_level_files = ['package.json', 'Cargo.toml', 'go.mod', 'pom.xml',
                             'CMakeLists.txt', 'requirements.txt', 'AndroidManifest.xml']

            changed_top_level = []
            for fname in top_level_files:
                if fname in current_hashes:
                    if fname not in cached_hashes or cached_hashes.get(fname) != current_hashes[fname]:
                        changed_top_level.append(fname)

            if not changed_top_level:
                result['is_valid'] = True
                result['reason'] = '缓存有效'
                result['lazy_skip'] = True
                return result

        # 完整检查：比较所有文件哈希
        current_hashes = self.compute_project_hashes()
        cached_hashes = cache.file_hashes

        changed_files = []
        for fname, h in current_hashes.items():
            if fname in cached_hashes:
                if cached_hashes[fname] != h:
                    changed_files.append(fname)
            else:
                changed_files.append(fname)

        if changed_files:
            result['reason'] = f'文件变更: {", ".join(changed_files[:5])}'
            result['changed_files'] = changed_files
            result['needs_update'] = True
            return result

        # 检查 Git 状态
        if self.config.incremental_update:
            git_status = self.get_git_status()
            cached_git = cache.git_status

            if git_status.get('has_changes'):
                result['reason'] = '存在未提交的变更'
                result['needs_update'] = True
                return result

            if git_status.get('last_commit') != cached_git.get('last_commit'):
                result['reason'] = '有新的提交'
                result['needs_update'] = True
                return result

        result['is_valid'] = True
        result['reason'] = '缓存有效'
        return result

    def update(self, analysis_data: Dict[str, Any] = None,
               incremental: bool = False) -> CacheEntry:
        """更新缓存

        Args:
            analysis_data: 分析数据
            incremental: 是否增量更新
        """
        cache = self.load()

        # 保留旧的分析数据（增量更新）
        old_analysis = cache.analysis_cache if incremental else {}

        cache.timestamp = datetime.now().isoformat()
        cache.file_hashes = self.compute_project_hashes()
        cache.git_status = self.get_git_status()

        if analysis_data:
            if incremental:
                # 合并分析数据
                cache.analysis_cache = {**old_analysis, **analysis_data}
            else:
                cache.analysis_cache = analysis_data

        self._cache = cache
        self._dirty = True
        self.save()

        return cache

    def get_analysis_cache(self, key: str = None) -> Any:
        """获取分析缓存"""
        cache = self.load()
        if key:
            return cache.analysis_cache.get(key)
        return cache.analysis_cache

    def set_analysis_cache(self, key: str, value: Any) -> None:
        """设置分析缓存"""
        cache = self.load()
        cache.analysis_cache[key] = value
        self._dirty = True

    def get_metadata(self, key: str = None) -> Any:
        """获取元数据"""
        cache = self.load()
        if key:
            return cache.metadata.get(key)
        return cache.metadata

    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据"""
        cache = self.load()
        cache.metadata[key] = value
        self._dirty = True

    def incremental_update(self, changed_files: List[str],
                           analysis_data: Dict[str, Any] = None) -> CacheEntry:
        """增量更新缓存，只处理变更文件

        Args:
            changed_files: 变更文件列表
            analysis_data: 新的分析数据

        Returns:
            更新后的缓存
        """
        cache = self.load()

        # 1. 更新变更文件的哈希
        for file_path in changed_files:
            full_path = self.project_dir / file_path
            if full_path.exists():
                h = self.compute_file_hash(full_path)
                if h:
                    cache.file_hashes[file_path] = h
            elif file_path in cache.file_hashes:
                # 文件已删除，移除哈希
                del cache.file_hashes[file_path]

        # 2. 使相关缓存失效
        self.invalidate_by_files(changed_files)

        # 3. 合并分析数据
        if analysis_data:
            cache.analysis_cache = {**cache.analysis_cache, **analysis_data}

        # 4. 更新时间戳
        cache.timestamp = datetime.now().isoformat()

        self._cache = cache
        self._dirty = True
        self.save()

        return cache

    def invalidate_by_files(self, files: List[str]) -> List[str]:
        """使涉及指定文件的缓存失效

        Args:
            files: 文件列表

        Returns:
            失效的缓存键列表
        """
        cache = self.load()
        invalidated_keys = []

        # 检查分析缓存中的每个条目
        keys_to_remove = []
        for key, value in cache.analysis_cache.items():
            if isinstance(value, dict):
                # 检查是否有文件引用
                file_refs = value.get('file_refs', [])
                if isinstance(file_refs, list):
                    for ref in file_refs:
                        for f in files:
                            if f in ref or ref in f:
                                keys_to_remove.append(key)
                                invalidated_keys.append(key)
                                break

                # 检查 source_file 字段
                source_file = value.get('source_file', '')
                if source_file:
                    for f in files:
                        if f in source_file or source_file in f:
                            keys_to_remove.append(key)
                            invalidated_keys.append(key)
                            break

        # 移除失效的缓存
        for key in set(keys_to_remove):
            del cache.analysis_cache[key]

        if keys_to_remove:
            self._dirty = True

        return invalidated_keys

    def get_file_changes_since_last_cache(self) -> Dict[str, Any]:
        """获取上次缓存以来的文件变更

        Returns:
            变更信息
        """
        cache = self.load()
        current_hashes = self.compute_project_hashes()

        added = []
        modified = []
        deleted = []

        # 检查新增和修改
        for file_path, hash_value in current_hashes.items():
            if file_path not in cache.file_hashes:
                added.append(file_path)
            elif cache.file_hashes[file_path] != hash_value:
                modified.append(file_path)

        # 检查删除
        for file_path in cache.file_hashes:
            if file_path not in current_hashes:
                deleted.append(file_path)

        return {
            'added': added,
            'modified': modified,
            'deleted': deleted,
            'total_changes': len(added) + len(modified) + len(deleted),
            'has_changes': bool(added or modified or deleted),
        }

    def get_incremental_update_info(self) -> Dict[str, Any]:
        """获取增量更新信息摘要

        Returns:
            更新信息
        """
        changes = self.get_file_changes_since_last_cache()
        validity = self.check_validity()

        return {
            'cache_valid': validity.get('is_valid', False),
            'last_update': self._cache.timestamp if self._cache else '',
            'files_tracked': len(self._cache.file_hashes) if self._cache else 0,
            'changes': changes,
            'needs_update': changes['has_changes'] or not validity.get('is_valid', False),
        }


def cleanup_old_caches(base_dir: str, max_age_days: int = 7,
                       max_total_size: int = 100 * 1024 * 1024) -> Dict[str, Any]:
    """清理过期或过大的缓存

    Args:
        base_dir: 基础目录（通常是用户主目录）
        max_age_days: 最大缓存天数
        max_total_size: 最大总缓存大小（字节）
    """
    result = {
        'scanned_dirs': 0,
        'removed_caches': [],
        'freed_size': 0,
        'errors': [],
    }

    base_path = Path(base_dir)
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    caches = []

    # 查找所有缓存文件
    try:
        for cache_file in base_path.rglob('.projmeta/cache.json'):
            try:
                stat = cache_file.stat()
                cache_time = datetime.fromtimestamp(stat.st_mtime)
                caches.append({
                    'path': cache_file,
                    'size': stat.st_size,
                    'mtime': cache_time,
                })
            except Exception as e:
                result['errors'].append(f'{cache_file}: {e}')

        result['scanned_dirs'] = len(caches)

        # 按时间排序
        caches.sort(key=lambda x: x['mtime'])

        total_size = sum(c['size'] for c in caches)

        # 清理过期缓存
        for cache_info in caches:
            if cache_info['mtime'] < cutoff_date:
                try:
                    cache_info['path'].unlink()
                    result['removed_caches'].append(str(cache_info['path'].parent.parent))
                    result['freed_size'] += cache_info['size']
                    total_size -= cache_info['size']
                except Exception as e:
                    result['errors'].append(f'{cache_info["path"]}: {e}')

        # 如果总大小超过限制，清理最旧的
        updated_caches = [c for c in caches if c['path'].exists()]
        updated_caches.sort(key=lambda x: x['mtime'])

        while total_size > max_total_size and updated_caches:
            oldest = updated_caches.pop(0)
            try:
                oldest['path'].unlink()
                result['removed_caches'].append(str(oldest['path'].parent.parent))
                result['freed_size'] += oldest['size']
                total_size -= oldest['size']
            except Exception as e:
                result['errors'].append(f'{oldest["path"]}: {e}')

    except Exception as e:
        result['errors'].append(f'Scan error: {e}')

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: cache_manager.py <command> <project_dir> [args]")
        print("\nCommands:")
        print("  check [project_dir] [--quick]  Check cache validity")
        print("  update [project_dir]           Update cache")
        print("  clear [project_dir]            Clear cache")
        print("  cleanup [base_dir]             Cleanup old caches")
        print("  info [project_dir]             Show cache info")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'check':
        project_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
        quick = '--quick' in sys.argv

        manager = CacheManager(project_dir)
        result = manager.check_validity(quick=quick)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == 'update':
        project_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
        incremental = '--incremental' in sys.argv

        manager = CacheManager(project_dir)
        cache = manager.update(incremental=incremental)
        print(json.dumps({
            'success': True,
            'timestamp': cache.timestamp,
            'files_tracked': len(cache.file_hashes),
        }, indent=2, ensure_ascii=False))

    elif command == 'clear':
        project_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

        manager = CacheManager(project_dir)
        manager.clear()
        print(json.dumps({'success': True, 'message': 'Cache cleared'}))

    elif command == 'cleanup':
        base_dir = sys.argv[2] if len(sys.argv) > 2 else str(Path.home())
        max_age = 7
        max_size = 100 * 1024 * 1024

        for arg in sys.argv:
            if arg.startswith('--max-age='):
                max_age = int(arg.split('=')[1])
            elif arg.startswith('--max-size='):
                max_size = int(arg.split('=')[1])

        result = cleanup_old_caches(base_dir, max_age, max_size)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == 'info':
        project_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

        manager = CacheManager(project_dir)
        cache = manager.load()

        info = {
            'cache_exists': bool(cache.timestamp),
            'version': cache.version,
            'timestamp': cache.timestamp,
            'files_tracked': len(cache.file_hashes),
            'has_analysis_cache': bool(cache.analysis_cache),
            'git_branch': cache.git_status.get('branch', ''),
            'last_commit': cache.git_status.get('last_commit', ''),
        }
        print(json.dumps(info, indent=2, ensure_ascii=False))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()