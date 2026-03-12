#!/usr/bin/env python3
"""
多仓库管理器
支持 monorepo 和多仓库项目的分析

特性:
- 多仓库统一管理
- 跨仓库搜索
- 仓库依赖图
- 自动检测关联仓库
"""

import os
import json
import yaml
import subprocess
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RepoType(Enum):
    """仓库类型"""
    FRONTEND = "frontend"
    BACKEND = "backend"
    LIBRARY = "library"
    SERVICE = "service"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


@dataclass
class RepoInfo:
    """仓库信息"""
    name: str
    path: str
    type: RepoType = RepoType.UNKNOWN
    language: str = ""
    framework: str = ""
    build_system: str = ""
    dependencies: List[str] = field(default_factory=list)
    last_sync: str = ""
    file_count: int = 0
    line_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'path': self.path,
            'type': self.type.value,
            'language': self.language,
            'framework': self.framework,
            'build_system': self.build_system,
            'dependencies': self.dependencies,
            'last_sync': self.last_sync,
            'file_count': self.file_count,
            'line_count': self.line_count,
        }


@dataclass
class CrossRepoResult:
    """跨仓库搜索结果"""
    repo_name: str
    file_path: str
    match_type: str  # file, function, class, etc.
    name: str
    line: int = 0
    score: float = 0.0
    snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'repo': self.repo_name,
            'path': self.file_path,
            'type': self.match_type,
            'name': self.name,
            'line': self.line,
            'score': self.score,
            'snippet': self.snippet,
        }


