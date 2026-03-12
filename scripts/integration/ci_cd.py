#!/usr/bin/env python3
"""
CI/CD 集成
流水线自动触发分析

特性:
- PR 创建时分析
- 合并时更新索引
- 生成分析报告
- 支持 GitHub Actions, GitLab CI, Jenkins
"""

import os
import json
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PRAction(Enum):
    """PR 操作类型"""
    OPENED = "opened"
    SYNCHRONIZE = "synchronize"
    CLOSED = "closed"
    MERGED = "merged"


@dataclass
class PRInfo:
    """PR 信息"""
    number: int
    title: str
    author: str
    source_branch: str
    target_branch: str
    action: PRAction = PRAction.OPENED
    files: List[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    changed_functions: List[str] = field(default_factory=list)
    url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'number': self.number,
            'title': self.title,
            'author': self.author,
            'source_branch': self.source_branch,
            'target_branch': self.target_branch,
            'action': self.action.value,
            'files': self.files,
            'additions': self.additions,
            'deletions': self.deletions,
            'changed_functions': self.changed_functions,
            'url': self.url,
        }


@dataclass
class MergeInfo:
    """合并信息"""
    commit_sha: str
    author: str
    message: str
    merged_at: str
    pr_number: Optional[int] = None
    files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'commit_sha': self.commit_sha,
            'author': self.author,
            'message': self.message,
            'merged_at': self.merged_at,
            'pr_number': self.pr_number,
            'files': self.files,
        }


@dataclass
class AnalysisReport:
    """分析报告"""
    pr_number: int
    analysis_time: str
    summary: str
    findings: List[Dict[str, Any]] = field(default_factory=list)
    related_qa: List[Dict[str, Any]] = field(default_factory=list)
    impact_analysis: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pr_number': self.pr_number,
            'analysis_time': self.analysis_time,
            'summary': self.summary,
            'findings': self.findings,
            'related_qa': self.related_qa,
            'impact_analysis': self.impact_analysis,
            'recommendations': self.recommendations,
            'warnings': self.warnings,
        }

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        lines = [
            "## 🤖 Project Assistant 分析报告",
            "",
            f"**PR**: #{self.pr_number}",
            f"**分析时间**: {self.analysis_time}",
            "",
            f"### 📋 概要",
            self.summary,
            "",
        ]

        if self.warnings:
            lines.append("### ⚠️ 警告")
            for w in self.warnings:
                lines.append(f"- {w}")
            lines.append("")

        if self.findings:
            lines.append("### 🔍 发现")
            for f in self.findings:
                lines.append(f"- **{f.get('type', '未知')}**: {f.get('message', '')}")
            lines.append("")

        if self.related_qa:
            lines.append("### 📚 相关问答")
            for qa in self.related_qa:
                lines.append(f"- [{qa.get('id')}] {qa.get('question', '')[:50]}...")
            lines.append("")

        if self.impact_analysis:
            lines.append("### 🎯 影响分析")
            lines.append(f"- 直接影响文件: {self.impact_analysis.get('direct_files', 0)}")
            lines.append(f"- 间接影响文件: {self.impact_analysis.get('indirect_files', 0)}")
            lines.append("")

        if self.recommendations:
            lines.append("### 💡 建议")
            for r in self.recommendations:
                lines.append(f"- {r}")
            lines.append("")

        lines.append("---")
        lines.append("*🤖 由 Project Assistant 自动生成*")

        return "\n".join(lines)


