#!/usr/bin/env python3
"""
问答协作模块
支持多人协作编辑问答

特性:
- 编辑提议
- 审核流程
- 评论功能
- 变更历史
"""

import os
import json
import uuid
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EditStatus(Enum):
    """编辑状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"


@dataclass
class QAEdit:
    """问答编辑提议"""
    id: str
    qa_id: str
    author: str
    field: str  # question, answer, tags, etc.
    old_value: str
    new_value: str
    reason: str = ""
    status: EditStatus = EditStatus.PENDING
    created_at: str = ""
    reviewed_at: str = ""
    reviewed_by: str = ""
    comments: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"edit_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'qa_id': self.qa_id,
            'author': self.author,
            'field': self.field,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'reason': self.reason,
            'status': self.status.value,
            'created_at': self.created_at,
            'reviewed_at': self.reviewed_at,
            'reviewed_by': self.reviewed_by,
            'comments': self.comments,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QAEdit':
        return cls(
            id=data.get('id', ''),
            qa_id=data.get('qa_id', ''),
            author=data.get('author', ''),
            field=data.get('field', ''),
            old_value=data.get('old_value', ''),
            new_value=data.get('new_value', ''),
            reason=data.get('reason', ''),
            status=EditStatus(data.get('status', 'pending')),
            created_at=data.get('created_at', ''),
            reviewed_at=data.get('reviewed_at', ''),
            reviewed_by=data.get('reviewed_by', ''),
            comments=data.get('comments', []),
        )


@dataclass
class Comment:
    """评论"""
    id: str
    qa_id: str
    author: str
    content: str
    parent_id: str = ""  # 回复的评论 ID
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"comment_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'qa_id': self.qa_id,
            'author': self.author,
            'content': self.content,
            'parent_id': self.parent_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


@dataclass
class ChangeHistory:
    """变更历史"""
    qa_id: str
    version: int
    field: str
    old_value: str
    new_value: str
    changed_by: str
    changed_at: str
    edit_id: str = ""  # 关联的编辑 ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            'qa_id': self.qa_id,
            'version': self.version,
            'field': self.field,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'changed_by': self.changed_by,
            'changed_at': self.changed_at,
            'edit_id': self.edit_id,
        }


class QACollaboration:
    """问答协作

    工作流程:
    1. 用户提出编辑建议
    2. 审核者审核（批准/拒绝）
    3. 批准后自动合并
    4. 记录变更历史
    """

    def __init__(self, project_dir: str):
        """初始化

        Args:
            project_dir: 项目目录
        """
        self.project_dir = Path(project_dir).resolve()
        self._meta_dir = self.project_dir / '.projmeta'
        self._collab_dir = self._meta_dir / 'collaboration'
        self._edits_dir = self._collab_dir / 'edits'
        self._comments_dir = self._collab_dir / 'comments'
        self._history_dir = self._collab_dir / 'history'

        # 确保目录存在
        self._edits_dir.mkdir(parents=True, exist_ok=True)
        self._comments_dir.mkdir(parents=True, exist_ok=True)
        self._history_dir.mkdir(parents=True, exist_ok=True)

        # 缓存
        self._edits: Dict[str, QAEdit] = {}
        self._comments: Dict[str, Comment] = {}

    def propose_edit(self, qa_id: str, field: str, old_value: str,
                     new_value: str, author: str, reason: str = "") -> QAEdit:
        """提议编辑

        Args:
            qa_id: 问答 ID
            field: 字段名
            old_value: 旧值
            new_value: 新值
            author: 提议者
            reason: 原因

        Returns:
            创建的编辑提议
        """
        edit = QAEdit(
            id=f"edit_{uuid.uuid4().hex[:8]}",
            qa_id=qa_id,
            author=author,
            field=field,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        )

        self._save_edit(edit)
        self._edits[edit.id] = edit

        return edit

    def review_edit(self, edit_id: str, reviewer: str, approve: bool,
                    comment: str = "") -> bool:
        """审核编辑

        Args:
            edit_id: 编辑 ID
            reviewer: 审核者
            approve: 是否批准
            comment: 审核意见

        Returns:
            是否成功
        """
        edit = self._load_edit(edit_id)
        if not edit or edit.status != EditStatus.PENDING:
            return False

        edit.reviewed_by = reviewer
        edit.reviewed_at = datetime.now().isoformat()

        if approve:
            edit.status = EditStatus.APPROVED
            # 应用编辑
            self._apply_edit(edit)
            edit.status = EditStatus.MERGED
        else:
            edit.status = EditStatus.REJECTED

        if comment:
            edit.comments.append({
                'author': reviewer,
                'content': comment,
                'type': 'review',
                'created_at': datetime.now().isoformat(),
            })

        self._save_edit(edit)
        return True

    def get_pending_reviews(self, reviewer: str = None) -> List[QAEdit]:
        """获取待审核编辑

        Args:
            reviewer: 审核者（可选，用于过滤）

        Returns:
            待审核编辑列表
        """
        pending = []

        for edit_file in self._edits_dir.glob('*.json'):
            try:
                with open(edit_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                edit = QAEdit.from_dict(data)

                if edit.status == EditStatus.PENDING:
                    pending.append(edit)

            except Exception:
                continue

        return pending

    def get_edit(self, edit_id: str) -> Optional[QAEdit]:
        """获取编辑提议"""
        return self._load_edit(edit_id)

    def get_qa_edits(self, qa_id: str) -> List[QAEdit]:
        """获取问答的所有编辑"""
        edits = []

        for edit_file in self._edits_dir.glob('*.json'):
            try:
                with open(edit_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                edit = QAEdit.from_dict(data)

                if edit.qa_id == qa_id:
                    edits.append(edit)

            except Exception:
                continue

        return edits

    def comment(self, qa_id: str, content: str, author: str,
                parent_id: str = "") -> Comment:
        """添加评论

        Args:
            qa_id: 问答 ID
            content: 评论内容
            author: 评论者
            parent_id: 父评论 ID（回复）

        Returns:
            创建的评论
        """
        comment = Comment(
            qa_id=qa_id,
            author=author,
            content=content,
            parent_id=parent_id,
        )

        self._save_comment(comment)
        self._comments[comment.id] = comment

        return comment

    def get_comments(self, qa_id: str) -> List[Comment]:
        """获取问答评论"""
        comments = []

        comments_file = self._comments_dir / f"{qa_id}.json"
        if comments_file.exists():
            try:
                with open(comments_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                comments = [Comment(**c) for c in data]
            except Exception:
                pass

        return comments

    def get_comment_replies(self, comment_id: str) -> List[Comment]:
        """获取评论回复"""
        replies = []

        for comments_file in self._comments_dir.glob('*.json'):
            try:
                with open(comments_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for c in data:
                    if c.get('parent_id') == comment_id:
                        replies.append(Comment(**c))
            except Exception:
                continue

        return replies

    def delete_comment(self, comment_id: str, author: str) -> bool:
        """删除评论"""
        comment = self._comments.get(comment_id)
        if not comment:
            return False

        if comment.author != author:
            return False

        # 从存储中删除
        comments_file = self._comments_dir / f"{comment.qa_id}.json"
        if comments_file.exists():
            try:
                with open(comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                comments = [c for c in comments if c.get('id') != comment_id]
                with open(comments_file, 'w', encoding='utf-8') as f:
                    json.dump(comments, f, ensure_ascii=False, indent=2)
                return True
            except Exception:
                pass

        return False

    def get_history(self, qa_id: str) -> List[ChangeHistory]:
        """获取变更历史"""
        history = []

        history_file = self._history_dir / f"{qa_id}.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                history = [ChangeHistory(**h) for h in data]
            except Exception:
                pass

        return history

    def _apply_edit(self, edit: QAEdit) -> bool:
        """应用编辑到问答"""
        # 这里需要与 QA 文档管理器集成
        # 简化实现：只记录历史

        history = ChangeHistory(
            qa_id=edit.qa_id,
            version=self._get_next_version(edit.qa_id),
            field=edit.field,
            old_value=edit.old_value,
            new_value=edit.new_value,
            changed_by=edit.reviewed_by,
            changed_at=datetime.now().isoformat(),
            edit_id=edit.id,
        )

        self._save_history(history)
        return True

    def _get_next_version(self, qa_id: str) -> int:
        """获取下一个版本号"""
        history = self.get_history(qa_id)
        return max(h.version for h in history) + 1 if history else 1

    def _load_edit(self, edit_id: str) -> Optional[QAEdit]:
        """加载编辑"""
        edit_file = self._edits_dir / f"{edit_id}.json"
        if not edit_file.exists():
            return None

        try:
            with open(edit_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return QAEdit.from_dict(data)
        except Exception:
            return None

    def _save_edit(self, edit: QAEdit):
        """保存编辑"""
        edit_file = self._edits_dir / f"{edit.id}.json"
        with open(edit_file, 'w', encoding='utf-8') as f:
            json.dump(edit.to_dict(), f, ensure_ascii=False, indent=2)

    def _save_comment(self, comment: Comment):
        """保存评论"""
        comments_file = self._comments_dir / f"{comment.qa_id}.json"

        comments = []
        if comments_file.exists():
            try:
                with open(comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
            except Exception:
                pass

        comments.append(comment.to_dict())

        with open(comments_file, 'w', encoding='utf-8') as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)

    def _save_history(self, history: ChangeHistory):
        """保存历史"""
        history_file = self._history_dir / f"{history.qa_id}.json"

        histories = []
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    histories = json.load(f)
            except Exception:
                pass

        histories.append(history.to_dict())

        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(histories, f, ensure_ascii=False, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        """获取协作统计"""
        stats = {
            'total_edits': 0,
            'pending_edits': 0,
            'approved_edits': 0,
            'rejected_edits': 0,
            'total_comments': 0,
            'top_contributors': [],
        }

        contributor_counts: Dict[str, int] = {}

        # 统计编辑
        for edit_file in self._edits_dir.glob('*.json'):
            try:
                with open(edit_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                stats['total_edits'] += 1

                status = data.get('status', 'pending')
                if status == 'pending':
                    stats['pending_edits'] += 1
                elif status in ('approved', 'merged'):
                    stats['approved_edits'] += 1
                elif status == 'rejected':
                    stats['rejected_edits'] += 1

                # 统计贡献者
                author = data.get('author', 'unknown')
                contributor_counts[author] = contributor_counts.get(author, 0) + 1

            except Exception:
                continue

        # 统计评论
        for comments_file in self._comments_dir.glob('*.json'):
            try:
                with open(comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                stats['total_comments'] += len(comments)

                for c in comments:
                    author = c.get('author', 'unknown')
                    contributor_counts[author] = contributor_counts.get(author, 0) + 1

            except Exception:
                continue

        # 排序贡献者
        stats['top_contributors'] = sorted(
            [{'author': k, 'count': v} for k, v in contributor_counts.items()],
            key=lambda x: -x['count']
        )[:10]

        return stats


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: collaboration.py <project_dir> [command]")
        print("\nCommands:")
        print("  propose <qa_id> <field> <new_value> <author>  Propose edit")
        print("  review <edit_id> <reviewer> <approve>          Review edit")
        print("  pending                                         List pending edits")
        print("  comment <qa_id> <content> <author>             Add comment")
        print("  history <qa_id>                                Show change history")
        print("  stats                                          Show collaboration stats")
        sys.exit(1)

    project_dir = sys.argv[1]
    collab = QACollaboration(project_dir)

    if len(sys.argv) < 3:
        print("Please specify a command")
        sys.exit(1)

    command = sys.argv[2]

    if command == 'propose':
        if len(sys.argv) < 7:
            print("Usage: collaboration.py <project_dir> propose <qa_id> <field> <new_value> <author>")
            sys.exit(1)
        qa_id = sys.argv[3]
        field = sys.argv[4]
        new_value = sys.argv[5]
        author = sys.argv[6]
        edit = collab.propose_edit(qa_id, field, "", new_value, author)
        print(f"Created edit: {edit.id}")

    elif command == 'review':
        if len(sys.argv) < 6:
            print("Usage: collaboration.py <project_dir> review <edit_id> <reviewer> <approve>")
            sys.exit(1)
        edit_id = sys.argv[3]
        reviewer = sys.argv[4]
        approve = sys.argv[5].lower() in ('yes', 'true', '1', 'approve')
        success = collab.review_edit(edit_id, reviewer, approve)
        print(f"Review {'succeeded' if success else 'failed'}")

    elif command == 'pending':
        pending = collab.get_pending_reviews()
        for edit in pending:
            print(f"- {edit.id}: {edit.qa_id}.{edit.field} by {edit.author}")

    elif command == 'comment':
        if len(sys.argv) < 6:
            print("Usage: collaboration.py <project_dir> comment <qa_id> <content> <author>")
            sys.exit(1)
        qa_id = sys.argv[3]
        content = sys.argv[4]
        author = sys.argv[5]
        comment = collab.comment(qa_id, content, author)
        print(f"Created comment: {comment.id}")

    elif command == 'history':
        if len(sys.argv) < 4:
            print("Usage: collaboration.py <project_dir> history <qa_id>")
            sys.exit(1)
        qa_id = sys.argv[3]
        history = collab.get_history(qa_id)
        for h in history:
            print(f"- v{h.version}: {h.field} changed by {h.changed_by}")

    elif command == 'stats':
        stats = collab.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()