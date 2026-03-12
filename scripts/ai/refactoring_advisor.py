#!/usr/bin/env python3
"""
重构顾问
代码质量自动检测和建议

特性:
- 代码重复检测
- 复杂度分析
- 设计模式建议
- 重构应用
"""

import os
import re
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RefactoringType(Enum):
    """重构类型"""
    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    RENAME = "rename"
    MOVE_METHOD = "move_method"
    INLINE_VARIABLE = "inline_variable"
    SIMPLIFY_CONDITIONAL = "simplify_conditional"
    REMOVE_DUPLICATION = "remove_duplication"
    INTRODUCE_PARAMETER = "introduce_parameter"


@dataclass
class RefactoringSuggestion:
    """重构建议"""
    type: RefactoringType
    file: str
    start_line: int
    end_line: int
    message: str
    suggestion: str
    impact: str = "low"  # low, medium, high
    auto_applicable: bool = False
    related_code: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'file': self.file,
            'start_line': self.start_line,
            'end_line': self.end_line,
            'message': self.message,
            'suggestion': self.suggestion,
            'impact': self.impact,
            'auto_applicable': self.auto_applicable,
            'related_code': self.related_code,
        }

    def to_markdown(self) -> str:
        """转换为 Markdown"""
        impact_icons = {'low': '📝', 'medium': '⚠️', 'high': '🔥'}
        icon = impact_icons.get(self.impact, '📝')

        lines = [
            f"### {icon} {self.type.value.replace('_', ' ').title()}",
            f"**位置**: `{self.file}:{self.start_line}-{self.end_line}`",
            f"**问题**: {self.message}",
            f"**建议**: {self.suggestion}",
            "",
        ]
        return "\n".join(lines)


@dataclass
class DuplicationInfo:
    """代码重复信息"""
    pattern: str
    occurrences: List[Dict[str, Any]]
    total_lines: int
    suggested_action: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern': self.pattern[:100],
            'occurrences': self.occurrences,
            'total_lines': self.total_lines,
            'suggested_action': self.suggested_action,
        }


@dataclass
class ComplexityInfo:
    """复杂度信息"""
    function: str
    file: str
    line: int
    cyclomatic_complexity: int
    cognitive_complexity: int
    lines_of_code: int
    parameter_count: int
    nested_depth: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'function': self.function,
            'file': self.file,
            'line': self.line,
            'cyclomatic_complexity': self.cyclomatic_complexity,
            'cognitive_complexity': self.cognitive_complexity,
            'lines_of_code': self.lines_of_code,
            'parameter_count': self.parameter_count,
            'nested_depth': self.nested_depth,
        }


