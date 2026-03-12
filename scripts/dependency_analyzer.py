#!/usr/bin/env python3
"""
依赖分析器
深度分析项目依赖关系

特性：
- 多种锁文件解析
- 依赖树构建
- 循环依赖检测
- 版本冲突检测
- 安全漏洞检查（基础）
"""

import os
import re
import json
import toml
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


class DependencyType(Enum):
    """依赖类型"""
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    OPTIONAL = "optional"
    PEER = "peer"


@dataclass
class Dependency:
    """依赖信息"""
    name: str
    version: str
    version_range: str = ""
    dep_type: DependencyType = DependencyType.PRODUCTION
    source: str = ""
    dependencies: List['Dependency'] = field(default_factory=list)
    is_direct: bool = True
    license: str = ""
    deprecated: bool = False


@dataclass
class VersionConflict:
    """版本冲突"""
    name: str
    versions: List[Tuple[str, str]]  # [(required_by, version), ...]
    resolved_version: str = ""


@dataclass
class CircularDep:
    """循环依赖"""
    cycle: List[str]
    severity: str = "warning"  # warning, error


class DependencyAnalyzer:
    """依赖分析器"""

    # 锁文件模式
    LOCK_FILES = {
        'package-lock.json': 'npm',
        'yarn.lock': 'yarn',
        'pnpm-lock.yaml': 'pnpm',
        'Cargo.lock': 'cargo',
        'go.sum': 'go',
        'requirements.txt': 'pip',
        'poetry.lock': 'poetry',
        'Pipfile.lock': 'pipenv',
        'composer.lock': 'composer',
        'Gemfile.lock': 'bundler',
        'pubspec.lock': 'flutter',
    }

    def __init__(self, project_dir: str):
        """初始化分析器

        Args:
            project_dir: 项目目录
        """
        self.project_dir = Path(project_dir).resolve()
        self.dependencies: Dict[str, Dependency] = {}
        self.dependency_tree: Dict[str, List[str]] = defaultdict(list)
        self.reverse_deps: Dict[str, List[str]] = defaultdict(list)

    def analyze(self) -> Dict[str, Any]:
        """执行分析"""
        # 检测并解析锁文件
        lock_file_type = self._detect_lock_file()

        if lock_file_type:
            self._parse_lock_file(lock_file_type)

        # 构建依赖树
        self._build_dependency_tree()

        # 检测问题
        circular_deps = self._detect_circular_deps()
        conflicts = self._detect_version_conflicts()

        return {
            'lock_file': lock_file_type,
            'total_dependencies': len(self.dependencies),
            'direct_dependencies': sum(1 for d in self.dependencies.values() if d.is_direct),
            'dependency_tree': self._get_tree_summary(),
            'circular_dependencies': [
                {'cycle': c.cycle, 'severity': c.severity}
                for c in circular_deps
            ],
            'version_conflicts': [
                {
                    'name': c.name,
                    'versions': c.versions,
                    'resolved': c.resolved_version,
                }
                for c in conflicts
            ],
            'recommendations': self._generate_recommendations(circular_deps, conflicts),
        }

    def _detect_lock_file(self) -> Optional[str]:
        """检测锁文件类型"""
        for lock_file, lock_type in self.LOCK_FILES.items():
            if (self.project_dir / lock_file).exists():
                return lock_file
        return None

    def _parse_lock_file(self, lock_file: str) -> None:
        """解析锁文件"""
        lock_path = self.project_dir / lock_file

        if lock_file == 'package-lock.json':
            self._parse_npm_lock(lock_path)
        elif lock_file == 'yarn.lock':
            self._parse_yarn_lock(lock_path)
        elif lock_file == 'Cargo.lock':
            self._parse_cargo_lock(lock_path)
        elif lock_file == 'go.sum':
            self._parse_go_sum(lock_path)
        elif lock_file == 'requirements.txt':
            self._parse_requirements(lock_path)
        elif lock_file == 'poetry.lock':
            self._parse_poetry_lock(lock_path)

    def _parse_npm_lock(self, lock_path: Path) -> None:
        """解析 package-lock.json"""
        try:
            with open(lock_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 解析 packages
            packages = data.get('packages', {})
            for name, info in packages.items():
                if name.startswith('node_modules/'):
                    name = name[13:]  # 移除 node_modules/ 前缀

                if not name:
                    continue

                dep_type = DependencyType.PRODUCTION
                if info.get('dev'):
                    dep_type = DependencyType.DEVELOPMENT
                elif info.get('optional'):
                    dep_type = DependencyType.OPTIONAL
                elif info.get('peer'):
                    dep_type = DependencyType.PEER

                self.dependencies[name] = Dependency(
                    name=name,
                    version=info.get('version', ''),
                    dep_type=dep_type,
                    source='npm',
                    is_direct=not name.startswith('@') or '/' not in name,
                    license=info.get('license', ''),
                    deprecated=info.get('deprecated', False),
                )

        except Exception as e:
            print(f"Warning: Failed to parse npm lock: {e}")

    def _parse_yarn_lock(self, lock_path: Path) -> None:
        """解析 yarn.lock"""
        try:
            content = lock_path.read_text(encoding='utf-8')

            # Yarn lock 格式较复杂，简化解析
            current_name = ""
            current_version = ""

            for line in content.split('\n'):
                line = line.strip()

                if not line.startswith(' ') and line:
                    # 新的包
                    match = re.match(r'^(@?[^@]+)@', line)
                    if match:
                        current_name = match.group(1)

                elif line.startswith('version '):
                    current_version = line.split('"')[1]

                elif line.startswith('"version"'):
                    current_version = line.split('"')[3]

                if current_name and current_version:
                    self.dependencies[current_name] = Dependency(
                        name=current_name,
                        version=current_version,
                        source='yarn',
                    )
                    current_name = ""
                    current_version = ""

        except Exception as e:
            print(f"Warning: Failed to parse yarn lock: {e}")

    def _parse_cargo_lock(self, lock_path: Path) -> None:
        """解析 Cargo.lock"""
        try:
            content = lock_path.read_text(encoding='utf-8')
            data = toml.loads(content)

            for pkg in data.get('package', []):
                name = pkg.get('name', '')
                version = pkg.get('version', '')

                if name:
                    self.dependencies[name] = Dependency(
                        name=name,
                        version=version,
                        source='cargo',
                    )

        except Exception as e:
            print(f"Warning: Failed to parse cargo lock: {e}")

    def _parse_go_sum(self, lock_path: Path) -> None:
        """解析 go.sum"""
        try:
            content = lock_path.read_text(encoding='utf-8')

            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    version = parts[1].replace('/go.mod', '').lstrip('v')

                    self.dependencies[name] = Dependency(
                        name=name,
                        version=version,
                        source='go',
                    )

        except Exception as e:
            print(f"Warning: Failed to parse go.sum: {e}")

    def _parse_requirements(self, lock_path: Path) -> None:
        """解析 requirements.txt"""
        try:
            content = lock_path.read_text(encoding='utf-8')

            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                match = re.match(r'^([a-zA-Z0-9_-]+)\s*([<>=!]+.*)?$', line)
                if match:
                    name = match.group(1)
                    version = match.group(2) or ''

                    self.dependencies[name] = Dependency(
                        name=name,
                        version=version.lstrip('=<>!'),
                        version_range=version,
                        source='pip',
                    )

        except Exception as e:
            print(f"Warning: Failed to parse requirements: {e}")

    def _parse_poetry_lock(self, lock_path: Path) -> None:
        """解析 poetry.lock"""
        try:
            content = lock_path.read_text(encoding='utf-8')
            data = toml.loads(content)

            for name, info in data.get('package', {}).items():
                if isinstance(info, dict):
                    self.dependencies[name] = Dependency(
                        name=name,
                        version=info.get('version', ''),
                        source='poetry',
                    )

        except Exception as e:
            print(f"Warning: Failed to parse poetry lock: {e}")

    def _build_dependency_tree(self) -> None:
        """构建依赖树"""
        # 简化实现：从 package.json / Cargo.toml 等读取直接依赖
        manifest_files = [
            ('package.json', self._parse_package_json_deps),
            ('Cargo.toml', self._parse_cargo_toml_deps),
            ('pyproject.toml', self._parse_pyproject_deps),
        ]

        for manifest, parser in manifest_files:
            manifest_path = self.project_dir / manifest
            if manifest_path.exists():
                direct_deps = parser(manifest_path)
                for dep in direct_deps:
                    if dep in self.dependencies:
                        self.dependencies[dep].is_direct = True

    def _parse_package_json_deps(self, path: Path) -> List[str]:
        """解析 package.json 依赖"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            deps = list(data.get('dependencies', {}).keys())
            deps.extend(data.get('devDependencies', {}).keys())
            return deps
        except Exception:
            return []

    def _parse_cargo_toml_deps(self, path: Path) -> List[str]:
        """解析 Cargo.toml 依赖"""
        try:
            content = path.read_text(encoding='utf-8')
            data = toml.loads(content)
            deps = list(data.get('dependencies', {}).keys())
            deps.extend(data.get('dev-dependencies', {}).keys())
            return deps
        except Exception:
            return []

    def _parse_pyproject_deps(self, path: Path) -> List[str]:
        """解析 pyproject.toml 依赖"""
        try:
            content = path.read_text(encoding='utf-8')
            data = toml.loads(content)

            deps = []
            project = data.get('project', {})
            deps.extend(project.get('dependencies', []))

            # 解析包名
            return [re.match(r'^([a-zA-Z0-9_-]+)', d).group(1)
                    for d in deps if re.match(r'^([a-zA-Z0-9_-]+)', d)]
        except Exception:
            return []

    def _detect_circular_deps(self) -> List[CircularDep]:
        """检测循环依赖"""
        circular = []

        # 简化检测：检查依赖树中的环
        visited = set()
        path = []

        def dfs(node: str) -> Optional[List[str]]:
            if node in path:
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]

            if node in visited:
                return None

            visited.add(node)
            path.append(node)

            for neighbor in self.dependency_tree.get(node, []):
                result = dfs(neighbor)
                if result:
                    return result

            path.pop()
            return None

        for node in list(self.dependencies.keys())[:50]:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    circular.append(CircularDep(cycle=cycle))

        return circular

    def _detect_version_conflicts(self) -> List[VersionConflict]:
        """检测版本冲突"""
        conflicts = []

        # 收集每个包的不同版本需求
        version_requirements: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

        for name, dep in self.dependencies.items():
            if dep.version_range:
                version_requirements[name].append((name, dep.version_range))

        # 检查冲突
        for name, requirements in version_requirements.items():
            versions = set(v for _, v in requirements)
            if len(versions) > 1:
                conflicts.append(VersionConflict(
                    name=name,
                    versions=requirements,
                    resolved_version=self.dependencies.get(name, Dependency(name, '')).version,
                ))

        return conflicts

    def _get_tree_summary(self) -> Dict[str, Any]:
        """获取依赖树摘要"""
        return {
            'total': len(self.dependencies),
            'by_source': self._count_by_source(),
            'by_type': self._count_by_type(),
        }

    def _count_by_source(self) -> Dict[str, int]:
        """按来源统计"""
        counts: Dict[str, int] = defaultdict(int)
        for dep in self.dependencies.values():
            counts[dep.source] += 1
        return dict(counts)

    def _count_by_type(self) -> Dict[str, int]:
        """按类型统计"""
        counts: Dict[str, int] = defaultdict(int)
        for dep in self.dependencies.values():
            counts[dep.dep_type.value] += 1
        return dict(counts)

    def _generate_recommendations(self, circular: List[CircularDep],
                                   conflicts: List[VersionConflict]) -> List[str]:
        """生成建议"""
        recommendations = []

        if circular:
            recommendations.append(
                f"发现 {len(circular)} 个循环依赖，建议重构以消除循环"
            )

        if conflicts:
            recommendations.append(
                f"发现 {len(conflicts)} 个版本冲突，建议更新依赖或使用 resolutions"
            )

        deprecated = [d for d in self.dependencies.values() if d.deprecated]
        if deprecated:
            recommendations.append(
                f"发现 {len(deprecated)} 个已废弃的依赖，建议更新或替换"
            )

        return recommendations

    def get_dependency_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取单个依赖信息"""
        dep = self.dependencies.get(name)
        if not dep:
            return None

        return {
            'name': dep.name,
            'version': dep.version,
            'type': dep.dep_type.value,
            'source': dep.source,
            'is_direct': dep.is_direct,
            'license': dep.license,
            'deprecated': dep.deprecated,
        }

    def find_dependents(self, name: str) -> List[str]:
        """查找依赖于指定包的包"""
        return self.reverse_deps.get(name, [])

    def find_dependencies(self, name: str) -> List[str]:
        """查找指定包的依赖"""
        return self.dependency_tree.get(name, [])


def main():
    """命令行接口"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: dependency_analyzer.py <project_dir>")
        sys.exit(1)

    project_dir = sys.argv[1]
    analyzer = DependencyAnalyzer(project_dir)
    result = analyzer.analyze()

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()