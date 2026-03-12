#!/usr/bin/env python3
"""
AI 增强分析器
使用启发式规则进行代码质量分析

特性：
- 代码质量预测
- 代码异味检测
- 重构建议
- 安全问题检测
- 本地计算，不依赖 LLM
"""

import os
import re
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter


class Severity(Enum):
    """严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Issue:
    """问题"""
    file: str
    line: int
    type: str
    message: str
    severity: Severity
    suggestion: str = ""


@dataclass
class CodeSmell:
    """代码异味"""
    file: str
    line: int
    smell_type: str
    description: str
    refactoring: str = ""


@dataclass
class QualityScore:
    """质量分数"""
    overall: float
    maintainability: float
    readability: float
    complexity: float
    security: float
    details: Dict[str, Any] = field(default_factory=dict)


class AIAnalyzer:
    """AI 增强分析器"""

    # 代码异味模式
    CODE_SMELLS = {
        # 长方法
        'long_method': {
            'threshold': 50,
            'message': '方法过长，建议拆分',
            'refactoring': 'Extract Method',
        },

        # 长参数列表
        'long_parameter_list': {
            'threshold': 4,
            'message': '参数列表过长，建议使用对象封装',
            'refactoring': 'Introduce Parameter Object',
        },

        # 深层嵌套
        'deep_nesting': {
            'threshold': 3,
            'message': '嵌套层级过深，建议提取方法',
            'refactoring': 'Extract Method or Guard Clauses',
        },

        # 魔法数字
        'magic_number': {
            'pattern': r'(?<!["\'])\b\d{2,}\b(?!\s*[;)\]])',
            'message': '发现魔法数字，建议使用常量',
            'refactoring': 'Replace Magic Number with Constant',
        },

        # 重复代码（简化检测）
        'duplicate_code': {
            'min_lines': 5,
            'message': '可能存在重复代码',
            'refactoring': 'Extract Method',
        },

        # 过长行
        'long_line': {
            'threshold': 120,
            'message': '代码行过长，影响可读性',
            'refactoring': 'Split line or use better naming',
        },

        # 注释过多
        'too_many_comments': {
            'ratio': 0.3,
            'message': '注释过多，代码可能需要重构',
            'refactoring': 'Refactor to make code self-documenting',
        },

        # TODO/FIXME
        'todo_fixme': {
            'pattern': r'(TODO|FIXME|XXX|HACK)',
            'message': '发现待办事项',
            'refactoring': '解决待办事项',
        },
    }

    # 安全问题模式
    SECURITY_PATTERNS = [
        {
            'id': 'sql_injection',
            'pattern': r'(?:execute|exec|query)\s*\([^)]*\+',
            'message': '可能的 SQL 注入风险',
            'severity': Severity.ERROR,
            'languages': ['python', 'java', 'php'],
        },
        {
            'id': 'xss_risk',
            'pattern': r'innerHTML\s*=\s*[^;]*\+',
            'message': '可能的 XSS 风险',
            'severity': Severity.ERROR,
            'languages': ['javascript', 'typescript'],
        },
        {
            'id': 'hardcoded_password',
            'pattern': r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']+["\']',
            'message': '硬编码密码',
            'severity': Severity.CRITICAL,
            'languages': None,  # all languages
        },
        {
            'id': 'hardcoded_secret',
            'pattern': r'(?i)(api_key|secret|token)\s*=\s*["\'][^"\']+["\']',
            'message': '硬编码密钥',
            'severity': Severity.CRITICAL,
            'languages': None,
        },
        {
            'id': 'eval_usage',
            'pattern': r'\beval\s*\(',
            'message': '使用 eval() 存在安全风险',
            'severity': Severity.WARNING,
            'languages': ['python', 'javascript'],
        },
        {
            'id': 'command_injection',
            'pattern': r'(?:os\.system|subprocess\.call|exec|shell)\s*\([^)]*\+',
            'message': '可能的命令注入风险',
            'severity': Severity.ERROR,
            'languages': ['python'],
        },
        {
            'id': 'debug_mode',
            'pattern': r'(?:DEBUG|debug)\s*=\s*(?:True|true|1)',
            'message': '调试模式可能未关闭',
            'severity': Severity.WARNING,
            'languages': None,
        },
    ]

    # 复杂度指示器
    COMPLEXITY_PATTERNS = {
        'if': r'\bif\s*\(',
        'elif': r'\belif\s*\(',
        'else': r'\belse\b',
        'for': r'\bfor\s*\(',
        'while': r'\bwhile\s*\(',
        'switch': r'\bswitch\s*\(',
        'case': r'\bcase\s+',
        'catch': r'\bcatch\s*\(',
        'ternary': r'\?[^:]*:',
        'and': r'\band\b|&&',
        'or': r'\bor\b|\|\|',
    }

    def __init__(self, project_dir: str = None):
        """初始化分析器

        Args:
            project_dir: 项目目录
        """
        self.project_dir = Path(project_dir) if project_dir else None
        self.issues: List[Issue] = []
        self.smells: List[CodeSmell] = []

    def analyze_file(self, file_path: str, content: str = None) -> Dict[str, Any]:
        """分析单个文件

        Args:
            file_path: 文件路径
            content: 文件内容（可选）

        Returns:
            分析结果
        """
        path = Path(file_path)
        if content is None:
            try:
                content = path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                return {'error': 'Failed to read file'}

        lines = content.split('\n')
        language = self._detect_language(path.suffix)

        # 清空结果
        self.issues = []
        self.smells = []

        # 检测安全问题
        self._detect_security_issues(file_path, content, language)

        # 检测代码异味
        self._detect_code_smells(file_path, content, lines)

        # 计算质量分数
        quality = self._calculate_quality(content, lines, language)

        return {
            'file': file_path,
            'language': language,
            'lines': len(lines),
            'quality': quality.__dict__,
            'issues': [
                {
                    'line': i.line,
                    'type': i.type,
                    'message': i.message,
                    'severity': i.severity.value,
                    'suggestion': i.suggestion,
                }
                for i in self.issues
            ],
            'code_smells': [
                {
                    'line': s.line,
                    'type': s.smell_type,
                    'description': s.description,
                    'refactoring': s.refactoring,
                }
                for s in self.smells
            ],
            'summary': self._generate_summary(),
        }

    def _detect_language(self, suffix: str) -> str:
        """检测语言"""
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
        }
        return lang_map.get(suffix.lower(), 'unknown')

    def _detect_security_issues(self, file_path: str, content: str, language: str) -> None:
        """检测安全问题"""
        lines = content.split('\n')

        for pattern_info in self.SECURITY_PATTERNS:
            # 检查语言是否匹配
            if pattern_info['languages'] and language not in pattern_info['languages']:
                continue

            pattern = pattern_info['pattern']
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    self.issues.append(Issue(
                        file=file_path,
                        line=i,
                        type=pattern_info['id'],
                        message=pattern_info['message'],
                        severity=pattern_info['severity'],
                        suggestion="请检查并修复此安全问题",
                    ))

    def _detect_code_smells(self, file_path: str, content: str, lines: List[str]) -> None:
        """检测代码异味"""
        # 长行检测
        for i, line in enumerate(lines, 1):
            if len(line) > self.CODE_SMELLS['long_line']['threshold']:
                self.smells.append(CodeSmell(
                    file=file_path,
                    line=i,
                    smell_type='long_line',
                    description=f"代码行长度 {len(line)} 超过阈值 {self.CODE_SMELLS['long_line']['threshold']}",
                    refactoring=self.CODE_SMELLS['long_line']['refactoring'],
                ))

        # 魔法数字检测
        for i, line in enumerate(lines, 1):
            # 排除版本号、日期等
            if re.search(r'\d{4}[/-]\d{2}[/-]\d{2}', line):
                continue
            if re.search(r'["\'].*\d+.*["\']', line):
                continue

            matches = re.findall(self.CODE_SMELLS['magic_number']['pattern'], line)
            for match in matches:
                if int(match) > 10:  # 忽略小数字
                    self.smells.append(CodeSmell(
                        file=file_path,
                        line=i,
                        smell_type='magic_number',
                        description=f"发现魔法数字: {match}",
                        refactoring=self.CODE_SMELLS['magic_number']['refactoring'],
                    ))

        # TODO/FIXME 检测
        for i, line in enumerate(lines, 1):
            match = re.search(self.CODE_SMELLS['todo_fixme']['pattern'], line)
            if match:
                self.smells.append(CodeSmell(
                    file=file_path,
                    line=i,
                    smell_type='todo_fixme',
                    description=f"发现 {match.group(1)}",
                    refactoring=self.CODE_SMELLS['todo_fixme']['refactoring'],
                ))

        # 深层嵌套检测
        self._detect_deep_nesting(file_path, lines)

    def _detect_deep_nesting(self, file_path: str, lines: List[str]) -> None:
        """检测深层嵌套"""
        nesting_level = 0
        nesting_stack = []

        for i, line in enumerate(lines, 1):
            # 计算缩进
            indent = len(line) - len(line.lstrip())

            # 检测代码块开始
            if re.search(r'[{:]\s*$', line) or re.search(r'^\s*(if|for|while|def|class|try|with|switch)\b', line):
                nesting_level += 1
                nesting_stack.append((i, nesting_level))

            # 检测代码块结束
            if '}' in line or (nesting_level > 0 and indent == 0 and line.strip()):
                if nesting_stack:
                    nesting_stack.pop()
                nesting_level = max(0, nesting_level - 1)

            # 检查嵌套深度
            if nesting_level > self.CODE_SMELLS['deep_nesting']['threshold']:
                self.smells.append(CodeSmell(
                    file=file_path,
                    line=i,
                    smell_type='deep_nesting',
                    description=f"嵌套层级 {nesting_level} 超过阈值",
                    refactoring=self.CODE_SMELLS['deep_nesting']['refactoring'],
                ))

    def _calculate_quality(self, content: str, lines: List[str], language: str) -> QualityScore:
        """计算质量分数"""
        # 代码行数（排除空行和注释）
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith(('#', '//', '/*', '*'))]
        total_lines = len(lines)
        code_line_count = len(code_lines)

        # 复杂度分数
        complexity = self._calculate_complexity(content)

        # 可读性分数
        readability = self._calculate_readability(content, lines)

        # 可维护性分数
        maintainability = self._calculate_maintainability(content, lines, complexity)

        # 安全分数
        security = self._calculate_security()

        # 总分
        overall = (maintainability * 0.3 + readability * 0.25 + complexity * 0.25 + security * 0.2)

        return QualityScore(
            overall=round(overall, 2),
            maintainability=round(maintainability, 2),
            readability=round(readability, 2),
            complexity=round(complexity, 2),
            security=round(security, 2),
            details={
                'total_lines': total_lines,
                'code_lines': code_line_count,
                'comment_lines': total_lines - code_line_count,
                'issues_count': len(self.issues),
                'smells_count': len(self.smells),
            },
        )

    def _calculate_complexity(self, content: str) -> float:
        """计算复杂度分数（越高越好）"""
        score = 100.0

        # 计算控制结构数量
        for pattern_name, pattern in self.COMPLEXITY_PATTERNS.items():
            count = len(re.findall(pattern, content))
            penalty = min(count * 2, 20)  # 每个扣2分，最多扣20分
            score -= penalty

        return max(0, min(100, score))

    def _calculate_readability(self, content: str, lines: List[str]) -> float:
        """计算可读性分数"""
        score = 100.0

        # 长行惩罚
        long_lines = sum(1 for l in lines if len(l) > 120)
        score -= min(long_lines * 0.5, 20)

        # 平均行长
        if lines:
            avg_length = sum(len(l) for l in lines) / len(lines)
            if avg_length > 80:
                score -= (avg_length - 80) * 0.2

        # 空行比例
        if lines:
            blank_ratio = sum(1 for l in lines if not l.strip()) / len(lines)
            if blank_ratio < 0.1:
                score -= 10  # 缺少空行分隔

        return max(0, min(100, score))

    def _calculate_maintainability(self, content: str, lines: List[str], complexity: float) -> float:
        """计算可维护性分数"""
        score = 100.0

        # 代码异味惩罚
        smell_count = len(self.smells)
        score -= min(smell_count * 2, 30)

        # 复杂度影响
        score = score * (complexity / 100)

        # TODO/FIXME 惩罚
        todo_count = sum(1 for s in self.smells if s.smell_type == 'todo_fixme')
        score -= todo_count * 1

        return max(0, min(100, score))

    def _calculate_security(self) -> float:
        """计算安全分数"""
        score = 100.0

        for issue in self.issues:
            if issue.severity == Severity.CRITICAL:
                score -= 30
            elif issue.severity == Severity.ERROR:
                score -= 15
            elif issue.severity == Severity.WARNING:
                score -= 5

        return max(0, min(100, score))

    def _generate_summary(self) -> str:
        """生成摘要"""
        if not self.issues and not self.smells:
            return "代码质量良好，未发现明显问题"

        summary_parts = []

        critical_issues = sum(1 for i in self.issues if i.severity == Severity.CRITICAL)
        error_issues = sum(1 for i in self.issues if i.severity == Severity.ERROR)
        warning_issues = sum(1 for i in self.issues if i.severity == Severity.WARNING)

        if critical_issues > 0:
            summary_parts.append(f"发现 {critical_issues} 个严重安全问题")
        if error_issues > 0:
            summary_parts.append(f"发现 {error_issues} 个错误")
        if warning_issues > 0:
            summary_parts.append(f"发现 {warning_issues} 个警告")
        if len(self.smells) > 0:
            summary_parts.append(f"发现 {len(self.smells)} 处代码异味")

        return "，".join(summary_parts) + "。建议进行代码审查和重构。"

    def suggest_refactoring(self, file_path: str, content: str = None) -> List[Dict[str, Any]]:
        """生成重构建议

        Args:
            file_path: 文件路径
            content: 文件内容

        Returns:
            重构建议列表
        """
        if content is None:
            try:
                content = Path(file_path).read_text(encoding='utf-8', errors='ignore')
            except Exception:
                return []

        suggestions = []
        lines = content.split('\n')

        # 检查长方法
        in_function = False
        function_start = 0
        brace_count = 0

        for i, line in enumerate(lines, 1):
            if re.search(r'^\s*(def|function|func|fn)\s+\w+', line):
                if not in_function:
                    function_start = i
                    in_function = True
                    brace_count = 0

            if in_function:
                brace_count += line.count('{') - line.count('}')
                if brace_count <= 0 and ('}' in line or (i - function_start > 5 and not line.strip())):
                    function_length = i - function_start
                    if function_length > self.CODE_SMELLS['long_method']['threshold']:
                        suggestions.append({
                            'type': 'extract_method',
                            'line_start': function_start,
                            'line_end': i,
                            'message': f"方法过长 ({function_length} 行)，建议拆分",
                        })
                    in_function = False

        return suggestions

    def analyze_project(self, project_dir: str = None) -> Dict[str, Any]:
        """分析整个项目

        Args:
            project_dir: 项目目录

        Returns:
            项目分析结果
        """
        project_path = Path(project_dir or self.project_dir)
        if not project_path:
            return {'error': 'No project directory specified'}

        results = []
        total_quality = QualityScore(overall=0, maintainability=0, readability=0, complexity=0, security=0)
        file_count = 0

        exclude_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'build', 'dist', 'target'}

        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for f in files:
                if f.endswith(('.py', '.js', '.ts', '.java', '.go', '.rs', '.c', '.cpp', '.php')):
                    file_path = Path(root) / f
                    result = self.analyze_file(str(file_path))
                    results.append(result)

                    if 'quality' in result:
                        total_quality.overall += result['quality']['overall']
                        total_quality.maintainability += result['quality']['maintainability']
                        total_quality.readability += result['quality']['readability']
                        total_quality.complexity += result['quality']['complexity']
                        total_quality.security += result['quality']['security']
                        file_count += 1

        # 计算平均分
        if file_count > 0:
            avg_quality = QualityScore(
                overall=round(total_quality.overall / file_count, 2),
                maintainability=round(total_quality.maintainability / file_count, 2),
                readability=round(total_quality.readability / file_count, 2),
                complexity=round(total_quality.complexity / file_count, 2),
                security=round(total_quality.security / file_count, 2),
            )
        else:
            avg_quality = QualityScore(overall=0, maintainability=0, readability=0, complexity=0, security=0)

        return {
            'project_dir': str(project_path),
            'files_analyzed': file_count,
            'average_quality': avg_quality.__dict__,
            'total_issues': sum(len(r.get('issues', [])) for r in results),
            'total_smells': sum(len(r.get('code_smells', [])) for r in results),
            'files': results[:20],  # 限制输出
        }


def main():
    """命令行接口"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: ai_analyzer.py <file_or_project> [--project]")
        print("\nOptions:")
        print("  --project    Analyze entire project")
        sys.exit(1)

    target = sys.argv[1]
    is_project = '--project' in sys.argv

    analyzer = AIAnalyzer()

    if is_project:
        result = analyzer.analyze_project(target)
    else:
        result = analyzer.analyze_file(target)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()