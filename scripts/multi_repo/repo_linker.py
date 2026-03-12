#!/usr/bin/env python3
"""
仓库关联分析器
分析仓库间的依赖和关联关系
"""

import os
import json
import re
import subprocess
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class RepoDepNode:
    """依赖图节点"""
    name: str
    repo_type: str = ""
    language: str = ""
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'type': self.repo_type,
            'language': self.language,
            'dependencies': self.dependencies,
            'dependents': self.dependents,
        }


@dataclass
class RepoDepEdge:
    """依赖图边"""
    source: str
    target: str
    dep_type: str  # npm, maven, pip, git, etc.
    version: str = ""
    is_dev: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source': self.source,
            'target': self.target,
            'type': self.dep_type,
            'version': self.version,
            'is_dev': self.is_dev,
        }


@dataclass
class RepoDepGraph:
    """仓库依赖图"""
    nodes: Dict[str, RepoDepNode] = field(default_factory=dict)
    edges: List[RepoDepEdge] = field(default_factory=list)

    def add_node(self, node: RepoDepNode):
        """添加节点"""
        self.nodes[node.name] = node

    def add_edge(self, edge: RepoDepEdge):
        """添加边"""
        self.edges.append(edge)
        # 更新节点的依赖关系
        if edge.source in self.nodes:
            self.nodes[edge.source].dependencies.append(edge.target)
        if edge.target in self.nodes:
            self.nodes[edge.target].dependents.append(edge.source)

    def get_dependencies(self, repo_name: str, depth: int = 1) -> List[str]:
        """获取仓库依赖"""
        if repo_name not in self.nodes:
            return []

        result = set()
        to_visit = [repo_name]
        current_depth = 0

        while to_visit and current_depth < depth:
            next_visit = []
            for name in to_visit:
                if name in self.nodes:
                    for dep in self.nodes[name].dependencies:
                        if dep not in result:
                            result.add(dep)
                            next_visit.append(dep)
            to_visit = next_visit
            current_depth += 1

        return list(result)

    def get_dependents(self, repo_name: str, depth: int = 1) -> List[str]:
        """获取依赖此仓库的其他仓库"""
        if repo_name not in self.nodes:
            return []

        result = set()
        to_visit = [repo_name]
        current_depth = 0

        while to_visit and current_depth < depth:
            next_visit = []
            for name in to_visit:
                if name in self.nodes:
                    for dep in self.nodes[name].dependents:
                        if dep not in result:
                            result.add(dep)
                            next_visit.append(dep)
            to_visit = next_visit
            current_depth += 1

        return list(result)

    def find_circular_deps(self) -> List[List[str]]:
        """检测循环依赖"""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            if node in self.nodes:
                for dep in self.nodes[node].dependencies:
                    if dep not in visited:
                        if dfs(dep):
                            return True
                    elif dep in rec_stack:
                        # 找到循环
                        cycle_start = path.index(dep)
                        cycle = path[cycle_start:] + [dep]
                        cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)
            return False

        for node in self.nodes:
            if node not in visited:
                dfs(node)

        return cycles

    def to_mermaid(self) -> str:
        """生成 Mermaid 图"""
        lines = ['graph TD']

        for name, node in self.nodes.items():
            lines.append(f"    {name}[{name}]")

        for edge in self.edges:
            style = '::' if edge.is_dev else '-->'
            lines.append(f"    {edge.source} {style}|{edge.dep_type}| {edge.target}")

        return '\n'.join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'nodes': {name: node.to_dict() for name, node in self.nodes.items()},
            'edges': [edge.to_dict() for edge in self.edges],
        }


