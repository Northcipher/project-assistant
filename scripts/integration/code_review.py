#!/usr/bin/env python3
"""
代码审查集成
PR 自动审查建议

特性:
- 分析 PR 变更
- 检测相关问答
- 影响范围分析
- 潜在问题检测
"""

import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ReviewSeverity(Enum):
    """审查严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ReviewSuggestion:
    """审查建议"""
    file: str
    line: int
    severity: ReviewSeverity
    category: str  # security, performance, style, logic
    message: str
    suggestion: str = ""
    related_qa: List[str] = field(default_factory=list)
    related_code: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file': self.file,
            'line': self.line,
            'severity': self.severity.value,
            'category': self.category,
            'message': self.message,
            'suggestion': self.suggestion,
            'related_qa': self.related_qa,
            'related_code': self.related_code,
        }

    def to_markdown(self) -> str:
        """转换为 Markdown"""
        severity_icons = {
            ReviewSeverity.INFO: "ℹ️",
            ReviewSeverity.WARNING: "⚠️",
            ReviewSeverity.ERROR: "❌",
            ReviewSeverity.CRITICAL: "🔥",
        }
        icon = severity_icons.get(self.severity, "")

        lines = [
            f"### {icon} {self.file}:{self.line}",
            f"**[{self.category}]** {self.message}",
            "",
        ]

        if self.suggestion:
            lines.append(f"**建议**: {self.suggestion}")

        if self.related_qa:
            lines.append("**相关问答**:")
            for qa in self.related_qa[:3]:
                lines.append(f"- {qa}")

        return "\n".join(lines)


@dataclass
class ReviewResult:
    """审查结果"""
    pr_number: int
    overall_score: float  # 0-100
    suggestions: List[ReviewSuggestion] = field(default_factory=list)
    impact_analysis: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    review_time: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pr_number': self.pr_number,
            'overall_score': self.overall_score,
            'suggestions': [s.to_dict() for s in self.suggestions],
            'impact_analysis': self.impact_analysis,
            'summary': self.summary,
            'review_time': self.review_time,
        }

    def to_markdown(self) -> str:
        """转换为 Markdown 报告"""
        lines = [
            "## 🔍 代码审查报告",
            "",
            f"**PR**: #{self.pr_number}",
            f"**评分**: {self.overall_score:.0f}/100",
            f"**审查时间**: {self.review_time}",
            "",
            f"### 📋 概要",
            self.summary,
            "",
        ]

        if self.suggestions:
            lines.append(f"### 📝 建议 ({len(self.suggestions)})")
            lines.append("")

            # 按严重程度分组
            by_severity = {}
            for s in self.suggestions:
                sev = s.severity.value
                if sev not in by_severity:
                    by_severity[sev] = []
                by_severity[sev].append(s)

            for sev in ['critical', 'error', 'warning', 'info']:
                if sev in by_severity:
                    for s in by_severity[sev][:5]:  # 限制每类最多 5 个
                        lines.append(s.to_markdown())
                        lines.append("")

        if self.impact_analysis:
            lines.append("### 🎯 影响分析")
            lines.append(f"- 直接影响文件: {self.impact_analysis.get('direct_files', 0)}")
            lines.append(f"- 间接影响文件: {self.impact_analysis.get('indirect_files', 0)}")
            lines.append("")

        lines.append("---")
        lines.append("*🔍 由 Project Assistant 自动审查*")

        return "\n".join(lines)


class CodeReviewAssistant:
    """代码审查助手

    功能:
    - 分析 PR 变更
    - 检测相关问答
    - 影响范围分析
    - 潜在问题检测
    """

    def __init__(self, project_dir: str):
        """初始化

        Args:
            project_dir: 项目目录
        """
        self.project_dir = Path(project_dir).resolve()

    def analyze_pr(self, pr_info: Dict[str, Any]) -> ReviewResult:
        """分析 PR

        Args:
            pr_info: PR 信息

        Returns:
            审查结果
        """
        result = ReviewResult(
            pr_number=pr_info.get('number', 0),
            overall_score=100.0,
            review_time=datetime.now().isoformat(),
        )

        suggestions = []

        # 1. 分析变更文件
        files = pr_info.get('files', [])
        for file_info in files:
            file_path = file_info if isinstance(file_info, str) else file_info.get('path', '')
            file_suggestions = self._analyze_file(file_path, pr_info)
            suggestions.extend(file_suggestions)

        # 2. 检测相关问答
        related_qa = self._detect_related_qa(files)
        if related_qa:
            suggestions.append(ReviewSuggestion(
                file="",
                line=0,
                severity=ReviewSeverity.INFO,
                category="knowledge",
                message=f"发现 {len(related_qa)} 个相关问答",
                related_qa=related_qa[:5],
            ))

        # 3. 影响分析
        impact = self._analyze_impact(files, pr_info.get('changed_functions', []))
        result.impact_analysis = impact

        # 4. 计算评分
        result.overall_score = self._calculate_score(suggestions, impact)

        # 5. 生成摘要
        result.summary = self._generate_summary(suggestions, impact)

        result.suggestions = suggestions
        return result

    def review_file(self, file_path: str) -> List[ReviewSuggestion]:
        """审查单个文件

        Args:
            file_path: 文件路径

        Returns:
            审查建议列表
        """
        suggestions = []

        full_path = self.project_dir / file_path
        if not full_path.exists():
            return suggestions

        # 安全检查
        security_issues = self._check_security(file_path, full_path)
        suggestions.extend(security_issues)

        # 性能检查
        perf_issues = self._check_performance(file_path, full_path)
        suggestions.extend(perf_issues)

        # 代码风格检查
        style_issues = self._check_style(file_path, full_path)
        suggestions.extend(style_issues)

        return suggestions

    def _analyze_file(self, file_path: str, pr_info: Dict) -> List[ReviewSuggestion]:
        """分析单个文件"""
        suggestions = []

        full_path = self.project_dir / file_path
        if not full_path.exists():
            return suggestions

        # 安全检查
        suggestions.extend(self._check_security(file_path, full_path))

        # 性能检查
        suggestions.extend(self._check_performance(file_path, full_path))

        # 检查相关问答
        related = self._get_file_qa(file_path)
        if related:
            suggestions.append(ReviewSuggestion(
                file=file_path,
                line=0,
                severity=ReviewSeverity.INFO,
                category="knowledge",
                message="此文件有相关问答记录",
                related_qa=related[:3],
            ))

        return suggestions

    def _check_security(self, file_path: str, full_path: Path) -> List[ReviewSuggestion]:
        """安全检查"""
        suggestions = []

        # 敏感文件检查
        sensitive_patterns = ['.env', 'secret', 'credential', 'password', 'key', 'token']
        file_lower = file_path.lower()

        for pattern in sensitive_patterns:
            if pattern in file_lower:
                suggestions.append(ReviewSuggestion(
                    file=file_path,
                    line=0,
                    severity=ReviewSeverity.WARNING,
                    category="security",
                    message=f"文件可能包含敏感信息 ({pattern})",
                    suggestion="请确认是否应该提交此文件",
                ))
                break

        # 敏感内容检查
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 密码模式
            import re
            password_pattern = r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?[^"\']{4,}'
            for match in re.finditer(password_pattern, content):
                line = content[:match.start()].count('\n') + 1
                suggestions.append(ReviewSuggestion(
                    file=file_path,
                    line=line,
                    severity=ReviewSeverity.ERROR,
                    category="security",
                    message="发现可能的硬编码密码",
                    suggestion="使用环境变量或配置文件",
                ))

            # API Key 模式
            api_key_pattern = r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[a-zA-Z0-9]{20,}'
            for match in re.finditer(api_key_pattern, content):
                line = content[:match.start()].count('\n') + 1
                suggestions.append(ReviewSuggestion(
                    file=file_path,
                    line=line,
                    severity=ReviewSeverity.ERROR,
                    category="security",
                    message="发现可能的 API Key",
                    suggestion="使用环境变量存储密钥",
                ))

        except Exception:
            pass

        return suggestions

    def _check_performance(self, file_path: str, full_path: Path) -> List[ReviewSuggestion]:
        """性能检查"""
        suggestions = []

        # 文件大小检查
        try:
            size = full_path.stat().st_size
            if size > 100 * 1024:  # 100KB
                suggestions.append(ReviewSuggestion(
                    file=file_path,
                    line=0,
                    severity=ReviewSeverity.INFO,
                    category="performance",
                    message=f"文件较大 ({size / 1024:.1f}KB)",
                    suggestion="考虑拆分文件以提高可维护性",
                ))
        except Exception:
            pass

        # 代码复杂度检查
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 检查嵌套深度
            max_depth = 0
            current_depth = 0
            for char in content:
                if char == '{':
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif char == '}':
                    current_depth = max(0, current_depth - 1)

            if max_depth > 5:
                suggestions.append(ReviewSuggestion(
                    file=file_path,
                    line=0,
                    severity=ReviewSeverity.WARNING,
                    category="performance",
                    message=f"代码嵌套深度较大 ({max_depth}层)",
                    suggestion="考虑重构以降低复杂度",
                ))

        except Exception:
            pass

        return suggestions

    def _check_style(self, file_path: str, full_path: Path) -> List[ReviewSuggestion]:
        """代码风格检查"""
        suggestions = []

        # 文件名检查
        if ' ' in file_path:
            suggestions.append(ReviewSuggestion(
                file=file_path,
                line=0,
                severity=ReviewSeverity.INFO,
                category="style",
                message="文件名包含空格",
                suggestion="使用下划线或连字符替代空格",
            ))

        return suggestions

    def _detect_related_qa(self, files: List[str]) -> List[str]:
        """检测相关问答"""
        related = []

        try:
            from knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph(str(self.project_dir))

            for file_path in files:
                qa_ids = kg.get_related_qa(file_path)
                for qa_id in qa_ids:
                    if qa_id not in related:
                        related.append(qa_id)

        except Exception:
            pass

        return related

    def _get_file_qa(self, file_path: str) -> List[str]:
        """获取文件相关问答"""
        try:
            from knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph(str(self.project_dir))
            return kg.get_related_qa(file_path)
        except Exception:
            return []

    def _analyze_impact(self, files: List[str],
                        changed_functions: List[str]) -> Dict[str, Any]:
        """影响分析"""
        impact = {
            'direct_files': len(files),
            'indirect_files': 0,
            'affected_functions': changed_functions[:10],
            'test_coverage': None,
        }

        try:
            from utils.call_chain_analyzer import CallChainAnalyzer
            analyzer = CallChainAnalyzer(str(self.project_dir))

            indirect_files = set()
            for func in changed_functions[:20]:  # 限制数量
                callers = analyzer.find_callers(func)
                for caller in callers:
                    if caller not in files:
                        indirect_files.add(caller)

            impact['indirect_files'] = len(indirect_files)

        except Exception:
            pass

        return impact

    def _calculate_score(self, suggestions: List[ReviewSuggestion],
                         impact: Dict) -> float:
        """计算审查评分"""
        score = 100.0

        for s in suggestions:
            if s.severity == ReviewSeverity.CRITICAL:
                score -= 20
            elif s.severity == ReviewSeverity.ERROR:
                score -= 10
            elif s.severity == ReviewSeverity.WARNING:
                score -= 5
            elif s.severity == ReviewSeverity.INFO:
                score -= 1

        # 影响范围惩罚
        if impact.get('indirect_files', 0) > 10:
            score -= 10

        return max(0, min(100, score))

    def _generate_summary(self, suggestions: List[ReviewSuggestion],
                          impact: Dict) -> str:
        """生成摘要"""
        critical = len([s for s in suggestions if s.severity == ReviewSeverity.CRITICAL])
        errors = len([s for s in suggestions if s.severity == ReviewSeverity.ERROR])
        warnings = len([s for s in suggestions if s.severity == ReviewSeverity.WARNING])

        if critical > 0:
            return f"发现 {critical} 个严重问题，建议修复后再合并。"
        elif errors > 0:
            return f"发现 {errors} 个错误，请审查后修复。"
        elif warnings > 0:
            return f"发现 {warnings} 个警告，建议关注。"
        elif impact.get('indirect_files', 0) > 5:
            return f"变更影响范围较大，请仔细审查。"
        else:
            return "代码审查通过，未发现明显问题。"

    def detect_issues(self, diff: str) -> List[ReviewSuggestion]:
        """检测 diff 中的问题"""
        suggestions = []

        # 检测 TODO/FIXME
        import re
        for i, line in enumerate(diff.split('\n'), 1):
            if line.startswith('+'):
                if 'TODO' in line or 'FIXME' in line:
                    suggestions.append(ReviewSuggestion(
                        file="",
                        line=i,
                        severity=ReviewSeverity.INFO,
                        category="maintenance",
                        message="发现 TODO/FIXME 注释",
                        suggestion="请确保在合适的时间处理",
                    ))

        return suggestions


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: code_review.py <project_dir> [command]")
        print("\nCommands:")
        print("  review-file <file>       Review a single file")
        print("  review-pr <pr_number>    Review a PR")
        sys.exit(1)

    project_dir = sys.argv[1]
    assistant = CodeReviewAssistant(project_dir)

    if len(sys.argv) < 3:
        print("Please specify a command")
        sys.exit(1)

    command = sys.argv[2]

    if command == 'review-file':
        if len(sys.argv) < 4:
            print("Usage: code_review.py <project_dir> review-file <file>")
            sys.exit(1)
        file_path = sys.argv[3]
        suggestions = assistant.review_file(file_path)
        for s in suggestions:
            print(f"[{s.severity.value}] {s.file}:{s.line} - {s.message}")

    elif command == 'review-pr':
        if len(sys.argv) < 4:
            print("Usage: code_review.py <project_dir> review-pr <pr_number>")
            sys.exit(1)
        pr_number = int(sys.argv[3])
        result = assistant.analyze_pr({'number': pr_number, 'files': []})
        print(result.to_markdown())


if __name__ == '__main__':
    main()