class MonoRepoManager:
    """多仓库管理器

    设计原则:
    - 单命令管理多个关联仓库
    - 跨仓库搜索和依赖分析
    - 自动检测仓库关联关系
    """

    # 项目类型检测规则
    TYPE_PATTERNS = {
        RepoType.FRONTEND: {
            'files': ['package.json', 'tsconfig.json', 'webpack.config.js', 'vite.config.ts'],
            'dirs': ['src/components', 'src/pages', 'public'],
            'keywords': ['react', 'vue', 'angular', 'svelte'],
        },
        RepoType.BACKEND: {
            'files': ['pom.xml', 'build.gradle', 'go.mod', 'requirements.txt'],
            'dirs': ['src/main', 'api', 'controllers', 'services'],
            'keywords': ['spring', 'express', 'django', 'flask', 'fastapi'],
        },
        RepoType.LIBRARY: {
            'files': ['Cargo.toml', 'setup.py', 'pyproject.toml'],
            'dirs': ['lib', 'src/lib'],
            'keywords': [],
        },
        RepoType.SERVICE: {
            'files': ['Dockerfile', 'docker-compose.yml', 'k8s/', '.kubernetes/'],
            'dirs': ['proto', 'protobuf', 'grpc'],
            'keywords': ['grpc', 'protobuf', 'microservice'],
        },
        RepoType.MOBILE: {
            'files': ['pubspec.yaml', 'build.gradle', 'AndroidManifest.xml', 'Info.plist'],
            'dirs': ['lib/', 'android/', 'ios/'],
            'keywords': ['flutter', 'react-native', 'kotlin', 'swift'],
        },
    }

    def __init__(self, main_project_dir: str, config_path: str = None):
        """初始化多仓库管理器

        Args:
            main_project_dir: 主项目目录
            config_path: 配置文件路径
        """
        self.main_project_dir = Path(main_project_dir).resolve()
        self._config_path = Path(config_path) if config_path else None
        self._meta_dir = self.main_project_dir / '.projmeta'
        self._repos: Dict[str, RepoInfo] = {}
        self._links: List[Dict] = []

        # 加载配置
        self._load_config()

    def add_repo(self, name: str, path: str, repo_type: str = None) -> RepoInfo:
        """添加仓库

        Args:
            name: 仓库名称
            path: 仓库路径
            repo_type: 仓库类型（可选，自动检测）

        Returns:
            RepoInfo: 仓库信息
        """
        repo_path = Path(path)
        if not repo_path.exists():
            raise ValueError(f"Repository path not found: {path}")

        # 自动检测类型
        if not repo_type:
            repo_type = self._detect_repo_type(repo_path)

        # 获取详细信息
        info = self._analyze_repo(repo_path)
        info.name = name
        info.type = RepoType(repo_type) if repo_type else RepoType.UNKNOWN

        self._repos[name] = info
        self._save_config()

        return info

    def remove_repo(self, name: str) -> bool:
        """移除仓库"""
        if name in self._repos:
            del self._repos[name]
            self._links = [l for l in self._links
                          if l.get('from') != name and l.get('to') != name]
            self._save_config()
            return True
        return False

    def get_repo(self, name: str) -> Optional[RepoInfo]:
        """获取仓库信息"""
        return self._repos.get(name)

    def list_repos(self) -> List[RepoInfo]:
        """列出所有仓库"""
        return list(self._repos.values())

    def detect_repos(self, scan_depth: int = 2) -> List[RepoInfo]:
        """自动检测关联仓库

        Args:
            scan_depth: 扫描深度

        Returns:
            检测到的仓库列表
        """
        detected = []
        parent_dir = self.main_project_dir.parent

        for _ in range(scan_depth):
            for item in parent_dir.iterdir():
                if item.is_dir() and item != self.main_project_dir:
                    # 检查是否是 Git 仓库
                    if (item / '.git').exists():
                        name = item.name
                        if name not in self._repos:
                            try:
                                info = self._analyze_repo(item)
                                info.name = name
                                detected.append(info)
                            except Exception:
                                continue

        return detected

    def cross_repo_search(self, query: str, repos: List[str] = None,
                          max_results: int = 50) -> List[CrossRepoResult]:
        """跨仓库搜索

        Args:
            query: 搜索查询
            repos: 指定仓库列表（可选）
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        results = []
        target_repos = repos if repos else list(self._repos.keys())

        for repo_name in target_repos:
            if repo_name not in self._repos:
                continue

            repo = self._repos[repo_name]
            repo_results = self._search_in_repo(repo, query)
            results.extend(repo_results)

        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:max_results]

    def _search_in_repo(self, repo: RepoInfo, query: str) -> List[CrossRepoResult]:
        """在单个仓库中搜索"""
        results = []
        repo_path = Path(repo.path)

        if not repo_path.exists():
            return results

        query_lower = query.lower()

        try:
            # 使用 LazyIndexer 搜索
            from indexer.lazy_indexer import LazyIndexer
            indexer = LazyIndexer(str(repo_path))

            # 先确保 L0 索引存在
            indexer.build_l0_index()

            # 搜索文件名
            l0 = indexer.get_l0_index()
            for f in l0.files:
                if query_lower in f['path'].lower():
                    results.append(CrossRepoResult(
                        repo_name=repo.name,
                        file_path=f['path'],
                        match_type='file',
                        name=f['path'].split('/')[-1],
                        score=0.8,
                    ))

            # 搜索函数和类
            l1 = indexer.get_l1_index()
            for file_path, funcs in l1.functions.items():
                for func in funcs:
                    if query_lower in func.get('name', '').lower():
                        results.append(CrossRepoResult(
                            repo_name=repo.name,
                            file_path=file_path,
                            match_type='function',
                            name=func.get('name'),
                            line=func.get('line', 0),
                            score=0.9,
                        ))

            for file_path, classes in l1.classes.items():
                for cls in classes:
                    if query_lower in cls.get('name', '').lower():
                        results.append(CrossRepoResult(
                            repo_name=repo.name,
                            file_path=file_path,
                            match_type='class',
                            name=cls.get('name'),
                            line=cls.get('line', 0),
                            score=0.95,
                        ))

        except Exception:
            # 回退到简单文件搜索
            for root, dirs, files in os.walk(repo_path):
                # 排除目录
                dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', 'venv', '__pycache__'}]

                for f in files:
                    if query_lower in f.lower():
                        rel_path = str(Path(root, f).relative_to(repo_path))
                        results.append(CrossRepoResult(
                            repo_name=repo.name,
                            file_path=rel_path,
                            match_type='file',
                            name=f,
                            score=0.7,
                        ))

        return results

    def sync_all(self) -> Dict[str, Any]:
        """同步所有仓库索引

        Returns:
            同步结果
        """
        results = {
            'success': [],
            'failed': [],
            'total': len(self._repos),
        }

        for name, repo in self._repos.items():
            try:
                repo_path = Path(repo.path)
                if not repo_path.exists():
                    results['failed'].append({'name': name, 'reason': 'Path not found'})
                    continue

                # 更新仓库信息
                updated_info = self._analyze_repo(repo_path)
                updated_info.name = name
                updated_info.type = repo.type
                updated_info.last_sync = datetime.now().isoformat()
                self._repos[name] = updated_info

                results['success'].append(name)

            except Exception as e:
                results['failed'].append({'name': name, 'reason': str(e)})

        self._save_config()
        return results

    def get_dep_graph(self) -> Dict[str, Any]:
        """获取仓库间依赖图

        Returns:
            依赖图数据
        """
        nodes = []
        edges = []

        # 构建节点
        for name, repo in self._repos.items():
            nodes.append({
                'id': name,
                'type': repo.type.value,
                'language': repo.language,
            })

        # 构建边
        for link in self._links:
            edges.append({
                'source': link.get('from'),
                'target': link.get('to'),
                'type': link.get('type', 'unknown'),
            })

        # 自动检测依赖关系
        auto_edges = self._detect_dependencies()
        for edge in auto_edges:
            if edge not in edges:
                edges.append(edge)

        return {
            'nodes': nodes,
            'edges': edges,
        }

    def _detect_dependencies(self) -> List[Dict]:
        """检测仓库间依赖关系"""
        edges = []

        # 分析每个仓库的依赖
        for name, repo in self._repos.items():
            repo_path = Path(repo.path)

            # 检查 package.json
            pkg_json = repo_path / 'package.json'
            if pkg_json.exists():
                deps = self._parse_package_deps(pkg_json)
                for dep in deps:
                    # 检查是否是其他仓库
                    for other_name, other_repo in self._repos.items():
                        if other_name != name and other_name in dep:
                            edges.append({
                                'source': name,
                                'target': other_name,
                                'type': 'npm',
                            })

            # 检查 pom.xml
            pom_xml = repo_path / 'pom.xml'
            if pom_xml.exists():
                deps = self._parse_maven_deps(pom_xml)
                for dep in deps:
                    for other_name, other_repo in self._repos.items():
                        if other_name != name and other_name in dep:
                            edges.append({
                                'source': name,
                                'target': other_name,
                                'type': 'maven',
                            })

        return edges

    def _parse_package_deps(self, pkg_json: Path) -> List[str]:
        """解析 package.json 依赖"""
        try:
            with open(pkg_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            deps = list(data.get('dependencies', {}).keys())
            deps.extend(data.get('devDependencies', {}).keys())
            return deps
        except Exception:
            return []

    def _parse_maven_deps(self, pom_xml: Path) -> List[str]:
        """解析 pom.xml 依赖"""
        # 简化实现，返回空列表
        return []

    def _detect_repo_type(self, repo_path: Path) -> str:
        """检测仓库类型"""
        scores = {}

        for repo_type, patterns in self.TYPE_PATTERNS.items():
            score = 0

            # 检查文件
            for f in patterns.get('files', []):
                if (repo_path / f).exists():
                    score += 1

            # 检查目录
            for d in patterns.get('dirs', []):
                if (repo_path / d).exists():
                    score += 0.5

            # 检查关键词
            pkg_json = repo_path / 'package.json'
            if pkg_json.exists():
                try:
                    with open(pkg_json, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                    for kw in patterns.get('keywords', []):
                        if kw in content:
                            score += 0.5
                except Exception:
                    pass

            scores[repo_type] = score

        if scores:
            best_type = max(scores, key=scores.get)
            if scores[best_type] > 0:
                return best_type.value

        return RepoType.UNKNOWN.value

    def _analyze_repo(self, repo_path: Path) -> RepoInfo:
        """分析仓库"""
        info = RepoInfo(
            name="",
            path=str(repo_path),
        )

        # 统计文件和行数
        file_count = 0
        line_count = 0

        for root, dirs, files in os.walk(repo_path):
            # 排除目录
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', 'venv', '__pycache__', 'build', 'dist'}]

            for f in files:
                file_path = Path(root, f)
                file_count += 1

                # 计算行数（文本文件）
                ext = file_path.suffix.lower()
                if ext in {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.c', '.cpp', '.h', '.html', '.css', '.json', '.yaml', '.yml', '.md'}:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                            line_count += sum(1 for _ in file)
                    except Exception:
                        continue

        info.file_count = file_count
        info.line_count = line_count

        # 检测语言
        info.language = self._detect_language(repo_path)

        # 检测构建系统
        info.build_system = self._detect_build_system(repo_path)

        return info

    def _detect_language(self, repo_path: Path) -> str:
        """检测主要语言"""
        lang_files = {
            'python': ['.py'],
            'javascript': ['.js', '.jsx'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java'],
            'go': ['.go'],
            'rust': ['.rs'],
            'c': ['.c', '.h'],
            'cpp': ['.cpp', '.hpp', '.cc'],
        }

        counts = {lang: 0 for lang in lang_files}

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', 'venv'}]

            for f in files:
                ext = Path(f).suffix.lower()
                for lang, exts in lang_files.items():
                    if ext in exts:
                        counts[lang] += 1

        if max(counts.values()) > 0:
            return max(counts, key=counts.get)
        return "unknown"

    def _detect_build_system(self, repo_path: Path) -> str:
        """检测构建系统"""
        build_files = {
            'package.json': 'npm/yarn',
            'Cargo.toml': 'cargo',
            'go.mod': 'go mod',
            'pom.xml': 'maven',
            'build.gradle': 'gradle',
            'CMakeLists.txt': 'cmake',
            'Makefile': 'make',
            'requirements.txt': 'pip',
            'pyproject.toml': 'poetry',
        }

        for file_name, build_system in build_files.items():
            if (repo_path / file_name).exists():
                return build_system

        return "unknown"

    def _load_config(self):
        """加载配置"""
        config_path = self._config_path or self._meta_dir / 'monorepo.yaml'

        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}

                # 加载仓库
                for repo_config in config.get('repos', []):
                    name = repo_config.get('name')
                    path = repo_config.get('path')
                    if name and path:
                        info = RepoInfo(
                            name=name,
                            path=path,
                            type=RepoType(repo_config.get('type', 'unknown')),
                            language=repo_config.get('language', ''),
                            build_system=repo_config.get('build_system', ''),
                        )
                        self._repos[name] = info

                # 加载链接
                self._links = config.get('links', [])

            except Exception:
                pass

    def _save_config(self):
        """保存配置"""
        config_path = self._config_path or self._meta_dir / 'monorepo.yaml'
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config = {
            'repos': [repo.to_dict() for repo in self._repos.values()],
            'links': self._links,
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    def to_mermaid_graph(self) -> str:
        """生成 Mermaid 依赖图"""
        dep_graph = self.get_dep_graph()

        lines = ['graph TD']

        # 添加节点
        for node in dep_graph['nodes']:
            node_id = node['id']
            node_type = node['type']
            lines.append(f"    {node_id}[{node_id}<br/>{node_type}]")

        # 添加边
        for edge in dep_graph['edges']:
            lines.append(f"    {edge['source']} -->|{edge['type']}| {edge['target']}")

        return '\n'.join(lines)


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: mono_manager.py <project_dir> [command]")
        print("\nCommands:")
        print("  list        List all repos")
        print("  detect      Detect related repos")
        print("  search      Cross-repo search")
        print("  graph       Show dependency graph")
        print("  sync        Sync all repos")
        sys.exit(1)

    project_dir = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else 'list'

    manager = MonoRepoManager(project_dir)

    if command == 'list':
        repos = manager.list_repos()
        for repo in repos:
            print(f"- {repo.name}: {repo.type.value} ({repo.language})")

    elif command == 'detect':
        detected = manager.detect_repos()
        print(f"Detected {len(detected)} repos:")
        for repo in detected:
            print(f"  - {repo.name}: {repo.type} ({repo.language})")

    elif command == 'search':
        if len(sys.argv) < 4:
            print("Usage: mono_manager.py <project_dir> search <query>")
            sys.exit(1)
        query = sys.argv[3]
        results = manager.cross_repo_search(query)
        for r in results:
            print(f"[{r.repo_name}] {r.file_path}: {r.name} ({r.match_type})")

    elif command == 'graph':
        print(manager.to_mermaid_graph())

    elif command == 'sync':
        results = manager.sync_all()
        print(f"Synced: {len(results['success'])} success, {len(results['failed'])} failed")


if __name__ == '__main__':
    main()