class RepoLinker:
    """仓库关联分析器

    分析仓库间的依赖关系:
    - 包管理依赖 (npm, maven, pip, cargo, go mod)
    - Git 子模块
    - Monorepo 工具配置 (lerna, nx, turborepo)
    - 自定义配置
    """

    def __init__(self, repos: Dict[str, str]):
        """初始化

        Args:
            repos: 仓库名称到路径的映射
        """
        self.repos = repos
        self._dep_graph = RepoDepGraph()

    def analyze_all(self) -> RepoDepGraph:
        """分析所有仓库的依赖关系"""
        # 初始化节点
        for name, path in self.repos.items():
            self._dep_graph.add_node(RepoDepNode(name=name))

        # 分析每个仓库
        for name, path in self.repos.items():
            self._analyze_repo(name, path)

        return self._dep_graph

    def _analyze_repo(self, repo_name: str, repo_path: str):
        """分析单个仓库的依赖"""
        path = Path(repo_path)

        # 分析 package.json
        self._analyze_npm_deps(repo_name, path)

        # 分析 pom.xml
        self._analyze_maven_deps(repo_name, path)

        # 分析 requirements.txt
        self._analyze_pip_deps(repo_name, path)

        # 分析 Cargo.toml
        self._analyze_cargo_deps(repo_name, path)

        # 分析 go.mod
        self._analyze_go_deps(repo_name, path)

        # 分析 Git 子模块
        self._analyze_git_submodules(repo_name, path)

        # 分析 Monorepo 配置
        self._analyze_monorepo_config(repo_name, path)

    def _analyze_npm_deps(self, repo_name: str, repo_path: Path):
        """分析 npm 依赖"""
        pkg_json = repo_path / 'package.json'
        if not pkg_json.exists():
            return

        try:
            with open(pkg_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            all_deps = {}
            all_deps.update(data.get('dependencies', {}))
            all_deps.update(data.get('devDependencies', {}))

            for dep_name, version in all_deps.items():
                # 检查是否是本地仓库
                is_local = self._is_local_repo(dep_name, version)

                if is_local:
                    self._dep_graph.add_edge(RepoDepEdge(
                        source=repo_name,
                        target=dep_name,
                        dep_type='npm',
                        version=version,
                        is_dev=dep_name in data.get('devDependencies', {}),
                    ))
                else:
                    # 外部依赖
                    pass

        except Exception:
            pass

    def _analyze_maven_deps(self, repo_name: str, repo_path: Path):
        """分析 Maven 依赖"""
        pom_xml = repo_path / 'pom.xml'
        if not pom_xml.exists():
            return

        try:
            with open(pom_xml, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简化解析：查找 groupId 和 artifactId
            pattern = r'<dependency>.*?<groupId>(.*?)</groupId>.*?<artifactId>(.*?)</artifactId>.*?</dependency>'
            for match in re.finditer(pattern, content, re.DOTALL):
                group_id = match.group(1)
                artifact_id = match.group(2)

                # 检查是否是本地仓库
                dep_name = artifact_id
                if dep_name in self.repos:
                    self._dep_graph.add_edge(RepoDepEdge(
                        source=repo_name,
                        target=dep_name,
                        dep_type='maven',
                    ))

        except Exception:
            pass

    def _analyze_pip_deps(self, repo_name: str, repo_path: Path):
        """分析 pip 依赖"""
        req_file = repo_path / 'requirements.txt'
        if not req_file.exists():
            return

        try:
            with open(req_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 解析包名
                        pkg_name = re.split(r'[=<>!~]', line)[0].strip()

                        if pkg_name in self.repos:
                            self._dep_graph.add_edge(RepoDepEdge(
                                source=repo_name,
                                target=pkg_name,
                                dep_type='pip',
                            ))

        except Exception:
            pass

    def _analyze_cargo_deps(self, repo_name: str, repo_path: Path):
        """分析 Cargo 依赖"""
        cargo_toml = repo_path / 'Cargo.toml'
        if not cargo_toml.exists():
            return

        try:
            with open(cargo_toml, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简化解析：查找 [dependencies] 部分
            in_deps = False
            for line in content.split('\n'):
                line = line.strip()

                if line == '[dependencies]':
                    in_deps = True
                    continue

                if line.startswith('['):
                    in_deps = False

                if in_deps and '=' in line:
                    pkg_name = line.split('=')[0].strip()

                    if pkg_name in self.repos:
                        self._dep_graph.add_edge(RepoDepEdge(
                            source=repo_name,
                            target=pkg_name,
                            dep_type='cargo',
                        ))

        except Exception:
            pass

    def _analyze_go_deps(self, repo_name: str, repo_path: Path):
        """分析 Go module 依赖"""
        go_mod = repo_path / 'go.mod'
        if not go_mod.exists():
            return

        try:
            with open(go_mod, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析 require 块
            pattern = r'require\s*\((.*?)\)'
            for match in re.finditer(pattern, content, re.DOTALL):
                block = match.group(1)
                for line in block.strip().split('\n'):
                    parts = line.strip().split()
                    if parts:
                        pkg_name = parts[0].split('/')[-1]

                        if pkg_name in self.repos:
                            self._dep_graph.add_edge(RepoDepEdge(
                                source=repo_name,
                                target=pkg_name,
                                dep_type='go',
                            ))

        except Exception:
            pass

    def _analyze_git_submodules(self, repo_name: str, repo_path: Path):
        """分析 Git 子模块"""
        gitmodules = repo_path / '.gitmodules'
        if not gitmodules.exists():
            return

        try:
            with open(gitmodules, 'r', encoding='utf-8') as f:
                content = f.read()

            # 解析子模块
            pattern = r'\[submodule\s+"(.*?)"\].*?path\s*=\s*(.*?)(?:\n|$)'
            for match in re.finditer(pattern, content, re.DOTALL):
                name = match.group(1)
                sub_path = match.group(2).strip()

                if name in self.repos:
                    self._dep_graph.add_edge(RepoDepEdge(
                        source=repo_name,
                        target=name,
                        dep_type='git-submodule',
                    ))

        except Exception:
            pass

    def _analyze_monorepo_config(self, repo_name: str, repo_path: Path):
        """分析 Monorepo 配置"""
        # Lerna
        lerna_json = repo_path / 'lerna.json'
        if lerna_json.exists():
            try:
                with open(lerna_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                packages = data.get('packages', [])
                for pkg in packages:
                    pkg_name = pkg.strip('/*')
                    if pkg_name in self.repos:
                        self._dep_graph.add_edge(RepoDepEdge(
                            source=repo_name,
                            target=pkg_name,
                            dep_type='lerna',
                        ))
            except Exception:
                pass

        # Turborepo
        turbo_json = repo_path / 'turbo.json'
        if turbo_json.exists():
            # 解析 turborepo 配置
            pass

        # Nx
        nx_json = repo_path / 'nx.json'
        if nx_json.exists():
            # 解析 nx 配置
            pass

    def _is_local_repo(self, dep_name: str, version: str) -> bool:
        """检查是否是本地仓库依赖"""
        # 检查是否在已知仓库列表中
        if dep_name in self.repos:
            return True

        # 检查版本是否是本地路径
        if version.startswith('file:') or version.startswith('link:'):
            return True

        # 检查是否是 workspace 协议
        if version.startswith('workspace:'):
            return True

        return False

    def get_dep_graph(self) -> RepoDepGraph:
        """获取依赖图"""
        return self._dep_graph

    def find_impact(self, repo_name: str) -> Dict[str, List[str]]:
        """分析仓库变更的影响范围

        Args:
            repo_name: 变更的仓库名称

        Returns:
            影响范围
        """
        return {
            'direct_dependents': self._dep_graph.get_dependents(repo_name, depth=1),
            'transitive_dependents': self._dep_graph.get_dependents(repo_name, depth=3),
            'dependencies': self._dep_graph.get_dependencies(repo_name),
        }

    def suggest_build_order(self) -> List[List[str]]:
        """建议构建顺序（拓扑排序）

        Returns:
            构建层级列表
        """
        # 计算入度
        in_degree = defaultdict(int)
        for name in self._dep_graph.nodes:
            in_degree[name] = 0

        for edge in self._dep_graph.edges:
            in_degree[edge.target] += 1

        # 拓扑排序
        result = []
        remaining = set(self._dep_graph.nodes.keys())

        while remaining:
            # 找到入度为 0 的节点
            level = [name for name in remaining if in_degree[name] == 0]

            if not level:
                # 存在循环依赖
                break

            result.append(level)

            # 移除这些节点并更新入度
            for name in level:
                remaining.remove(name)
                if name in self._dep_graph.nodes:
                    for dep in self._dep_graph.nodes[name].dependencies:
                        in_degree[dep] -= 1

        return result


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: repo_linker.py <config_file>")
        print("\nConfig file format (JSON):")
        print('{"repos": {"name": "path", ...}}')
        sys.exit(1)

    config_file = sys.argv[1]

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    repos = config.get('repos', {})
    linker = RepoLinker(repos)
    graph = linker.analyze_all()

    print("=== Dependency Graph ===")
    print(graph.to_mermaid())

    print("\n=== Build Order ===")
    order = linker.suggest_build_order()
    for i, level in enumerate(order):
        print(f"Level {i + 1}: {', '.join(level)}")

    print("\n=== Circular Dependencies ===")
    cycles = graph.find_circular_deps()
    if cycles:
        for cycle in cycles:
            print(" -> ".join(cycle))
    else:
        print("No circular dependencies found")


if __name__ == '__main__':
    main()