class CICDIntegration:
    """CI/CD 集成"""

    def __init__(self, project_dir: str, platform: str = "github"):
        """初始化

        Args:
            project_dir: 项目目录
            platform: CI 平台 (github, gitlab, jenkins)
        """
        self.project_dir = Path(project_dir).resolve()
        self.platform = platform

    def on_pr_created(self, pr: PRInfo) -> AnalysisReport:
        """PR 创建时触发

        Args:
            pr: PR 信息

        Returns:
            分析报告
        """
        report = AnalysisReport(
            pr_number=pr.number,
            analysis_time=datetime.now().isoformat(),
            summary="",
        )

        # 1. 分析变更文件
        findings = self._analyze_changed_files(pr.files)
        report.findings = findings

        # 2. 检测影响的问答
        related_qa = self._detect_affected_qa(pr.files)
        report.related_qa = related_qa

        # 3. 影响分析
        impact = self._analyze_impact(pr.files, pr.changed_functions)
        report.impact_analysis = impact

        # 4. 生成摘要和建议
        report.summary = self._generate_summary(findings, impact)
        report.recommendations = self._generate_recommendations(findings, impact)
        report.warnings = self._detect_warnings(pr)

        return report

    def on_merge(self, merge: MergeInfo) -> Dict[str, Any]:
        """合并时更新索引

        Args:
            merge: 合并信息

        Returns:
            更新结果
        """
        result = {
            'commit': merge.commit_sha,
            'updated': False,
            'files_processed': 0,
            'qa_outdated': [],
            'errors': [],
        }

        try:
            # 更新索引
            from indexer.lazy_indexer import LazyIndexer
            indexer = LazyIndexer(str(self.project_dir))

            update_result = indexer.incremental_update(merge.files)
            result['updated'] = True
            result['files_processed'] = update_result.get('files_processed', 0)

            # 检测过期问答
            from knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph(str(self.project_dir))

            for file_path in merge.files:
                related = kg.get_related_qa(file_path)
                for qa_id in related:
                    if qa_id not in result['qa_outdated']:
                        result['qa_outdated'].append(qa_id)

        except Exception as e:
            result['errors'].append(str(e))

        return result

    def generate_report(self, pr: PRInfo, format: str = "markdown") -> str:
        """生成分析报告

        Args:
            pr: PR 信息
            format: 输出格式 (markdown, json, html)

        Returns:
            报告内容
        """
        report = self.on_pr_created(pr)

        if format == "json":
            return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        elif format == "html":
            return self._to_html(report)
        else:
            return report.to_markdown()

    def _analyze_changed_files(self, files: List[str]) -> List[Dict]:
        """分析变更文件"""
        findings = []

        for file_path in files:
            # 检查敏感信息
            if self._contains_sensitive_info(file_path):
                findings.append({
                    'type': 'security',
                    'severity': 'high',
                    'file': file_path,
                    'message': '可能包含敏感信息',
                })

            # 检查大文件
            full_path = self.project_dir / file_path
            if full_path.exists():
                size = full_path.stat().st_size
                if size > 500 * 1024:  # 500KB
                    findings.append({
                        'type': 'performance',
                        'severity': 'medium',
                        'file': file_path,
                        'message': f'文件较大 ({size / 1024:.1f}KB)',
                    })

        return findings

    def _detect_affected_qa(self, files: List[str]) -> List[Dict]:
        """检测受影响的问答"""
        related = []

        try:
            from knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph(str(self.project_dir))

            for file_path in files:
                qa_ids = kg.get_related_qa(file_path)
                for qa_id in qa_ids:
                    related.append({
                        'id': qa_id,
                        'file': file_path,
                    })

        except Exception:
            pass

        return related

    def _analyze_impact(self, files: List[str],
                        changed_functions: List[str]) -> Dict[str, Any]:
        """影响分析"""
        impact = {
            'direct_files': len(files),
            'indirect_files': 0,
            'affected_functions': [],
            'test_coverage': 0,
        }

        try:
            from utils.call_chain_analyzer import CallChainAnalyzer
            analyzer = CallChainAnalyzer(str(self.project_dir))

            indirect_files = set()
            for func in changed_functions:
                callers = analyzer.find_callers(func)
                for caller in callers:
                    if caller not in files:
                        indirect_files.add(caller)

            impact['indirect_files'] = len(indirect_files)
            impact['affected_functions'] = changed_functions[:10]

        except Exception:
            pass

        return impact

    def _generate_summary(self, findings: List[Dict],
                          impact: Dict) -> str:
        """生成摘要"""
        if not findings and impact.get('direct_files', 0) < 5:
            return "本次变更较小，未发现明显问题。"
        elif findings:
            high_severity = len([f for f in findings if f.get('severity') == 'high'])
            if high_severity > 0:
                return f"发现 {high_severity} 个高严重性问题，请关注。"
            return f"本次变更涉及 {impact.get('direct_files', 0)} 个文件，建议仔细审查。"
        else:
            return f"本次变更涉及 {impact.get('direct_files', 0)} 个文件。"

    def _generate_recommendations(self, findings: List[Dict],
                                   impact: Dict) -> List[str]:
        """生成建议"""
        recommendations = []

        if impact.get('indirect_files', 0) > 0:
            recommendations.append(f"建议检查 {impact['indirect_files']} 个间接影响文件")

        if impact.get('affected_functions'):
            recommendations.append("建议更新相关单元测试")

        for f in findings:
            if f.get('type') == 'security':
                recommendations.append("请检查敏感信息是否应该提交")

        return recommendations

    def _detect_warnings(self, pr: PRInfo) -> List[str]:
        """检测警告"""
        warnings = []

        # 检查大 PR
        if pr.additions + pr.deletions > 1000:
            warnings.append(f"PR 较大 (+{pr.additions}/-{pr.deletions})，建议拆分")

        # 检查文件数量
        if len(pr.files) > 20:
            warnings.append(f"涉及 {len(pr.files)} 个文件，建议拆分 PR")

        return warnings

    def _contains_sensitive_info(self, file_path: str) -> bool:
        """检查是否包含敏感信息"""
        sensitive_patterns = ['.env', 'secret', 'credential', 'password', 'key']
        file_lower = file_path.lower()
        return any(p in file_lower for p in sensitive_patterns)

    def _to_html(self, report: AnalysisReport) -> str:
        """转换为 HTML"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>分析报告 - PR #{report.pr_number}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .warning {{ color: #d9534f; }}
        .success {{ color: #5cb85c; }}
    </style>
</head>
<body>
    <h1>🤖 Project Assistant 分析报告</h1>
    <p>PR: #{report.pr_number}</p>
    <p>分析时间: {report.analysis_time}</p>
    <h2>概要</h2>
    <p>{report.summary}</p>
</body>
</html>
"""

    def generate_github_actions_config(self) -> str:
        """生成 GitHub Actions 配置"""
        return """name: Project Assistant Analysis
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt || true

      - name: Run Analysis
        id: analysis
        run: |
          python scripts/cli.py init . --output report.json

      - name: Comment PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('report.json', 'utf8'));

            const body = `## 🤖 分析报告

            **项目类型**: ${report.project_type || 'Unknown'}
            **语言**: ${report.language || 'Unknown'}

            ### 检查结果
            - 安全扫描: ${report.steps?.security?.status || 'skipped'}
            - 项目检测: ${report.steps?.detection?.status || 'skipped'}

            ---
            *由 Project Assistant 自动生成*`;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
"""

    def generate_gitlab_ci_config(self) -> str:
        """生成 GitLab CI 配置"""
        return """project-assistant:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt || true
    - python scripts/cli.py init .
  artifacts:
    reports:
      junit: report.xml
  only:
    - merge_requests
"""


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: ci_cd.py <project_dir> [command]")
        print("\nCommands:")
        print("  analyze-pr <pr_number>           Analyze a PR")
        print("  on-merge <commit_sha>            Handle merge event")
        print("  generate-config <platform>       Generate CI config")
        sys.exit(1)

    project_dir = sys.argv[1]
    cicd = CICDIntegration(project_dir)

    if len(sys.argv) < 3:
        print("Please specify a command")
        sys.exit(1)

    command = sys.argv[2]

    if command == 'analyze-pr':
        if len(sys.argv) < 4:
            print("Usage: ci_cd.py <project_dir> analyze-pr <pr_number>")
            sys.exit(1)
        pr_number = int(sys.argv[3])
        pr = PRInfo(
            number=pr_number,
            title="Test PR",
            author="test",
            source_branch="feature",
            target_branch="main",
            files=[],
        )
        report = cicd.on_pr_created(pr)
        print(report.to_markdown())

    elif command == 'on-merge':
        if len(sys.argv) < 4:
            print("Usage: ci_cd.py <project_dir> on-merge <commit_sha>")
            sys.exit(1)
        commit_sha = sys.argv[3]
        merge = MergeInfo(
            commit_sha=commit_sha,
            author="test",
            message="Test merge",
            merged_at=datetime.now().isoformat(),
        )
        result = cicd.on_merge(merge)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == 'generate-config':
        platform = sys.argv[4] if len(sys.argv) > 4 else 'github'
        if platform == 'github':
            print(cicd.generate_github_actions_config())
        elif platform == 'gitlab':
            print(cicd.generate_gitlab_ci_config())


if __name__ == '__main__':
    main()