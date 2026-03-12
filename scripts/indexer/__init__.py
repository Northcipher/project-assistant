#!/usr/bin/env python3
"""
索引器模块
分层延迟索引，支持百万行代码项目
"""

from .lazy_indexer import LazyIndexer, L0Index, L1Index, L2Index, L3Index
from .memory_manager import MemoryAwareIndexer, LRUCache

__all__ = [
    'LazyIndexer',
    'L0Index',
    'L1Index',
    'L2Index',
    'L3Index',
    'MemoryAwareIndexer',
    'LRUCache',
]