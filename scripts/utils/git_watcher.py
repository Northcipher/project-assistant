#!/usr/bin/env python3
"""
Git 变更检测器
检测 Git 仓库中的变更文件和差异

特性：
- 未提交变更检测
- 提交间差异检测
- 文件差异内容获取
- 分支比较
"""

import os
import sys
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from enum import Enum


class GitChangeType(Enum):
    """Git 变更类型"""
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"
    UNTRACKED = "?"
    UNMERGED = "U"
    IGNORED = "!"


@dataclass
class GitFileChange:
    """Git 文件变更"""
    file_path: str
    change_type: GitChangeType
    old_path: str = ""  # 用于 RENAMED
    staged: bool = False
    insertions: int = 0
    deletions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_path': self.file_path,
            'change_type': self.change_type.value,
            'old_path': self.old_path,
            'staged': self.staged,
            'insertions': self.insertions,
            'deletions': self.deletions,
        }


@dataclass
class GitDiff:
    """Git 差异"""
    file_path: str
    old_content: str
    new_content: str
    hunks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_path': self.file_path,
            'hunks': self.hunks,
        }


@dataclass
class CommitInfo:
    """提交信息"""
    hash: str
    short_hash: str
    author: str
    date: str
    message: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'hash': self.hash,
            'short_hash': self.short_hash,
            'author': self.author,
            'date': self.date,
            'message': self.message,
            'files_changed': self.files_changed,
            'insertions': self.insertions,
            'deletions': self.deletions,
        }


