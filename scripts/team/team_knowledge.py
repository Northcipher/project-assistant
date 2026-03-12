#!/usr/bin/env python3
"""
团队知识库
支持团队间问答知识共享

特性:
- 问答分享到团队
- 导入团队问答库
- 合并问答库
- 团队知识统计
"""

import os
import json
import time
import uuid
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class QAPriority(Enum):
    """问答优先级"""
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class QAStatus(Enum):
    """问答状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    OUTDATED = "outdated"


@dataclass
class QAEntry:
    """问答条目"""
    id: str
    question: str
    answer: str
    author: str = ""
    created_at: str = ""
    updated_at: str = ""
    tags: List[str] = field(default_factory=list)
    code_refs: List[str] = field(default_factory=list)
    file_refs: List[str] = field(default_factory=list)
    team: str = ""
    votes: int = 0
    views: int = 0
    priority: QAPriority = QAPriority.NORMAL
    status: QAStatus = QAStatus.ACTIVE
    version: int = 1

    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return f"qa_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'author': self.author,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'tags': self.tags,
            'code_refs': self.code_refs,
            'file_refs': self.file_refs,
            'team': self.team,
            'votes': self.votes,
            'views': self.views,
            'priority': self.priority.value,
            'status': self.status.value,
            'version': self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QAEntry':
        """从字典创建"""
        return cls(
            id=data.get('id', ''),
            question=data.get('question', ''),
            answer=data.get('answer', ''),
            author=data.get('author', ''),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            tags=data.get('tags', []),
            code_refs=data.get('code_refs', []),
            file_refs=data.get('file_refs', []),
            team=data.get('team', ''),
            votes=data.get('votes', 0),
            views=data.get('views', 0),
            priority=QAPriority(data.get('priority', 'normal')),
            status=QAStatus(data.get('status', 'active')),
            version=data.get('version', 1),
        )


@dataclass
class TeamStats:
    """团队统计"""
    team_name: str
    total_qa: int = 0
    total_votes: int = 0
    total_views: int = 0
    active_qa: int = 0
    archived_qa: int = 0
    top_contributors: List[Dict[str, Any]] = field(default_factory=list)
    popular_tags: List[Dict[str, int]] = field(default_factory=list)
    last_sync: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'team_name': self.team_name,
            'total_qa': self.total_qa,
            'total_votes': self.total_votes,
            'total_views': self.total_views,
            'active_qa': self.active_qa,
            'archived_qa': self.archived_qa,
            'top_contributors': self.top_contributors,
            'popular_tags': self.popular_tags,
            'last_sync': self.last_sync,
        }


class TeamKnowledgeBase:
    """团队知识库

    功能:
    - 分享问答到团队
    - 导入团队问答库
    - 合并问答库
    - 统计分析
    """

    def __init__(self, project_dir: str, team_name: str = None):
        """初始化团队知识库

        Args:
            project_dir: 项目目录
            team_name: 团队名称
        """
        self.project_dir = Path(project_dir).resolve()
        self.team_name = team_name
        self._meta_dir = self.project_dir / '.projmeta'
        self._team_dir = self._meta_dir / 'team'
        self._qa_dir = self._team_dir / 'qa'
        self._shared_dir = self._team_dir / 'shared'

        # 确保目录存在
        self._qa_dir.mkdir(parents=True, exist_ok=True)
        self._shared_dir.mkdir(parents=True, exist_ok=True)

        # 本地问答缓存
        self._qa_cache: Dict[str, QAEntry] = {}

    def share_qa(self, qa_id: str, team: str, author: str = "") -> bool:
        """分享问答到团队

        Args:
            qa_id: 问答 ID
            team: 团队名称
            author: 分享者

        Returns:
            是否成功
        """
        # 加载问答
        qa = self._load_qa(qa_id)
        if not qa:
            return False

        # 更新团队信息
        qa.team = team
        qa.updated_at = datetime.now().isoformat()

        # 保存到团队共享目录
        team_dir = self._shared_dir / team
        team_dir.mkdir(parents=True, exist_ok=True)

        qa_file = team_dir / f"{qa_id}.json"
        with open(qa_file, 'w', encoding='utf-8') as f:
            json.dump(qa.to_dict(), f, ensure_ascii=False, indent=2)

        # 记录分享日志
        self._log_share(qa_id, team, author)

        return True

    def import_team_qa(self, team: str) -> List[QAEntry]:
        """导入团队问答库

        Args:
            team: 团队名称

        Returns:
            导入的问答列表
        """
        team_dir = self._shared_dir / team
        if not team_dir.exists():
            return []

        imported = []
        for qa_file in team_dir.glob('*.json'):
            try:
                with open(qa_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                qa = QAEntry.from_dict(data)

                # 保存到本地
                self._save_qa(qa)
                imported.append(qa)

            except Exception:
                continue

        return imported

    def merge_qa(self, source: str, target: str, strategy: str = "keep_newer") -> bool:
        """合并问答库

        Args:
            source: 源团队
            target: 目标团队
            strategy: 合并策略 (keep_newer, keep_source, keep_target)

        Returns:
            是否成功
        """
        source_dir = self._shared_dir / source
        target_dir = self._shared_dir / target

        if not source_dir.exists():
            return False

        target_dir.mkdir(parents=True, exist_ok=True)

        for qa_file in source_dir.glob('*.json'):
            try:
                with open(qa_file, 'r', encoding='utf-8') as f:
                    source_qa = QAEntry.from_dict(json.load(f))

                target_file = target_dir / qa_file.name

                if target_file.exists():
                    with open(target_file, 'r', encoding='utf-8') as f:
                        target_qa = QAEntry.from_dict(json.load(f))

                    # 根据策略合并
                    merged = self._merge_qa_entries(source_qa, target_qa, strategy)
                else:
                    merged = source_qa

                merged.team = target
                with open(target_file, 'w', encoding='utf-8') as f:
                    json.dump(merged.to_dict(), f, ensure_ascii=False, indent=2)

            except Exception:
                continue

        return True

    def _merge_qa_entries(self, source: QAEntry, target: QAEntry, strategy: str) -> QAEntry:
        """合并两个问答条目"""
        if strategy == "keep_newer":
            # 比较更新时间
            source_time = datetime.fromisoformat(source.updated_at)
            target_time = datetime.fromisoformat(target.updated_at)
            return source if source_time > target_time else target

        elif strategy == "keep_source":
            return source

        elif strategy == "keep_target":
            return target

        else:
            # 合并内容
            merged = QAEntry(
                id=target.id,
                question=target.question,
                answer=target.answer if target.answer else source.answer,
                author=target.author,
                created_at=min(target.created_at, source.created_at),
                updated_at=max(target.updated_at, source.updated_at),
                tags=list(set(target.tags + source.tags)),
                code_refs=list(set(target.code_refs + source.code_refs)),
                file_refs=list(set(target.file_refs + source.file_refs)),
                team=target.team,
                votes=max(target.votes, source.votes),
                views=max(target.views, source.views),
            )
            return merged

    def get_team_stats(self, team: str = None) -> TeamStats:
        """获取团队知识统计

        Args:
            team: 团队名称（可选，默认当前团队）

        Returns:
            团队统计
        """
        team = team or self.team_name
        if not team:
            return TeamStats(team_name="unknown")

        team_dir = self._shared_dir / team
        if not team_dir.exists():
            return TeamStats(team_name=team)

        stats = TeamStats(team_name=team)
        contributor_counts: Dict[str, int] = {}
        tag_counts: Dict[str, int] = {}

        for qa_file in team_dir.glob('*.json'):
            try:
                with open(qa_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                stats.total_qa += 1
                stats.total_votes += data.get('votes', 0)
                stats.total_views += data.get('views', 0)

                if data.get('status') == 'active':
                    stats.active_qa += 1
                elif data.get('status') == 'archived':
                    stats.archived_qa += 1

                # 统计贡献者
                author = data.get('author', 'unknown')
                contributor_counts[author] = contributor_counts.get(author, 0) + 1

                # 统计标签
                for tag in data.get('tags', []):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

            except Exception:
                continue

        # 排序贡献者
        stats.top_contributors = [
            {'author': author, 'count': count}
            for author, count in sorted(contributor_counts.items(), key=lambda x: -x[1])[:10]
        ]

        # 排序标签
        stats.popular_tags = [
            {'tag': tag, 'count': count}
            for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:20]
        ]

        stats.last_sync = datetime.now().isoformat()

        return stats

    def search_team_qa(self, query: str, team: str = None, limit: int = 20) -> List[QAEntry]:
        """搜索团队问答

        Args:
            query: 搜索查询
            team: 团队名称
            limit: 最大结果数

        Returns:
            匹配的问答列表
        """
        team = team or self.team_name
        if not team:
            return []

        team_dir = self._shared_dir / team
        if not team_dir.exists():
            return []

        results = []
        query_lower = query.lower()

        for qa_file in team_dir.glob('*.json'):
            try:
                with open(qa_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                qa = QAEntry.from_dict(data)

                # 计算匹配分数
                score = 0
                if query_lower in qa.question.lower():
                    score += 10
                if query_lower in qa.answer.lower():
                    score += 5
                if query_lower in qa.tags:
                    score += 8

                if score > 0:
                    results.append((qa, score))

            except Exception:
                continue

        # 按分数排序
        results.sort(key=lambda x: -x[1])
        return [r[0] for r in results[:limit]]

    def vote_qa(self, qa_id: str, team: str, vote: int) -> bool:
        """为问答投票

        Args:
            qa_id: 问答 ID
            team: 团队名称
            vote: 投票值 (+1 或 -1)

        Returns:
            是否成功
        """
        qa_file = self._shared_dir / team / f"{qa_id}.json"
        if not qa_file.exists():
            return False

        try:
            with open(qa_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data['votes'] = data.get('votes', 0) + vote

            with open(qa_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True

        except Exception:
            return False

    def record_view(self, qa_id: str, team: str) -> bool:
        """记录问答浏览

        Args:
            qa_id: 问答 ID
            team: 团队名称

        Returns:
            是否成功
        """
        qa_file = self._shared_dir / team / f"{qa_id}.json"
        if not qa_file.exists():
            return False

        try:
            with open(qa_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data['views'] = data.get('views', 0) + 1

            with open(qa_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True

        except Exception:
            return False

    def archive_qa(self, qa_id: str, team: str) -> bool:
        """归档问答

        Args:
            qa_id: 问答 ID
            team: 团队名称

        Returns:
            是否成功
        """
        qa_file = self._shared_dir / team / f"{qa_id}.json"
        if not qa_file.exists():
            return False

        try:
            with open(qa_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data['status'] = QAStatus.ARCHIVED.value
            data['updated_at'] = datetime.now().isoformat()

            with open(qa_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True

        except Exception:
            return False

    def _load_qa(self, qa_id: str) -> Optional[QAEntry]:
        """加载问答"""
        if qa_id in self._qa_cache:
            return self._qa_cache[qa_id]

        qa_file = self._qa_dir / f"{qa_id}.json"
        if not qa_file.exists():
            return None

        try:
            with open(qa_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            qa = QAEntry.from_dict(data)
            self._qa_cache[qa_id] = qa
            return qa
        except Exception:
            return None

    def _save_qa(self, qa: QAEntry) -> bool:
        """保存问答"""
        qa_file = self._qa_dir / f"{qa.id}.json"
        try:
            with open(qa_file, 'w', encoding='utf-8') as f:
                json.dump(qa.to_dict(), f, ensure_ascii=False, indent=2)
            self._qa_cache[qa.id] = qa
            return True
        except Exception:
            return False

    def _log_share(self, qa_id: str, team: str, author: str):
        """记录分享日志"""
        log_file = self._team_dir / 'share_log.json'
        logs = []

        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except Exception:
                pass

        logs.append({
            'qa_id': qa_id,
            'team': team,
            'author': author,
            'timestamp': datetime.now().isoformat(),
        })

        # 只保留最近 1000 条
        logs = logs[-1000:]

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: team_knowledge.py <project_dir> [command]")
        print("\nCommands:")
        print("  share <qa_id> <team>     Share QA to team")
        print("  import <team>            Import team QA")
        print("  stats [team]             Show team stats")
        print("  search <query> [team]    Search team QA")
        sys.exit(1)

    project_dir = sys.argv[1]
    kb = TeamKnowledgeBase(project_dir)

    if len(sys.argv) < 3:
        print("Please specify a command")
        sys.exit(1)

    command = sys.argv[2]

    if command == 'share':
        if len(sys.argv) < 5:
            print("Usage: team_knowledge.py <project_dir> share <qa_id> <team>")
            sys.exit(1)
        qa_id = sys.argv[3]
        team = sys.argv[4]
        success = kb.share_qa(qa_id, team)
        print(f"Share {'succeeded' if success else 'failed'}")

    elif command == 'import':
        if len(sys.argv) < 4:
            print("Usage: team_knowledge.py <project_dir> import <team>")
            sys.exit(1)
        team = sys.argv[3]
        imported = kb.import_team_qa(team)
        print(f"Imported {len(imported)} QA entries")

    elif command == 'stats':
        team = sys.argv[3] if len(sys.argv) > 3 else None
        stats = kb.get_team_stats(team)
        print(json.dumps(stats.to_dict(), indent=2, ensure_ascii=False))

    elif command == 'search':
        if len(sys.argv) < 4:
            print("Usage: team_knowledge.py <project_dir> search <query> [team]")
            sys.exit(1)
        query = sys.argv[3]
        team = sys.argv[4] if len(sys.argv) > 4 else None
        results = kb.search_team_qa(query, team)
        for qa in results:
            print(f"- {qa.id}: {qa.question[:50]}...")


if __name__ == '__main__':
    main()