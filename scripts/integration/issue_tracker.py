#!/usr/bin/env python3
"""
Issue 系统集成
问答与 Issue 双向关联

特性:
- 关联问答与 Issue
- 从问答创建 Issue
- 同步 Issue 状态
- 获取文件相关 Issue
"""

import os
import json
import re
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class IssueStatus(Enum):
    """Issue 状态"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"
    RESOLVED = "resolved"


class IssuePriority(Enum):
    """Issue 优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Issue:
    """Issue 定义"""
    id: str
    title: str
    description: str = ""
    status: IssueStatus = IssueStatus.OPEN
    priority: IssuePriority = IssuePriority.MEDIUM
    labels: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)
    reporter: str = ""
    created_at: str = ""
    updated_at: str = ""
    url: str = ""
    related_files: List[str] = field(default_factory=list)
    related_qa: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'labels': self.labels,
            'assignees': self.assignees,
            'reporter': self.reporter,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'url': self.url,
            'related_files': self.related_files,
            'related_qa': self.related_qa,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Issue':
        return cls(
            id=data.get('id', ''),
            title=data.get('title', ''),
            description=data.get('description', ''),
            status=IssueStatus(data.get('status', 'open')),
            priority=IssuePriority(data.get('priority', 'medium')),
            labels=data.get('labels', []),
            assignees=data.get('assignees', []),
            reporter=data.get('reporter', ''),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            url=data.get('url', ''),
            related_files=data.get('related_files', []),
            related_qa=data.get('related_qa', []),
        )


