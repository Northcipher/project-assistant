#!/usr/bin/env python3
"""
团队协作模块
团队知识库、权限管理、问答协作
"""

from .team_knowledge import TeamKnowledgeBase, QAEntry
from .team_db import TeamDatabase
from .permission_manager import PermissionManager
from .collaboration import QACollaboration, QAEdit

__all__ = [
    'TeamKnowledgeBase',
    'QAEntry',
    'TeamDatabase',
    'PermissionManager',
    'QACollaboration',
    'QAEdit',
]