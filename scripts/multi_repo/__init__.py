#!/usr/bin/env python3
"""
多仓库管理模块
支持 monorepo 和多仓库项目的分析
"""

from .mono_manager import MonoRepoManager, RepoInfo, CrossRepoResult
from .repo_linker import RepoLinker, RepoDepGraph

__all__ = [
    'MonoRepoManager',
    'RepoInfo',
    'CrossRepoResult',
    'RepoLinker',
    'RepoDepGraph',
]