class IssueTrackerIntegration:
    """Issue 追踪集成

    支持平台:
    - GitHub Issues
    - GitLab Issues
    - Jira
    - Azure DevOps
    """

    def __init__(self, project_dir: str, platform: str = "github",
                 config: Dict[str, Any] = None):
        """初始化

        Args:
            project_dir: 项目目录
            platform: 平台类型
            config: 平台配置
        """
        self.project_dir = Path(project_dir).resolve()
        self.platform = platform
        self.config = config or {}

        self._meta_dir = self.project_dir / '.projmeta'
        self._links_file = self._meta_dir / 'issue_links.json'
        self._links: Dict[str, List[str]] = {}  # qa_id -> [issue_urls]

        self._load_links()

    def link_qa_to_issue(self, qa_id: str, issue_url: str) -> bool:
        """关联问答与 Issue

        Args:
            qa_id: 问答 ID
            issue_url: Issue URL

        Returns:
            是否成功
        """
        if qa_id not in self._links:
            self._links[qa_id] = []

        if issue_url not in self._links[qa_id]:
            self._links[qa_id].append(issue_url)
            self._save_links()

        return True

    def unlink_qa_from_issue(self, qa_id: str, issue_url: str) -> bool:
        """取消关联"""
        if qa_id in self._links and issue_url in self._links[qa_id]:
            self._links[qa_id].remove(issue_url)
            self._save_links()
            return True
        return False

    def get_qa_issues(self, qa_id: str) -> List[str]:
        """获取问答关联的 Issue"""
        return self._links.get(qa_id, [])

    def get_issue_qa(self, issue_url: str) -> List[str]:
        """获取 Issue 关联的问答"""
        qa_ids = []
        for qa_id, issues in self._links.items():
            if issue_url in issues:
                qa_ids.append(qa_id)
        return qa_ids

    def create_issue_from_qa(self, qa_id: str, title: str = None,
                             labels: List[str] = None) -> Optional[str]:
        """从问答创建 Issue

        Args:
            qa_id: 问答 ID
            title: Issue 标题（可选）
            labels: 标签列表

        Returns:
            创建的 Issue URL
        """
        # 获取问答内容
        qa_content = self._get_qa_content(qa_id)
        if not qa_content:
            return None

        issue_title = title or f"Follow-up: {qa_content.get('question', '')[:50]}"
        issue_body = self._format_issue_body(qa_id, qa_content)

        # 根据平台创建 Issue
        if self.platform == "github":
            issue_url = self._create_github_issue(issue_title, issue_body, labels)
        elif self.platform == "gitlab":
            issue_url = self._create_gitlab_issue(issue_title, issue_body, labels)
        elif self.platform == "jira":
            issue_url = self._create_jira_issue(issue_title, issue_body, labels)
        else:
            issue_url = None

        if issue_url:
            self.link_qa_to_issue(qa_id, issue_url)

        return issue_url

    def sync_issue_status(self) -> Dict[str, Any]:
        """同步 Issue 状态

        Returns:
            同步结果
        """
        result = {
            'synced': 0,
            'updated': 0,
            'errors': [],
        }

        for qa_id, issue_urls in self._links.items():
            for issue_url in issue_urls:
                try:
                    status = self._fetch_issue_status(issue_url)

                    if status:
                        result['synced'] += 1

                        # 如果 Issue 已关闭，标记问答可能需要更新
                        if status == 'closed':
                            self._mark_qa_for_review(qa_id)
                            result['updated'] += 1

                except Exception as e:
                    result['errors'].append(f"{issue_url}: {str(e)}")

        return result

    def get_related_issues(self, file: str) -> List[Issue]:
        """获取文件相关 Issue

        Args:
            file: 文件路径

        Returns:
            相关 Issue 列表
        """
        issues = []

        # 从代码注释中提取 Issue 引用
        file_path = self.project_dir / file
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # 查找 Issue 引用模式
                patterns = [
                    r'#(\d+)',  # GitHub #123
                    r'Issue[:\s]+#?(\d+)',  # Issue #123
                    r'([A-Z]+-\d+)',  # Jira PROJ-123
                    r'https://github\.com/[^/]+/[^/]+/issues/(\d+)',
                    r'https://gitlab\.com/[^/]+/[^/]+/-/issues/(\d+)',
                ]

                found_ids = set()
                for pattern in patterns:
                    for match in re.finditer(pattern, content):
                        issue_id = match.group(1) if match.lastindex else match.group(0)

                        if issue_id not in found_ids:
                            found_ids.add(issue_id)
                            issue = self._fetch_issue(issue_id)
                            if issue:
                                issue.related_files = [file]
                                issues.append(issue)

            except Exception:
                pass

        # 从关联数据中查找
        for qa_id, issue_urls in self._links.items():
            qa_files = self._get_qa_files(qa_id)
            if file in qa_files:
                for issue_url in issue_urls:
                    issue = self._fetch_issue_by_url(issue_url)
                    if issue:
                        issues.append(issue)

        return issues

    def _create_github_issue(self, title: str, body: str,
                             labels: List[str] = None) -> Optional[str]:
        """创建 GitHub Issue"""
        if not self.config.get('repo'):
            return None

        try:
            cmd = ['gh', 'issue', 'create',
                   '--repo', self.config['repo'],
                   '--title', title,
                   '--body', body]

            if labels:
                cmd.extend(['--label', ','.join(labels)])

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return None

    def _create_gitlab_issue(self, title: str, body: str,
                             labels: List[str] = None) -> Optional[str]:
        """创建 GitLab Issue"""
        # GitLab API 调用
        return None

    def _create_jira_issue(self, title: str, body: str,
                           labels: List[str] = None) -> Optional[str]:
        """创建 Jira Issue"""
        # Jira API 调用
        return None

    def _fetch_issue_status(self, issue_url: str) -> Optional[str]:
        """获取 Issue 状态"""
        if 'github.com' in issue_url:
            return self._fetch_github_issue_status(issue_url)
        elif 'gitlab.com' in issue_url:
            return self._fetch_gitlab_issue_status(issue_url)
        return None

    def _fetch_github_issue_status(self, issue_url: str) -> Optional[str]:
        """获取 GitHub Issue 状态"""
        try:
            # 解析 URL 获取 owner/repo/number
            match = re.search(r'github\.com/([^/]+)/([^/]+)/issues/(\d+)', issue_url)
            if match:
                owner, repo, number = match.groups()
                cmd = ['gh', 'issue', 'view', number,
                       '--repo', f'{owner}/{repo}',
                       '--json', 'state']
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    return data.get('state')
        except Exception:
            pass
        return None

    def _fetch_gitlab_issue_status(self, issue_url: str) -> Optional[str]:
        """获取 GitLab Issue 状态"""
        return None

    def _fetch_issue(self, issue_id: str) -> Optional[Issue]:
        """获取 Issue 详情"""
        return None

    def _fetch_issue_by_url(self, issue_url: str) -> Optional[Issue]:
        """通过 URL 获取 Issue"""
        return None

    def _get_qa_content(self, qa_id: str) -> Optional[Dict]:
        """获取问答内容"""
        qa_file = self._meta_dir / 'qa' / f'{qa_id}.json'
        if qa_file.exists():
            with open(qa_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _get_qa_files(self, qa_id: str) -> List[str]:
        """获取问答关联的文件"""
        qa_content = self._get_qa_content(qa_id)
        if qa_content:
            return qa_content.get('file_refs', [])
        return []

    def _format_issue_body(self, qa_id: str, qa_content: Dict) -> str:
        """格式化 Issue 内容"""
        lines = [
            f"**来源问答**: {qa_id}",
            "",
            "### 问题",
            qa_content.get('question', ''),
            "",
            "### 答案摘要",
            qa_content.get('answer', '')[:500],
            "",
        ]

        if qa_content.get('code_refs'):
            lines.append("### 相关代码")
            for ref in qa_content['code_refs'][:5]:
                lines.append(f"- `{ref}`")
            lines.append("")

        if qa_content.get('file_refs'):
            lines.append("### 相关文件")
            for ref in qa_content['file_refs'][:5]:
                lines.append(f"- {ref}")
            lines.append("")

        lines.append("---")
        lines.append(f"*由 Project Assistant 从问答 {qa_id} 创建*")

        return "\n".join(lines)

    def _mark_qa_for_review(self, qa_id: str):
        """标记问答需要审查"""
        # 更新问答状态
        pass

    def _load_links(self):
        """加载关联数据"""
        if self._links_file.exists():
            try:
                with open(self._links_file, 'r', encoding='utf-8') as f:
                    self._links = json.load(f)
            except Exception:
                self._links = {}

    def _save_links(self):
        """保存关联数据"""
        self._links_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._links_file, 'w', encoding='utf-8') as f:
            json.dump(self._links, f, ensure_ascii=False, indent=2)


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: issue_tracker.py <project_dir> [command]")
        print("\nCommands:")
        print("  link <qa_id> <issue_url>      Link QA to Issue")
        print("  unlink <qa_id> <issue_url>    Unlink QA from Issue")
        print("  issues <qa_id>                Get QA issues")
        print("  create <qa_id>                Create Issue from QA")
        print("  sync                          Sync issue status")
        print("  file-issues <file>            Get file related issues")
        sys.exit(1)

    project_dir = sys.argv[1]
    tracker = IssueTrackerIntegration(project_dir)

    if len(sys.argv) < 3:
        print("Please specify a command")
        sys.exit(1)

    command = sys.argv[2]

    if command == 'link':
        if len(sys.argv) < 5:
            print("Usage: issue_tracker.py <project_dir> link <qa_id> <issue_url>")
            sys.exit(1)
        qa_id = sys.argv[3]
        issue_url = sys.argv[4]
        tracker.link_qa_to_issue(qa_id, issue_url)
        print(f"Linked {qa_id} to {issue_url}")

    elif command == 'unlink':
        if len(sys.argv) < 5:
            print("Usage: issue_tracker.py <project_dir> unlink <qa_id> <issue_url>")
            sys.exit(1)
        qa_id = sys.argv[3]
        issue_url = sys.argv[4]
        tracker.unlink_qa_from_issue(qa_id, issue_url)
        print(f"Unlinked {qa_id} from {issue_url}")

    elif command == 'issues':
        if len(sys.argv) < 4:
            print("Usage: issue_tracker.py <project_dir> issues <qa_id>")
            sys.exit(1)
        qa_id = sys.argv[3]
        issues = tracker.get_qa_issues(qa_id)
        print(json.dumps(issues, indent=2))

    elif command == 'create':
        if len(sys.argv) < 4:
            print("Usage: issue_tracker.py <project_dir> create <qa_id>")
            sys.exit(1)
        qa_id = sys.argv[3]
        issue_url = tracker.create_issue_from_qa(qa_id)
        if issue_url:
            print(f"Created issue: {issue_url}")
        else:
            print("Failed to create issue")

    elif command == 'sync':
        result = tracker.sync_issue_status()
        print(json.dumps(result, indent=2))

    elif command == 'file-issues':
        if len(sys.argv) < 4:
            print("Usage: issue_tracker.py <project_dir> file-issues <file>")
            sys.exit(1)
        file_path = sys.argv[3]
        issues = tracker.get_related_issues(file_path)
        for issue in issues:
            print(f"- {issue.id}: {issue.title}")


if __name__ == '__main__':
    main()