class GitWatcher:
    """Git 变更检测器"""

    def __init__(self, project_dir: str, timeout: int = 10):
        """初始化 Git 检测器

        Args:
            project_dir: 项目目录
            timeout: 命令超时时间（秒）
        """
        self.project_dir = Path(project_dir).resolve()
        self.timeout = timeout
        self._is_repo = None

    @property
    def is_repo(self) -> bool:
        """检查是否是 Git 仓库"""
        if self._is_repo is None:
            self._is_repo = self._check_is_repo()
        return self._is_repo

    def _check_is_repo(self) -> bool:
        """检查是否是 Git 仓库"""
        try:
            r = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.project_dir,
                capture_output=True,
                timeout=self.timeout,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _run_git(self, *args, check: bool = False) -> Tuple[int, str, str]:
        """运行 Git 命令"""
        try:
            r = subprocess.run(
                ['git'] + list(args),
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    def get_current_branch(self) -> Optional[str]:
        """获取当前分支名"""
        if not self.is_repo:
            return None

        code, stdout, _ = self._run_git('branch', '--show-current')
        if code == 0:
            return stdout.strip()
        return None

    def get_uncommitted_changes(self, include_untracked: bool = True) -> List[GitFileChange]:
        """获取未提交的变更文件

        Args:
            include_untracked: 是否包含未跟踪的文件

        Returns:
            变更文件列表
        """
        if not self.is_repo:
            return []

        changes = []

        # 获取暂存区变更
        code, stdout, _ = self._run_git('diff', '--cached', '--name-status')
        if code == 0:
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                change = self._parse_change_line(line, staged=True)
                if change:
                    changes.append(change)

        # 获取工作区变更
        code, stdout, _ = self._run_git('diff', '--name-status')
        if code == 0:
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                change = self._parse_change_line(line, staged=False)
                if change:
                    changes.append(change)

        # 获取未跟踪文件
        if include_untracked:
            code, stdout, _ = self._run_git('ls-files', '--others', '--exclude-standard')
            if code == 0:
                for line in stdout.strip().split('\n'):
                    if line:
                        changes.append(GitFileChange(
                            file_path=line,
                            change_type=GitChangeType.UNTRACKED,
                            staged=False,
                        ))

        return changes

    def _parse_change_line(self, line: str, staged: bool) -> Optional[GitFileChange]:
        """解析变更行"""
        parts = line.split('\t')
        if not parts:
            return None

        status = parts[0][0]  # 取第一个字符
        file_path = parts[1] if len(parts) > 1 else parts[0][1:]

        change_type_map = {
            'A': GitChangeType.ADDED,
            'M': GitChangeType.MODIFIED,
            'D': GitChangeType.DELETED,
            'R': GitChangeType.RENAMED,
            'C': GitChangeType.COPIED,
        }

        change_type = change_type_map.get(status)
        if not change_type:
            return None

        old_path = ""
        if change_type == GitChangeType.RENAMED and len(parts) > 2:
            old_path = parts[1]
            file_path = parts[2]

        return GitFileChange(
            file_path=file_path,
            change_type=change_type,
            old_path=old_path,
            staged=staged,
        )

    def get_diff_files(self, since_commit: str = "HEAD~1",
                       until_commit: str = "HEAD") -> List[GitFileChange]:
        """获取指定提交间的变更文件

        Args:
            since_commit: 起始提交
            until_commit: 结束提交

        Returns:
            变更文件列表
        """
        if not self.is_repo:
            return []

        changes = []
        code, stdout, _ = self._run_git(
            'diff', '--name-status', since_commit, until_commit
        )

        if code == 0:
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                change = self._parse_change_line(line, staged=False)
                if change:
                    changes.append(change)

        return changes

    def get_file_diff(self, file_path: str,
                      staged: bool = False,
                      since_commit: str = None) -> Optional[str]:
        """获取文件差异内容

        Args:
            file_path: 文件路径
            staged: 是否获取暂存区差异
            since_commit: 起始提交（可选）

        Returns:
            差异内容
        """
        if not self.is_repo:
            return None

        args = ['git', 'diff']

        if staged:
            args.append('--cached')

        if since_commit:
            args.extend([since_commit, '--', file_path])
        else:
            args.extend(['--', file_path])

        code, stdout, _ = self._run_git(*args[1:])
        return stdout if code == 0 else None

    def get_file_diff_stats(self, file_path: str) -> Dict[str, int]:
        """获取文件差异统计

        Args:
            file_path: 文件路径

        Returns:
            统计数据
        """
        if not self.is_repo:
            return {'insertions': 0, 'deletions': 0}

        code, stdout, _ = self._run_git(
            'diff', '--numstat', '--', file_path
        )

        if code == 0 and stdout:
            parts = stdout.strip().split()
            if len(parts) >= 2:
                try:
                    return {
                        'insertions': int(parts[0]) if parts[0] != '-' else 0,
                        'deletions': int(parts[1]) if parts[1] != '-' else 0,
                    }
                except ValueError:
                    pass

        return {'insertions': 0, 'deletions': 0}

    def get_recent_commits(self, count: int = 10,
                           branch: str = None) -> List[CommitInfo]:
        """获取最近提交

        Args:
            count: 提交数量
            branch: 分支名（可选）

        Returns:
            提交列表
        """
        if not self.is_repo:
            return []

        commits = []

        args = [
            'log',
            f'-{count}',
            '--format=%H|%h|%an|%ci|%s',
            '--shortstat',
        ]

        if branch:
            args.append(branch)

        code, stdout, _ = self._run_git(*args)

        if code == 0:
            lines = stdout.strip().split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]
                if '|' in line:
                    parts = line.split('|', 4)
                    if len(parts) >= 5:
                        commit = CommitInfo(
                            hash=parts[0],
                            short_hash=parts[1],
                            author=parts[2],
                            date=parts[3],
                            message=parts[4],
                        )

                        # 下一行可能是统计信息
                        if i + 1 < len(lines) and 'file' in lines[i + 1]:
                            stat_line = lines[i + 1]
                            commit.files_changed = self._parse_stat(
                                stat_line, 'file'
                            )
                            commit.insertions = self._parse_stat(
                                stat_line, 'insertion'
                            )
                            commit.deletions = self._parse_stat(
                                stat_line, 'deletion'
                            )
                            i += 1

                        commits.append(commit)
                i += 1

        return commits

    def _parse_stat(self, line: str, keyword: str) -> int:
        """解析统计行"""
        import re
        pattern = rf'(\d+)\s+{keyword}'
        match = re.search(pattern, line)
        return int(match.group(1)) if match else 0

    def get_branches(self, include_remote: bool = True) -> Dict[str, List[str]]:
        """获取分支列表

        Args:
            include_remote: 是否包含远程分支

        Returns:
            分支列表 {'local': [...], 'remote': [...]}
        """
        if not self.is_repo:
            return {'local': [], 'remote': []}

        result = {'local': [], 'remote': []}

        # 本地分支
        code, stdout, _ = self._run_git('branch', '--format=%(refname:short)')
        if code == 0:
            result['local'] = [b.strip() for b in stdout.strip().split('\n') if b.strip()]

        # 远程分支
        if include_remote:
            code, stdout, _ = self._run_git('branch', '-r', '--format=%(refname:short)')
            if code == 0:
                result['remote'] = [b.strip() for b in stdout.strip().split('\n') if b.strip()]

        return result

    def get_file_history(self, file_path: str, count: int = 10) -> List[CommitInfo]:
        """获取文件历史

        Args:
            file_path: 文件路径
            count: 提交数量

        Returns:
            提交列表
        """
        if not self.is_repo:
            return []

        code, stdout, _ = self._run_git(
            'log', f'-{count}', '--format=%H|%h|%an|%ci|%s', '--', file_path
        )

        commits = []
        if code == 0:
            for line in stdout.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|', 4)
                    if len(parts) >= 5:
                        commits.append(CommitInfo(
                            hash=parts[0],
                            short_hash=parts[1],
                            author=parts[2],
                            date=parts[3],
                            message=parts[4],
                        ))

        return commits

    def get_status(self) -> Dict[str, Any]:
        """获取 Git 状态摘要"""
        if not self.is_repo:
            return {'is_repo': False}

        return {
            'is_repo': True,
            'branch': self.get_current_branch(),
            'has_uncommitted': len(self.get_uncommitted_changes(include_untracked=False)) > 0,
            'has_untracked': len(self.get_uncommitted_changes()) > 0,
            'recent_commits': [c.to_dict() for c in self.get_recent_commits(5)],
        }

    def get_blame(self, file_path: str) -> List[Dict[str, Any]]:
        """获取文件 blame 信息

        Args:
            file_path: 文件路径

        Returns:
            blame 信息列表
        """
        if not self.is_repo:
            return []

        code, stdout, _ = self._run_git(
            'blame', '--line-porcelain', '--', file_path
        )

        if code != 0:
            return []

        blames = []
        current = {}

        for line in stdout.split('\n'):
            if line.startswith('author '):
                current['author'] = line[7:]
            elif line.startswith('author-time '):
                try:
                    ts = int(line[12:])
                    current['date'] = datetime.fromtimestamp(ts).isoformat()
                except Exception:
                    pass
            elif line.startswith('\t'):
                # 代码行
                current['code'] = line[1:]
                if 'author' in current:
                    blames.append(current)
                current = {}

        return blames


