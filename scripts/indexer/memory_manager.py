#!/usr/bin/env python3
"""
内存感知索引器
支持超大项目的内存管理

特性:
- LRU 缓存策略
- 内存占用限制
- 索引压缩
- 内存监控
"""

import os
import sys
import json
import gzip
import time
import threading
import weakref
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from collections import OrderedDict
from enum import Enum


class CachePriority(Enum):
    """缓存优先级"""
    HIGH = 0    # 高优先级，尽量保留
    NORMAL = 1  # 正常优先级
    LOW = 2     # 低优先级，优先清除


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    size: int  # 字节数
    priority: CachePriority = CachePriority.NORMAL
    access_count: int = 0
    last_access: float = 0.0
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()
        if self.last_access == 0:
            self.last_access = time.time()


class LRUCache:
    """LRU 缓存实现"""

    def __init__(self, max_size: int = 100 * 1024 * 1024):
        """初始化 LRU 缓存

        Args:
            max_size: 最大缓存大小（字节）
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._current_size = 0
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                entry.access_count += 1
                entry.last_access = time.time()
                self._cache[key] = entry  # 移到最后
                self._hits += 1
                return entry.value
            self._misses += 1
            return None

    def set(self, key: str, value: Any, size: int = None,
            priority: CachePriority = CachePriority.NORMAL) -> bool:
        """设置缓存值"""
        with self._lock:
            # 计算大小
            if size is None:
                try:
                    size = sys.getsizeof(value)
                except Exception:
                    size = 1024  # 默认 1KB

            # 如果已存在，先删除
            if key in self._cache:
                old_entry = self._cache.pop(key)
                self._current_size -= old_entry.size

            # 检查是否需要清理
            while self._current_size + size > self.max_size and self._cache:
                self._evict_one()

            # 如果还是放不下，放弃
            if size > self.max_size:
                return False

            # 添加新条目
            entry = CacheEntry(
                key=key,
                value=value,
                size=size,
                priority=priority,
            )
            self._cache[key] = entry
            self._current_size += size

            return True

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_size -= entry.size
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._current_size = 0

    def _evict_one(self):
        """驱逐一个缓存条目（LRU 策略）"""
        if not self._cache:
            return

        # 找到最低优先级且最久未访问的条目
        candidates = [(k, e) for k, e in self._cache.items()
                      if e.priority == CachePriority.LOW]
        if not candidates:
            candidates = [(k, e) for k, e in self._cache.items()
                          if e.priority == CachePriority.NORMAL]
        if not candidates:
            candidates = list(self._cache.items())

        # 按 last_access 排序，移除最旧的
        candidates.sort(key=lambda x: x[1].last_access)
        key_to_remove = candidates[0][0]

        entry = self._cache.pop(key_to_remove)
        self._current_size -= entry.size

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            hit_rate = self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0
            return {
                'entries': len(self._cache),
                'current_size': self._current_size,
                'max_size': self.max_size,
                'usage_percent': self._current_size / self.max_size * 100 if self.max_size > 0 else 0,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
            }


class MemoryAwareIndexer:
    """内存感知索引器

    特性:
    - 限制内存占用
    - LRU 驱逐策略
    - 自动压缩
    - 内存监控
    """

    def __init__(self, project_dir: str, max_memory_mb: int = 512):
        """初始化内存感知索引器

        Args:
            project_dir: 项目目录
            max_memory_mb: 最大内存占用（MB）
        """
        self.project_dir = Path(project_dir).resolve()
        self.max_memory = max_memory_mb * 1024 * 1024
        self._cache_dir = self.project_dir / '.projmeta' / 'index'

        # LRU 缓存
        self._cache = LRUCache(max_size=self.max_memory)

        # 索引存储路径
        self._index_paths: Dict[str, Path] = {}

        # 压缩配置
        self._compress_threshold = 10 * 1024  # 10KB 以上压缩
        self._compression_level = 6

        # 内存监控
        self._monitor_interval = 60  # 秒
        self._last_check = 0

    def load_with_lru(self, index_key: str, loader: Callable[[], Any] = None) -> Any:
        """使用 LRU 策略加载索引

        Args:
            index_key: 索引键
            loader: 加载函数（缓存未命中时调用）

        Returns:
            索引数据
        """
        # 尝试从内存缓存获取
        cached = self._cache.get(index_key)
        if cached is not None:
            return cached

        # 尝试从磁盘加载
        disk_data = self._load_from_disk(index_key)
        if disk_data is not None:
            self._cache.set(index_key, disk_data)
            return disk_data

        # 使用加载器
        if loader:
            data = loader()
            if data is not None:
                self._cache.set(index_key, data)
                self._save_to_disk(index_key, data)
            return data

        return None

    def store(self, index_key: str, data: Any, priority: CachePriority = CachePriority.NORMAL):
        """存储索引数据

        Args:
            index_key: 索引键
            data: 索引数据
            priority: 缓存优先级
        """
        self._cache.set(index_key, data, priority=priority)
        self._save_to_disk(index_key, data)

    def invalidate(self, index_key: str):
        """使缓存失效"""
        self._cache.delete(index_key)
        self._delete_from_disk(index_key)

    def current_memory_usage(self) -> int:
        """获取当前内存使用量"""
        return self._cache._current_size

    def memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        return self._cache.get_stats()

    def evict_lru(self, target_size: int = None):
        """执行 LRU 驱逐

        Args:
            target_size: 目标大小（字节）
        """
        if target_size:
            while self._cache._current_size > target_size and self._cache._cache:
                self._cache._evict_one()
        else:
            self._cache._evict_one()

    def compress_index(self, data: Dict) -> bytes:
        """压缩索引数据

        Args:
            data: 索引数据

        Returns:
            压缩后的字节
        """
        json_str = json.dumps(data, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')

        if len(json_bytes) >= self._compress_threshold:
            return gzip.compress(json_bytes, compresslevel=self._compression_level)
        return json_bytes

    def decompress_index(self, data: bytes) -> Dict:
        """解压索引数据

        Args:
            data: 压缩数据

        Returns:
            解压后的字典
        """
        try:
            # 尝试解压
            decompressed = gzip.decompress(data)
            json_str = decompressed.decode('utf-8')
        except Exception:
            # 未压缩的数据
            json_str = data.decode('utf-8')

        return json.loads(json_str)

    def _load_from_disk(self, index_key: str) -> Optional[Any]:
        """从磁盘加载索引"""
        index_path = self._get_index_path(index_key)
        if not index_path.exists():
            return None

        try:
            with open(index_path, 'rb') as f:
                data = f.read()
            return self.decompress_index(data)
        except Exception:
            return None

    def _save_to_disk(self, index_key: str, data: Any):
        """保存索引到磁盘"""
        index_path = self._get_index_path(index_key)
        index_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            compressed = self.compress_index(data) if isinstance(data, dict) else data
            with open(index_path, 'wb') as f:
                f.write(compressed)
        except Exception:
            pass

    def _delete_from_disk(self, index_key: str):
        """从磁盘删除索引"""
        index_path = self._get_index_path(index_key)
        if index_path.exists():
            index_path.unlink()

    def _get_index_path(self, index_key: str) -> Path:
        """获取索引文件路径"""
        # 使用 hash 避免文件名冲突
        key_hash = hash(index_key) % 10000
        safe_key = index_key.replace('/', '_').replace('\\', '_')
        return self._cache_dir / f'{safe_key}_{key_hash}.idx'

    def optimize_memory(self):
        """优化内存使用"""
        stats = self.memory_stats()

        # 如果使用率超过 80%，清理低优先级缓存
        if stats['usage_percent'] > 80:
            target = int(self.max_memory * 0.6)
            self.evict_lru(target)

        return stats


class MemoryMonitor:
    """内存监控器"""

    def __init__(self, indexer: MemoryAwareIndexer, interval: int = 60):
        """初始化内存监控器

        Args:
            indexer: 内存感知索引器
            interval: 检查间隔（秒）
        """
        self.indexer = indexer
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable] = []

    def start(self):
        """启动监控"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def add_callback(self, callback: Callable):
        """添加回调函数"""
        self._callbacks.append(callback)

    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                stats = self.indexer.optimize_memory()

                # 如果内存使用过高，触发回调
                if stats['usage_percent'] > 90:
                    for callback in self._callbacks:
                        try:
                            callback(stats)
                        except Exception:
                            pass

            except Exception:
                pass

            time.sleep(self.interval)


