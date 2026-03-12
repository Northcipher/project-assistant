#!/usr/bin/env python3
"""
代码质量预测器
预测代码风险

特性:
- 复杂度分析
- 测试覆盖率检查
- 变更频率分析
- 作者经验分析
- 风险评分
"""

import os
import re
import json
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskFactor:
    """风险因素"""
    name: str
    value: float
    weight: float
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'weight': self.weight,
            'description': self.description,
        }


@dataclass
class RiskAssessment:
    """风险评估"""
    file: str
    score: float  # 0-100
    level: RiskLevel
    factors: List[RiskFactor] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file': self.file,
            'score': self.score,
            'level': self.level.value,
            'factors': [f.to_dict() for f in self.factors],
            'recommendations': self.recommendations,
            'details': self.details,
        }

    def to_markdown(self) -> str:
        """转换为 Markdown"""
        level_icons = {
            RiskLevel.LOW: '✅',
            RiskLevel.MEDIUM: '⚠️',
            RiskLevel.HIGH: '🔶',
            RiskLevel.CRITICAL: '🔴',
        }
        icon = level_icons.get(self.level, '❓')

        lines = [
            f"## {icon} {self.file}",
            f"**风险评分**: {self.score:.1f}/100",
            f"**风险等级**: {self.level.value}",
            "",
            "### 风险因素",
            "",
        ]

        for factor in self.factors:
            lines.append(f"- **{factor.name}**: {factor.value:.2f} (权重: {factor.weight})")
            if factor.description:
                lines.append(f"  {factor.description}")

        if self.recommendations:
            lines.append("")
            lines.append("### 建议")
            for r in self.recommendations:
                lines.append(f"- {r}")

        return "\n".join(lines)


@dataclass
class QualityScore:
    """代码质量分数"""
    file: str
    overall_score: float
    maintainability: float
    reliability: float
    security: float
    testability: float
    issues: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file': self.file,
            'overall_score': self.overall_score,
            'maintainability': self.maintainability,
            'reliability': self.reliability,
            'security': self.security,
            'testability': self.testability,
            'issues': self.issues,
        }