class RefactoringAdvisor:
    """重构顾问

    检测类型:
    - 代码重复
    - 高复杂度
    - 长方法/类
    - 过多参数
    - 深层嵌套
    - 设计模式机会
    """

    # 复杂度阈值
    COMPLEXITY_THRESHOLDS = {
        'cyclomatic_high': 15,
        'cyclomatic_critical': 25,
        'lines_high': 50,
        'lines_critical': 100,
        'parameters_high': 4,
        'parameters_critical': 6,
        'nested_high': 4,
        'nested_critical': 6,
    }

    def __init__(self, project_dir: str):
        """初始化

        Args:
            project_dir: 项目目录
        """
        self.project_dir = Path(project_dir).resolve()
        self._ast_parser = None

        try:
            from ast_parser import ASTParser
            self._ast_parser = ASTParser()
        except ImportError:
            pass

    def analyze(self, file: str = None) -> List[RefactoringSuggestion]:
        """分析重构建议

        Args:
            file: 文件路径（可选，不指定则分析整个项目）

        Returns:
            重构建议列表
        """
        suggestions = []

        if file:
            suggestions.extend(self._analyze_file(file))
        else:
            suggestions.extend(self._analyze_project())

        return suggestions

    def _analyze_file(self, file: str) -> List[RefactoringSuggestion]:
        """分析单个文件"""
        suggestions = []

        full_path = self.project_dir / file
        if not full_path.exists():
            return suggestions

        # 1. 代码重复检测
        suggestions.extend(self._detect_duplicates(file, full_path))

        # 2. 复杂度分析
        suggestions.extend(self._analyze_complexity(file, full_path))

        # 3. 设计模式建议
        suggestions.extend(self._suggest_patterns(file, full_path))

        return suggestions

    def _analyze_project(self) -> List[RefactoringSuggestion]:
        """分析整个项目"""
        suggestions = []

        code_extensions = {'.py', '.js', '.ts', '.java', '.go'}

        for file_path in self.project_dir.rglob('*'):
            if file_path.suffix.lower() in code_extensions:
                if '.git' in str(file_path) or 'node_modules' in str(file_path):
                    continue

                rel_path = str(file_path.relative_to(self.project_dir))
                suggestions.extend(self._analyze_file(rel_path))

        return suggestions[:100]  # 限制数量

    def _detect_duplicates(self, file: str, full_path: Path) -> List[RefactoringSuggestion]:
        """检测代码重复"""
        suggestions = []

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            # 检测重复的代码块 (至少 5 行)
            min_lines = 5
            code_blocks: Dict[str, List[int]] = {}

            for i in range(len(lines) - min_lines + 1):
                block = '\n'.join(lines[i:i + min_lines])
                # 标准化：去除空白和注释
                normalized = self._normalize_code(block)
                if normalized:
                    if normalized not in code_blocks:
                        code_blocks[normalized] = []
                    code_blocks[normalized].append(i + 1)

            # 生成建议
            for normalized, line_nums in code_blocks.items():
                if len(line_nums) > 1:
                    suggestions.append(RefactoringSuggestion(
                        type=RefactoringType.REMOVE_DUPLICATION,
                        file=file,
                        start_line=min(line_nums),
                        end_line=min(line_nums) + min_lines,
                        message=f"检测到重复代码块 ({len(line_nums)} 处)",
                        suggestion="考虑提取为公共方法或函数",
                        impact="medium",
                        related_code=[f"行 {ln}" for ln in line_nums],
                    ))

        except Exception:
            pass

        return suggestions

    def _normalize_code(self, code: str) -> str:
        """标准化代码"""
        # 去除空白
        code = re.sub(r'\s+', ' ', code)
        # 去除注释
        code = re.sub(r'//.*|/\*.*?\*/|#.*', '', code)
        return code.strip()

    def _analyze_complexity(self, file: str, full_path: Path) -> List[RefactoringSuggestion]:
        """分析复杂度"""
        suggestions = []

        if not self._ast_parser:
            return suggestions

        try:
            result = self._ast_parser.parse_file(str(full_path))

            for func in result.get('functions', []):
                name = func.get('name', '')
                line = func.get('line', 0)

                # 获取函数体
                func_body = func.get('body', '')
                lines_of_code = func_body.count('\n') if func_body else 0

                # 计算圈复杂度
                cyclomatic = self._calculate_cyclomatic_complexity(func_body)

                # 计算嵌套深度
                nested_depth = self._calculate_nested_depth(func_body)

                # 参数数量
                params = func.get('parameters', [])
                param_count = len(params) if params else 0

                # 检查复杂度
                if cyclomatic > self.COMPLEXITY_THRESHOLDS['cyclomatic_critical']:
                    suggestions.append(RefactoringSuggestion(
                        type=RefactoringType.EXTRACT_METHOD,
                        file=file,
                        start_line=line,
                        end_line=line,
                        message=f"函数 '{name}' 圈复杂度过高 ({cyclomatic})",
                        suggestion="考虑拆分为多个小函数",
                        impact="high",
                    ))
                elif cyclomatic > self.COMPLEXITY_THRESHOLDS['cyclomatic_high']:
                    suggestions.append(RefactoringSuggestion(
                        type=RefactoringType.SIMPLIFY_CONDITIONAL,
                        file=file,
                        start_line=line,
                        end_line=line,
                        message=f"函数 '{name}' 圈复杂度较高 ({cyclomatic})",
                        suggestion="考虑简化条件逻辑",
                        impact="medium",
                    ))

                # 检查行数
                if lines_of_code > self.COMPLEXITY_THRESHOLDS['lines_critical']:
                    suggestions.append(RefactoringSuggestion(
                        type=RefactoringType.EXTRACT_METHOD,
                        file=file,
                        start_line=line,
                        end_line=line,
                        message=f"函数 '{name}' 行数过多 ({lines_of_code})",
                        suggestion="考虑拆分为多个小函数",
                        impact="high",
                    ))

                # 检查参数数量
                if param_count > self.COMPLEXITY_THRESHOLDS['parameters_critical']:
                    suggestions.append(RefactoringSuggestion(
                        type=RefactoringType.INTRODUCE_PARAMETER,
                        file=file,
                        start_line=line,
                        end_line=line,
                        message=f"函数 '{name}' 参数过多 ({param_count})",
                        suggestion="考虑使用参数对象或配置字典",
                        impact="medium",
                    ))

                # 检查嵌套深度
                if nested_depth > self.COMPLEXITY_THRESHOLDS['nested_critical']:
                    suggestions.append(RefactoringSuggestion(
                        type=RefactoringType.EXTRACT_METHOD,
                        file=file,
                        start_line=line,
                        end_line=line,
                        message=f"函数 '{name}' 嵌套过深 ({nested_depth} 层)",
                        suggestion="考虑提取内部逻辑为独立函数",
                        impact="high",
                    ))

        except Exception:
            pass

        return suggestions

    def _calculate_cyclomatic_complexity(self, code: str) -> int:
        """计算圈复杂度"""
        if not code:
            return 1

        complexity = 1

        # 计算决策点
        patterns = [
            r'\bif\b',
            r'\belif\b',
            r'\bfor\b',
            r'\bwhile\b',
            r'\band\b',
            r'\bor\b',
            r'\bexcept\b',
            r'\bcase\b',
            r'\?\s*:',  # 三元运算符
        ]

        for pattern in patterns:
            complexity += len(re.findall(pattern, code))

        return complexity

    def _calculate_nested_depth(self, code: str) -> int:
        """计算嵌套深度"""
        if not code:
            return 0

        max_depth = 0
        current_depth = 0

        for line in code.split('\n'):
            # 计算缩进
            stripped = line.lstrip()
            if stripped:
                indent = len(line) - len(stripped)
                depth = indent // 4  # 假设 4 空格缩进
                max_depth = max(max_depth, depth)

        return max_depth

    def _suggest_patterns(self, file: str, full_path: Path) -> List[RefactoringSuggestion]:
        """建议设计模式"""
        suggestions = []

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 检测工厂模式机会
            if re.search(r'if\s+.*type\s*==', content):
                suggestions.append(RefactoringSuggestion(
                    type=RefactoringType.EXTRACT_CLASS,
                    file=file,
                    start_line=0,
                    end_line=0,
                    message="检测到类型判断逻辑",
                    suggestion="考虑使用工厂模式或策略模式",
                    impact="low",
                ))

            # 检测单例模式机会
            if re.search(r'getInstance|get_instance|_instance', content):
                suggestions.append(RefactoringSuggestion(
                    type=RefactoringType.EXTRACT_CLASS,
                    file=file,
                    start_line=0,
                    end_line=0,
                    message="检测到实例获取逻辑",
                    suggestion="考虑使用单例模式装饰器",
                    impact="low",
                ))

        except Exception:
            pass

        return suggestions

    def apply_refactoring(self, suggestion: RefactoringSuggestion) -> Dict[str, Any]:
        """应用重构（自动重构）

        Args:
            suggestion: 重构建议

        Returns:
            应用结果
        """
        result = {
            'success': False,
            'changes': [],
            'message': '',
        }

        if not suggestion.auto_applicable:
            result['message'] = '此重构建议不支持自动应用'
            return result

        # 自动重构逻辑
        if suggestion.type == RefactoringType.RENAME:
            # 重命名
            result['message'] = '请使用 IDE 的重命名功能'
        elif suggestion.type == RefactoringType.EXTRACT_METHOD:
            result['message'] = '请手动提取方法'
        else:
            result['message'] = '请手动应用此重构'

        return result

    def get_refactoring_report(self, file: str = None) -> str:
        """生成重构报告

        Args:
            file: 文件路径（可选）

        Returns:
            Markdown 格式报告
        """
        suggestions = self.analyze(file)

        lines = [
            "# 🔧 重构分析报告",
            "",
            f"**分析时间**: {datetime.now().isoformat()}",
            f"**建议数量**: {len(suggestions)}",
            "",
        ]

        # 按类型分组
        by_type: Dict[str, List[RefactoringSuggestion]] = {}
        for s in suggestions:
            type_name = s.type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(s)

        for type_name, items in by_type.items():
            lines.append(f"## {type_name.replace('_', ' ').title()}")
            lines.append("")

            for item in items[:5]:  # 每类最多 5 个
                lines.append(item.to_markdown())

            if len(items) > 5:
                lines.append(f"*...还有 {len(items) - 5} 个类似建议*")
                lines.append("")

        lines.append("---")
        lines.append("*🔧 由 RefactoringAdvisor 自动生成*")

        return "\n".join(lines)


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: refactoring_advisor.py <project_dir> [file]")
        print("\nCommands:")
        print("  analyze [file]       Analyze and show suggestions")
        print("  report [file]        Generate markdown report")
        sys.exit(1)

    project_dir = sys.argv[1]
    file = sys.argv[2] if len(sys.argv) > 2 else None

    advisor = RefactoringAdvisor(project_dir)

    suggestions = advisor.analyze(file)

    print(f"Found {len(suggestions)} refactoring suggestions:")
    print()

    for s in suggestions[:10]:
        print(f"- [{s.impact}] {s.type.value}: {s.message}")


if __name__ == '__main__':
    main()