class ParallelCacheManager:
    """并行缓存管理器

    支持多线程并行更新缓存
    """

    def __init__(self, project_dir: str, workers: int = None):
        """初始化并行缓存管理器

        Args:
            project_dir: 项目目录
            workers: 工作线程数
        """
        self.project_dir = Path(project_dir).resolve()
        self.workers = workers or os.cpu_count() or 4
        self._cache_dir = self.project_dir / '.projmeta' / 'cache'
        self._lock = threading.Lock()

    def parallel_update(self, files: List[str], processor: Callable[[str], Any]) -> Dict[str, Any]:
        """并行更新多个文件的缓存

        Args:
            files: 文件列表
            processor: 处理函数

        Returns:
            更新结果
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {}
        errors = []

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self._update_single, f, processor): f for f in files}

            for future in as_completed(futures):
                file_path = futures[future]
                try:
                    result = future.result()
                    if result:
                        results[file_path] = result
                except Exception as e:
                    errors.append({'file': file_path, 'error': str(e)})

        return {
            'updated': len(results),
            'errors': errors,
            'results': results,
        }

    def _update_single(self, file_path: str, processor: Callable) -> Any:
        """更新单个文件缓存"""
        try:
            result = processor(file_path)
            if result:
                self._save_cache(file_path, result)
            return result
        except Exception:
            return None

    def _save_cache(self, file_path: str, data: Any):
        """保存缓存"""
        cache_path = self._cache_dir / f'{hash(file_path) % 10000}.json'
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({'file': file_path, 'data': data}, f, ensure_ascii=False)


def get_system_memory_info() -> Dict[str, int]:
    """获取系统内存信息"""
    info = {
        'total': 0,
        'available': 0,
        'used': 0,
        'percent': 0,
    }

    try:
        import psutil
        mem = psutil.virtual_memory()
        info['total'] = mem.total
        info['available'] = mem.available
        info['used'] = mem.used
        info['percent'] = mem.percent
    except ImportError:
        # 回退方案
        if sys.platform == 'linux':
            try:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'MemTotal' in line:
                            info['total'] = int(line.split()[1]) * 1024
                        elif 'MemAvailable' in line:
                            info['available'] = int(line.split()[1]) * 1024
                info['used'] = info['total'] - info['available']
                info['percent'] = info['used'] / info['total'] * 100 if info['total'] > 0 else 0
            except Exception:
                pass

    return info


def estimate_index_size(file_count: int, avg_lines_per_file: int = 200) -> int:
    """估算索引大小

    Args:
        file_count: 文件数量
        avg_lines_per_file: 平均每文件行数

    Returns:
        估算的字节数
    """
    # 每行约 100 字节
    bytes_per_file = avg_lines_per_file * 100
    # 索引约为原始数据的 30%
    return int(file_count * bytes_per_file * 0.3)


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description='Memory-aware indexer')
    parser.add_argument('project_dir', help='Project directory')
    parser.add_argument('--max-memory', type=int, default=512, help='Max memory in MB')
    parser.add_argument('--stats', action='store_true', help='Show memory stats')
    parser.add_argument('--optimize', action='store_true', help='Optimize memory')

    args = parser.parse_args()

    indexer = MemoryAwareIndexer(args.project_dir, args.max_memory)

    if args.stats:
        stats = indexer.memory_stats()
        print(json.dumps(stats, indent=2))

    elif args.optimize:
        stats = indexer.optimize_memory()
        print(f"Memory optimized: {stats['usage_percent']:.1f}% used")

    else:
        # 显示系统内存信息
        sys_mem = get_system_memory_info()
        print("System Memory:")
        print(f"  Total: {sys_mem['total'] / 1024 / 1024:.0f} MB")
        print(f"  Available: {sys_mem['available'] / 1024 / 1024:.0f} MB")
        print(f"  Used: {sys_mem['percent']:.1f}%")

        print(f"\nIndexer Memory:")
        stats = indexer.memory_stats()
        print(f"  Current: {stats['current_size'] / 1024 / 1024:.1f} MB")
        print(f"  Max: {stats['max_size'] / 1024 / 1024:.1f} MB")
        print(f"  Usage: {stats['usage_percent']:.1f}%")


if __name__ == '__main__':
    main()