class QualityPredictor:
    """代码质量预测器

    风险因素:
    - 复杂度 (权重 0.3)
    - 测试覆盖率 (权重 0.25)
    - 变更频率 (权重 0.2)
    - 作者经验 (权重 0.15)
    - 代码行数 (权重 0.1)
    """

    # 风险权重
    WEIGHTS = {
        'complexity': 0.30,
        'test_coverage': 0.25,
        'change_frequency': 0.20,
        'author_experience': 0.15,
        'code_size': 0.10,
    }

    def __init__(self, project_dir: str):
        """初始化

        Args:
            project_dir: 项目目录
        """
        self.project_dir = Path(project_dir).resolve()
        self._git_available = self._check_git()

    def _check_git(self) -> bool:
        """检查 Git 是否可用"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def predict_risk(self, file: str) -> RiskAssessment:
        """预测代码风险

        Args:
            file: 文件路径

        Returns:
            风险评估结果
        """
        factors = []

        # 1. 复杂度
        complexity_score = self._calc_complexity(file)
        factors.append(RiskFactor(
            name='complexity',
            value=complexity_score,
            weight=self.WEIGHTS['complexity'],
            description=f"圈复杂度评分: {complexity_score:.2f}",
        ))

        # 2. 测试覆盖率
        coverage_score = self._get_coverage(file)
        factors.append(RiskFactor(
            name='test_coverage',
            value=1 - coverage_score,  # 转换为风险分数
            weight=self.WEIGHTS['test_coverage'],
            description=f"测试覆盖率: {coverage_score * 100:.1f}%",
        ))

        # 3. 变更频率
        change_freq = self._get_change_freq(file)
        factors.append(RiskFactor(
            name='change_frequency',
            value=change_freq,
            weight=self.WEIGHTS['change_frequency'],
            description=f"变更频率评分: {change_freq:.2f}",
        ))

        # 4. 作者经验
        author_exp = self._get_author_exp(file)
        factors.append(RiskFactor(
            name='author_experience',
            value=1 - author_exp,  # 经验越高，风险越低
            weight=self.WEIGHTS['author_experience'],
            description=f"作者经验评分: {author_exp:.2f}",
        ))

        # 5. 代码行数
        size_score = self._get_code_size_score(file)
        factors.append(RiskFactor(
            name='code_size',
            value=size_score,
            weight=self.WEIGHTS['code_size'],
            description=f"代码行数评分: {size_score:.2f}",
        ))

        # 计算总分
        total_score = sum(f.value * f.weight for f in factors)
        total_score = min(1.0, max(0.0, total_score))

        # 确定风险等级
        if total_score < 0.25:
            level = RiskLevel.LOW
        elif total_score < 0.5:
            level = RiskLevel.MEDIUM
        elif total_score < 0.75:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.CRITICAL

        # 生成建议
        recommendations = self._get_recommendations(factors)

        return RiskAssessment(
            file=file,
            score=total_score * 100,
            level=level,
            factors=factors,
            recommendations=recommendations,
        )

    def analyze_quality(self, file: str) -> QualityScore:
        """分析代码质量

        Args:
            file: 文件路径

        Returns:
            质量分数
        """
        issues = []

        # 可维护性
        maintainability = self._assess_maintainability(file, issues)

        # 可靠性
        reliability = self._assess_reliability(file, issues)

        # 安全性
        security = self._assess_security(file, issues)

        # 可测试性
        testability = self._assess_testability(file, issues)

        # 综合评分
        overall = (maintainability + reliability + security + testability) / 4

        return QualityScore(
            file=file,
            overall_score=overall,
            maintainability=maintainability,
            reliability=reliability,
            security=security,
            testability=testability,
            issues=issues[:20],  # 限制问题数量
        )

    def _calc_complexity(self, file: str) -> float:
        """计算复杂度分数"""
        full_path = self.project_dir / file
        if not full_path.exists():
            return 0.5

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 计算圈复杂度
            complexity = 1
            patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\band\b', r'\bor\b']
            for pattern in patterns:
                complexity += len(re.findall(pattern, content))

            # 转换为 0-1 分数
            # 复杂度 > 30 为高风险
            return min(1.0, complexity / 30)

        except Exception:
            return 0.5

    def _get_coverage(self, file: str) -> float:
        """获取测试覆盖率"""
        # 尝试读取覆盖率报告
        coverage_file = self.project_dir / 'coverage.json'
        if coverage_file.exists():
            try:
                with open(coverage_file, 'r') as f:
                    data = json.load(f)
                return data.get('files', {}).get(file, {}).get('summary', {}).get('percent_covered', 0) / 100
            except Exception:
                pass

        # 检查是否有对应的测试文件
        test_patterns = [
            f'test_{file}',
            f'{file.replace(".py", "_test.py")}',
            f'tests/{file}',
        ]

        for pattern in test_patterns:
            if (self.project_dir / pattern).exists():
                return 0.5  # 有测试文件，假设 50% 覆盖

        return 0.0  # 无测试

    def _get_change_freq(self, file: str) -> float:
        """获取变更频率"""
        if not self._git_available:
            return 0.5

        try:
            # 获取最近 30 天的变更次数
            result = subprocess.run(
                ['git', 'log', '--oneline', '--since', '30 days ago', '--', file],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                changes = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                # 变更 > 10 次为高风险
                return min(1.0, changes / 10)

        except Exception:
            pass

        return 0.5

    def _get_author_exp(self, file: str) -> float:
        """获取作者经验"""
        if not self._git_available:
            return 0.5

        try:
            # 获取作者提交次数
            result = subprocess.run(
                ['git', 'shortlog', '-sne', '--', file],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    # 统计总提交数
                    total_commits = 0
                    for line in lines:
                        match = re.match(r'\s*(\d+)', line)
                        if match:
                            total_commits += int(match.group(1))

                    # 提交 > 20 次为高经验
                    return min(1.0, total_commits / 20)

        except Exception:
            pass

        return 0.5

    def _get_code_size_score(self, file: str) -> float:
        """获取代码大小分数"""
        full_path = self.project_dir / file
        if not full_path.exists():
            return 0.5

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = sum(1 for _ in f)

            # 行数 > 500 为高风险
            return min(1.0, lines / 500)

        except Exception:
            return 0.5

    def _assess_maintainability(self, file: str, issues: List) -> float:
        """评估可维护性"""
        score = 100.0

        full_path = self.project_dir / file
        if not full_path.exists():
            return 50.0

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 检查函数长度
            func_pattern = r'def\s+\w+\([^)]*\):[^}]*?(?=\ndef|\nclass|\Z)'
            for match in re.finditer(func_pattern, content, re.DOTALL):
                func_lines = match.group(0).count('\n')
                if func_lines > 50:
                    score -= 10
                    issues.append({
                        'type': 'maintainability',
                        'message': f'函数过长 ({func_lines} 行)',
                        'severity': 'warning',
                    })

            # 检查注释比例
            comment_lines = len(re.findall(r'#.*|""".*?"""|\'\'\'.*?\'\'\'', content, re.DOTALL))
            total_lines = content.count('\n')
            if total_lines > 0 and comment_lines / total_lines < 0.1:
                score -= 5
                issues.append({
                    'type': 'maintainability',
                    'message': '注释比例过低',
                    'severity': 'info',
                })

        except Exception:
            pass

        return max(0, score)

    def _assess_reliability(self, file: str, issues: List) -> float:
        """评估可靠性"""
        score = 100.0

        full_path = self.project_dir / file
        if not full_path.exists():
            return 50.0

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 检查异常处理
            try_blocks = len(re.findall(r'\btry\s*:', content))
            raise_statements = len(re.findall(r'\braise\s+', content))

            # 有 raise 但没有 try
            if raise_statements > 0 and try_blocks == 0:
                score -= 10
                issues.append({
                    'type': 'reliability',
                    'message': '缺少异常处理',
                    'severity': 'warning',
                })

        except Exception:
            pass

        return max(0, score)

    def _assess_security(self, file: str, issues: List) -> float:
        """评估安全性"""
        score = 100.0

        full_path = self.project_dir / file
        if not full_path.exists():
            return 50.0

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 检查危险函数
            dangerous_funcs = ['eval', 'exec', 'compile', '__import__']
            for func in dangerous_funcs:
                if re.search(rf'\b{func}\s*\(', content):
                    score -= 15
                    issues.append({
                        'type': 'security',
                        'message': f'使用了危险函数 {func}()',
                        'severity': 'error',
                    })

            # 检查 SQL 注入风险
            if re.search(r'execute\s*\([^)]*\+', content):
                score -= 20
                issues.append({
                    'type': 'security',
                    'message': '潜在的 SQL 注入风险',
                    'severity': 'error',
                })

        except Exception:
            pass

        return max(0, score)

    def _assess_testability(self, file: str, issues: List) -> float:
        """评估可测试性"""
        score = 100.0

        full_path = self.project_dir / file
        if not full_path.exists():
            return 50.0

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # 检查全局变量
            global_vars = len(re.findall(r'^\s*\w+\s*=', content, re.MULTILINE))
            if global_vars > 5:
                score -= 10
                issues.append({
                    'type': 'testability',
                    'message': f'全局变量过多 ({global_vars})',
                    'severity': 'info',
                })

        except Exception:
            pass

        return max(0, score)

    def _get_recommendations(self, factors: List[RiskFactor]) -> List[str]:
        """生成建议"""
        recommendations = []

        for factor in factors:
            if factor.value > 0.7:
                if factor.name == 'complexity':
                    recommendations.append('降低代码复杂度，考虑拆分大函数')
                elif factor.name == 'test_coverage':
                    recommendations.append('添加单元测试，提高测试覆盖率')
                elif factor.name == 'change_frequency':
                    recommendations.append('稳定接口，减少频繁变更')
                elif factor.name == 'author_experience':
                    recommendations.append('安排代码审查，由经验丰富的开发者指导')
                elif factor.name == 'code_size':
                    recommendations.append('拆分大文件，提高模块化程度')

        return recommendations

    def get_project_risk_summary(self) -> Dict[str, Any]:
        """获取项目风险摘要"""
        code_extensions = {'.py', '.js', '.ts', '.java', '.go'}
        assessments = []

        for file_path in self.project_dir.rglob('*'):
            if file_path.suffix.lower() in code_extensions:
                if '.git' in str(file_path) or 'node_modules' in str(file_path):
                    continue

                rel_path = str(file_path.relative_to(self.project_dir))
                assessment = self.predict_risk(rel_path)
                assessments.append(assessment)

        # 统计
        risk_counts = defaultdict(int)
        for a in assessments:
            risk_counts[a.level.value] += 1

        high_risk_files = [a for a in assessments if a.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]

        return {
            'total_files': len(assessments),
            'risk_distribution': dict(risk_counts),
            'high_risk_files': len(high_risk_files),
            'average_score': sum(a.score for a in assessments) / len(assessments) if assessments else 0,
            'recommendations': self._get_project_recommendations(assessments),
        }

    def _get_project_recommendations(self, assessments: List[RiskAssessment]) -> List[str]:
        """生成项目级建议"""
        recommendations = []

        high_risk = [a for a in assessments if a.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]
        if len(high_risk) > len(assessments) * 0.2:
            recommendations.append('超过 20% 的文件为高风险，建议进行系统性重构')

        low_coverage = [a for a in assessments
                        if any(f.name == 'test_coverage' and f.value > 0.8 for f in a.factors)]
        if len(low_coverage) > len(assessments) * 0.5:
            recommendations.append('超过 50% 的文件测试覆盖率不足，建议优先添加测试')

        return recommendations


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: quality_predictor.py <project_dir> [file]")
        print("\nCommands:")
        print("  risk [file]         Predict risk for file or project")
        print("  quality [file]      Analyze code quality")
        print("  summary             Get project risk summary")
        sys.exit(1)

    project_dir = sys.argv[1]
    file = sys.argv[2] if len(sys.argv) > 2 else None

    predictor = QualityPredictor(project_dir)

    if file:
        assessment = predictor.predict_risk(file)
        print(assessment.to_markdown())
    else:
        summary = predictor.get_project_risk_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()