def get_git_watcher(project_dir: str) -> GitWatcher:
    """获取 Git 检测器的便捷函数"""
    return GitWatcher(project_dir)


def main():
    """命令行接口"""
    import json

    if len(sys.argv) < 2:
        print("Usage: git_watcher.py <project_dir> [command]")
        print("\nCommands:")
        print("  status              Show git status")
        print("  changes             Show uncommitted changes")
        print("  diff <file>         Show file diff")
        print("  commits [N]         Show recent N commits")
        print("  branches            List branches")
        print("  history <file>      Show file history")
        print("  blame <file>        Show file blame")
        sys.exit(1)

    project_dir = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else 'status'

    watcher = GitWatcher(project_dir)

    if not watcher.is_repo:
        print(f"Not a git repository: {project_dir}")
        sys.exit(1)

    if command == 'status':
        status = watcher.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))

    elif command == 'changes':
        changes = watcher.get_uncommitted_changes()
        if changes:
            print(f"Uncommitted changes ({len(changes)}):")
            for c in changes:
                staged = "[staged]" if c.staged else "[unstaged]"
                print(f"  {staged} {c.change_type.value} {c.file_path}")
        else:
            print("No uncommitted changes")

    elif command == 'diff':
        if len(sys.argv) < 4:
            print("Usage: git_watcher.py <project_dir> diff <file>")
            sys.exit(1)
        file_path = sys.argv[3]
        diff = watcher.get_file_diff(file_path)
        if diff:
            print(diff)
        else:
            print("No diff")

    elif command == 'commits':
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        commits = watcher.get_recent_commits(count)
        for c in commits:
            print(f"\n{c.short_hash} {c.message}")
            print(f"  Author: {c.author}")
            print(f"  Date: {c.date}")
            if c.files_changed:
                print(f"  Files: {c.files_changed}, +{c.insertions}/-{c.deletions}")

    elif command == 'branches':
        branches = watcher.get_branches()
        print("Local branches:")
        for b in branches['local']:
            print(f"  - {b}")
        print("\nRemote branches:")
        for b in branches['remote'][:10]:
            print(f"  - {b}")
        if len(branches['remote']) > 10:
            print(f"  ... and {len(branches['remote']) - 10} more")

    elif command == 'history':
        if len(sys.argv) < 4:
            print("Usage: git_watcher.py <project_dir> history <file>")
            sys.exit(1)
        file_path = sys.argv[3]
        commits = watcher.get_file_history(file_path)
        print(f"History for {file_path}:")
        for c in commits:
            print(f"  {c.short_hash} {c.date} {c.author}: {c.message[:50]}")

    elif command == 'blame':
        if len(sys.argv) < 4:
            print("Usage: git_watcher.py <project_dir> blame <file>")
            sys.exit(1)
        file_path = sys.argv[3]
        blames = watcher.get_blame(file_path)
        print(f"Blame for {file_path}:")
        for b in blames[:20]:
            print(f"  {b.get('author', 'unknown')} ({b.get('date', '')[:10]}): {b.get('code', '')[:50]}")
        if len(blames) > 20:
            print(f"  ... and {len(blames) - 20} more lines")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()