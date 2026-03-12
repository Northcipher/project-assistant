#!/usr/bin/env python3
"""
分层延迟索引器
支持百万行代码项目的快速索引

分层架构:
- L0 快速索引 (< 1s): 文件列表、类型、最近修改
- L1 结构索引 (< 5s): 函数/类定义、导入关系
- L2 语义索引 (< 30s): 调用图、依赖图、向量嵌入
- L3 深度索引 (后台): 全量 AST、代码质量分析
"""

import os
import json
import time
import hashlib
import threading
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, Future
from enum import Enum


class IndexLevel(Enum):
    """索引层级"""
    L0 = 0  # 快速索引
    L1 = 1  # 结构索引
    L2 = 2  # 语义索引
    L3 = 3  # 深度索引


@dataclass
class L0Index:
    """L0 快速索引: 文件元数据"""
    files: List[Dict[str, Any]] = field(default_factory=list)
    file_types: Dict[str, int] = field(default_factory=dict)
    last_modified: Dict[str, str] = field(default_factory=dict)
    total_files: int = 0
    total_lines: int = 0
    build_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'files': self.files[:100],  # 限制输出
            'file_types': self.file_types,
            'total_files': self.total_files,
            'total_lines': self.total_lines,
            'build_time': self.build_time,
        }


@dataclass
class L1Index:
    """L1 结构索引: 函数/类定义、导入关系"""
    functions: Dict[str, List[Dict]] = field(default_factory=dict)  # file -> functions
    classes: Dict[str, List[Dict]] = field(default_factory=dict)  # file -> classes
    imports: Dict[str, List[str]] = field(default_factory=dict)  # file -> imports
    exports: Dict[str, List[str]] = field(default_factory=dict)  # file -> exports
    total_functions: int = 0
    total_classes: int = 0
    build_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_functions': self.total_functions,
            'total_classes': self.total_classes,
            'build_time': self.build_time,
        }


@dataclass
class L2Index:
    """L2 语义索引: 调用图、依赖图、向量嵌入"""
    call_graph: Dict[str, List[str]] = field(default_factory=dict)  # func -> callers
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)  # module -> deps
    embeddings_indexed: bool = False
    total_calls: int = 0
    build_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_calls': self.total_calls,
            'embeddings_indexed': self.embeddings_indexed,
            'build_time': self.build_time,
        }


@dataclass
class L3Index:
    """L3 深度索引: 全量 AST、代码质量"""
    ast_cache: Dict[str, Any] = field(default_factory=dict)
    quality_scores: Dict[str, float] = field(default_factory=dict)
    issues: List[Dict] = field(default_factory=list)
    build_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'quality_score_avg': sum(self.quality_scores.values()) / len(self.quality_scores) if self.quality_scores else 0,
            'issues_count': len(self.issues),
            'build_time': self.build_time,
        }


@dataclass
class IndexStatus:
    """索引状态"""
    l0_ready: bool = False
    l1_ready: bool = False
    l2_ready: bool = False
    l3_ready: bool = False
    l1_progress: float = 0.0
    l2_progress: float = 0.0
    l3_progress: float = 0.0
    last_update: str = ""
    error: str = ""


class LazyIndexer:
    """分层延迟索引器

    设计原则:
    - L0 总是同步构建，保证 < 1s
    - L1 按需构建，可指定文件列表
    - L2 后台构建，支持预热
    - L3 完全后台，不阻塞主流程
    """

    # 文件类型映射
    FILE_TYPE_EXTENSIONS = {
        'python': {'.py'},
        'javascript': {'.js', '.jsx', '.mjs'},
        'typescript': {'.ts', '.tsx'},
        'java': {'.java'},
        'kotlin': {'.kt', '.kts'},
        'go': {'.go'},
        'rust': {'.rs'},
        'c': {'.c', '.h'},
        'cpp': {'.cpp', '.cc', '.cxx', '.hpp', '.hxx'},
        'csharp': {'.cs'},
        'swift': {'.swift'},
        'ruby': {'.rb'},
        'php': {'.php'},
        'scala': {'.scala'},
        'config': {'.json', '.yaml', '.yml', '.toml', '.ini', '.conf', '.cfg'},
        'doc': {'.md', '.rst', '.txt'},
        'html': {'.html', '.htm'},
        'css': {'.css', '.scss', '.less', '.sass'},
        'shell': {'.sh', '.bash', '.zsh', '.bat'},
    }

    # 排除目录
    EXCLUDE_DIRS = {
        '.git', '.svn', '.hg',
        'node_modules', 'venv', '.venv', 'env', '__pycache__',
        'dist', 'build', 'target', 'out', '.gradle',
        '.idea', '.vscode', 'Pods',
    }

    # 排除文件
    EXCLUDE_FILES = {
        '*.min.js', '*.min.css', '*.map', '*.lock',
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    }

    def __init__(self, project_dir: str, max_workers: int = None):
        """初始化索引器

        Args:
            project_dir: 项目目录
            max_workers: 最大工作线程数
        """
        self.project_dir = Path(project_dir).resolve()
        self.max_workers = max_workers or os.cpu_count() or 4
        self._index_dir = self.project_dir / '.projmeta' / 'index'

        # 索引缓存
        self._l0_index: Optional[L0Index] = None
        self._l1_index: Optional[L1Index] = None
        self._l2_index: Optional[L2Index] = None
        self._l3_index: Optional[L3Index] = None

        # 状态
        self._status = IndexStatus()
        self._lock = threading.RLock()
        self._background_tasks: Dict[str, Future] = {}

        # 后台线程池
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

    @property
    def status(self) -> IndexStatus:
        """获取索引状态"""
        return self._status

    def build_l0_index(self, force: bool = False) -> L0Index:
        """构建 L0 快速索引

        目标: < 1s 完成

        Args:
            force: 是否强制重建

        Returns:
            L0Index: 快速索引
        """
        start_time = time.time()

        if self._l0_index and not force:
            return self._l0_index

        # 尝试从缓存加载
        if not force:
            cached = self._load_index('l0')
            if cached:
                self._l0_index = L0Index(**cached)
                self._status.l0_ready = True
                return self._l0_index

        # 构建索引
        files = []
        file_types: Dict[str, int] = {}
        last_modified: Dict[str, str] = {}
        total_lines = 0

        for root, dirs, filenames in os.walk(self.project_dir):
            # 过滤排除目录
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]

            for filename in filenames:
                # 过滤排除文件
                if self._should_exclude_file(filename):
                    continue

                file_path = Path(root) / filename
                rel_path = str(file_path.relative_to(self.project_dir))

                try:
                    stat = file_path.stat()
                    file_type = self._get_file_type(filename)
                    line_count = self._count_lines(file_path) if self._is_text_file(filename) else 0

                    files.append({
                        'path': rel_path,
                        'type': file_type,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'lines': line_count,
                    })

                    file_types[file_type] = file_types.get(file_type, 0) + 1
                    last_modified[rel_path] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    total_lines += line_count

                except Exception:
                    continue

        build_time = time.time() - start_time

        self._l0_index = L0Index(
            files=files,
            file_types=file_types,
            last_modified=last_modified,
            total_files=len(files),
            total_lines=total_lines,
            build_time=build_time,
        )

        # 保存缓存
        self._save_index('l0', self._l0_index.to_dict())

        with self._lock:
            self._status.l0_ready = True
            self._status.last_update = datetime.now().isoformat()

        return self._l0_index

    def get_l0_index(self) -> L0Index:
        """获取 L0 索引（如果不存在则构建）"""
        if not self._l0_index:
            return self.build_l0_index()
        return self._l0_index

    def get_l1_index(self, files: List[str] = None) -> L1Index:
        """获取 L1 结构索引

        Args:
            files: 指定文件列表（可选，不指定则全量）

        Returns:
            L1Index: 结构索引
        """
        if self._l1_index and not files:
            return self._l1_index

        # 按需构建
        return self._build_l1_index(files)

    def _build_l1_index(self, files: List[str] = None) -> L1Index:
        """构建 L1 结构索引"""
        start_time = time.time()

        # 尝试从缓存加载
        cached = self._load_index('l1')
        if cached and not files:
            self._l1_index = L1Index(**cached)
            self._status.l1_ready = True
            return self._l1_index

        # 获取 L0 索引
        l0 = self.get_l0_index()
        target_files = files if files else [f['path'] for f in l0.files]

        functions: Dict[str, List[Dict]] = {}
        classes: Dict[str, List[Dict]] = {}
        imports: Dict[str, List[str]] = {}
        exports: Dict[str, List[str]] = {}
        total_functions = 0
        total_classes = 0

        # 尝试使用 AST 解析器
        try:
            from ast_parser import ASTParser
            parser = ASTParser()

            for file_path in target_files:
                full_path = self.project_dir / file_path
                if not full_path.exists():
                    continue

                try:
                    result = parser.parse_file(str(full_path))
                    if result:
                        functions[file_path] = result.get('functions', [])
                        classes[file_path] = result.get('classes', [])
                        imports[file_path] = result.get('imports', [])
                        exports[file_path] = result.get('exports', [])
                        total_functions += len(result.get('functions', []))
                        total_classes += len(result.get('classes', []))
                except Exception:
                    continue

        except ImportError:
            # 回退到简单解析
            for file_path in target_files:
                full_path = self.project_dir / file_path
                if not full_path.exists():
                    continue

                try:
                    simple_result = self._simple_parse(full_path)
                    functions[file_path] = simple_result.get('functions', [])
                    classes[file_path] = simple_result.get('classes', [])
                    total_functions += len(simple_result.get('functions', []))
                    total_classes += len(simple_result.get('classes', []))
                except Exception:
                    continue

        build_time = time.time() - start_time

        self._l1_index = L1Index(
            functions=functions,
            classes=classes,
            imports=imports,
            exports=exports,
            total_functions=total_functions,
            total_classes=total_classes,
            build_time=build_time,
        )

        # 保存缓存
        self._save_index('l1', self._l1_index.to_dict())

        with self._lock:
            self._status.l1_ready = True

        return self._l1_index

    def warmup_l2(self, priority_files: List[str] = None, callback=None):
        """预热 L2 索引（后台构建）

        Args:
            priority_files: 优先构建的文件列表
            callback: 完成回调
        """
        if 'l2' in self._background_tasks and not self._background_tasks['l2'].done():
            return  # 已经在后台运行

        def build_l2():
            try:
                self._build_l2_index(priority_files)
                if callback:
                    callback(True, self._l2_index)
            except Exception as e:
                if callback:
                    callback(False, str(e))

        self._background_tasks['l2'] = self._executor.submit(build_l2)

    def _build_l2_index(self, priority_files: List[str] = None) -> L2Index:
        """构建 L2 语义索引"""
        start_time = time.time()

        # 获取 L1 索引
        l1 = self.get_l1_index()

        call_graph: Dict[str, List[str]] = {}
        dependency_graph: Dict[str, List[str]] = {}
        total_calls = 0

        # 构建调用图
        try:
            from utils.call_chain_analyzer import CallChainAnalyzer
            analyzer = CallChainAnalyzer(str(self.project_dir))
            # 简化: 只统计调用关系
            for file_path, funcs in l1.functions.items():
                for func in funcs:
                    func_name = func.get('name', '')
                    if func_name:
                        callers = analyzer.find_callers(func_name)
                        if callers:
                            call_graph[func_name] = callers
                            total_calls += len(callers)
        except Exception:
            pass

        # 构建依赖图
        for file_path, imports in l1.imports.items():
            deps = []
            for imp in imports:
                # 简化依赖关系
                if imp.startswith('.'):
                    deps.append(imp)
            if deps:
                dependency_graph[file_path] = deps

        build_time = time.time() - start_time

        self._l2_index = L2Index(
            call_graph=call_graph,
            dependency_graph=dependency_graph,
            embeddings_indexed=False,  # 向量索引需要单独构建
            total_calls=total_calls,
            build_time=build_time,
        )

        self._save_index('l2', self._l2_index.to_dict())

        with self._lock:
            self._status.l2_ready = True

        return self._l2_index

    def build_l3_index(self, callback=None):
        """构建 L3 深度索引（后台）

        Args:
            callback: 完成回调
        """
        if 'l3' in self._background_tasks and not self._background_tasks['l3'].done():
            return

        def build_l3():
            try:
                result = self._build_l3_index()
                if callback:
                    callback(True, result)
            except Exception as e:
                if callback:
                    callback(False, str(e))

        self._background_tasks['l3'] = self._executor.submit(build_l3)

    def _build_l3_index(self) -> L3Index:
        """构建 L3 深度索引"""
        start_time = time.time()

        l1 = self.get_l1_index()
        quality_scores: Dict[str, float] = {}
        issues: List[Dict] = []

        # 尝试使用 AI 分析器
        try:
            from ai_analyzer import AIAnalyzer
            analyzer = AIAnalyzer()

            for file_path in list(l1.functions.keys())[:100]:  # 限制数量
                full_path = self.project_dir / file_path
                if not full_path.exists():
                    continue

                try:
                    result = analyzer.analyze_file(str(full_path))
                    if result:
                        quality_scores[file_path] = result.get('quality_score', 0.5)
                        issues.extend(result.get('issues', []))
                except Exception:
                    continue

        except ImportError:
            pass

        build_time = time.time() - start_time

        self._l3_index = L3Index(
            quality_scores=quality_scores,
            issues=issues,
            build_time=build_time,
        )

        self._save_index('l3', self._l3_index.to_dict())

        with self._lock:
            self._status.l3_ready = True

        return self._l3_index

    def search(self, query: str, level: IndexLevel = IndexLevel.L1) -> List[Dict]:
        """搜索索引

        Args:
            query: 搜索查询
            level: 搜索层级

        Returns:
            搜索结果列表
        """
        results = []

        if level.value >= IndexLevel.L0.value and self._l0_index:
            # 文件名搜索
            for f in self._l0_index.files:
                if query.lower() in f['path'].lower():
                    results.append({
                        'type': 'file',
                        'path': f['path'],
                        'score': 1.0,
                    })

        if level.value >= IndexLevel.L1.value and self._l1_index:
            # 函数/类搜索
            for file_path, funcs in self._l1_index.functions.items():
                for func in funcs:
                    if query.lower() in func.get('name', '').lower():
                        results.append({
                            'type': 'function',
                            'name': func.get('name'),
                            'path': file_path,
                            'line': func.get('line', 0),
                            'score': 0.9,
                        })

            for file_path, classes in self._l1_index.classes.items():
                for cls in classes:
                    if query.lower() in cls.get('name', '').lower():
                        results.append({
                            'type': 'class',
                            'name': cls.get('name'),
                            'path': file_path,
                            'line': cls.get('line', 0),
                            'score': 0.9,
                        })

        # 按分数排序
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return results[:50]

    def incremental_update(self, changed_files: List[str]) -> Dict[str, Any]:
        """增量更新索引

        Args:
            changed_files: 变更文件列表

        Returns:
            更新结果
        """
        result = {
            'updated_l0': False,
            'updated_l1': False,
            'updated_l2': False,
            'files_processed': 0,
        }

        if not changed_files:
            return result

        # 更新 L0
        if self._l0_index:
            for file_path in changed_files:
                full_path = self.project_dir / file_path
                if full_path.exists():
                    # 添加或更新文件
                    stat = full_path.stat()
                    file_type = self._get_file_type(full_path.name)

                    # 更新文件列表
                    existing = next((f for f in self._l0_index.files if f['path'] == file_path), None)
                    if existing:
                        existing['modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                        existing['size'] = stat.st_size
                    else:
                        self._l0_index.files.append({
                            'path': file_path,
                            'type': file_type,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        })
                        self._l0_index.total_files += 1

            result['updated_l0'] = True

        # 更新 L1
        if self._l1_index:
            for file_path in changed_files:
                full_path = self.project_dir / file_path
                if full_path.exists():
                    try:
                        from ast_parser import ASTParser
                        parser = ASTParser()
                        parse_result = parser.parse_file(str(full_path))

                        if parse_result:
                            self._l1_index.functions[file_path] = parse_result.get('functions', [])
                            self._l1_index.classes[file_path] = parse_result.get('classes', [])
                            result['files_processed'] += 1
                    except Exception:
                        continue

            result['updated_l1'] = True

        # L2 需要重建
        if self._l2_index:
            result['updated_l2'] = 'needs_rebuild'

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        return {
            'l0': {
                'ready': self._status.l0_ready,
                'files': self._l0_index.total_files if self._l0_index else 0,
                'lines': self._l0_index.total_lines if self._l0_index else 0,
                'build_time': self._l0_index.build_time if self._l0_index else 0,
            },
            'l1': {
                'ready': self._status.l1_ready,
                'functions': self._l1_index.total_functions if self._l1_index else 0,
                'classes': self._l1_index.total_classes if self._l1_index else 0,
                'build_time': self._l1_index.build_time if self._l1_index else 0,
            },
            'l2': {
                'ready': self._status.l2_ready,
                'calls': self._l2_index.total_calls if self._l2_index else 0,
                'build_time': self._l2_index.build_time if self._l2_index else 0,
            },
            'l3': {
                'ready': self._status.l3_ready,
                'build_time': self._l3_index.build_time if self._l3_index else 0,
            },
            'last_update': self._status.last_update,
        }

    def _should_exclude_file(self, filename: str) -> bool:
        """判断是否应排除文件"""
        import fnmatch
        for pattern in self.EXCLUDE_FILES:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    def _get_file_type(self, filename: str) -> str:
        """获取文件类型"""
        ext = Path(filename).suffix.lower()
        for file_type, extensions in self.FILE_TYPE_EXTENSIONS.items():
            if ext in extensions:
                return file_type
        return 'other'

    def _is_text_file(self, filename: str) -> bool:
        """判断是否是文本文件"""
        text_extensions = set()
        for exts in self.FILE_TYPE_EXTENSIONS.values():
            text_extensions.update(exts)
        ext = Path(filename).suffix.lower()
        return ext in text_extensions

    def _count_lines(self, file_path: Path) -> int:
        """计算文件行数"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def _simple_parse(self, file_path: Path) -> Dict[str, List]:
        """简单解析文件（无 AST 解析器时的回退）"""
        result = {'functions': [], 'classes': []}

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            ext = file_path.suffix.lower()

            if ext == '.py':
                # Python 函数/类检测
                import re
                for m in re.finditer(r'^def\s+(\w+)', content, re.MULTILINE):
                    result['functions'].append({'name': m.group(1), 'line': content[:m.start()].count('\n') + 1})
                for m in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
                    result['classes'].append({'name': m.group(1), 'line': content[:m.start()].count('\n') + 1})

            elif ext in {'.js', '.ts', '.jsx', '.tsx'}:
                # JavaScript 函数检测
                import re
                for m in re.finditer(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()', content):
                    name = m.group(1) or m.group(2)
                    result['functions'].append({'name': name, 'line': content[:m.start()].count('\n') + 1})
                for m in re.finditer(r'class\s+(\w+)', content):
                    result['classes'].append({'name': m.group(1), 'line': content[:m.start()].count('\n') + 1})

        except Exception:
            pass

        return result

    def _load_index(self, level: str) -> Optional[Dict]:
        """加载索引缓存"""
        index_path = self._index_dir / f'{level}.json'
        if index_path.exists():
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _save_index(self, level: str, data: Dict):
        """保存索引缓存"""
        self._index_dir.mkdir(parents=True, exist_ok=True)
        index_path = self._index_dir / f'{level}.json'
        try:
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    def shutdown(self):
        """关闭索引器"""
        self._executor.shutdown(wait=False)


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: lazy_indexer.py <project_dir> [command]")
        print("\nCommands:")
        print("  build-l0    Build L0 index")
        print("  build-l1    Build L1 index")
        print("  stats       Show index stats")
        print("  search      Search in index")
        sys.exit(1)

    project_dir = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else 'stats'

    indexer = LazyIndexer(project_dir)

    if command == 'build-l0':
        print("Building L0 index...")
        l0 = indexer.build_l0_index()
        print(f"Done in {l0.build_time:.2f}s")
        print(f"Files: {l0.total_files}, Lines: {l0.total_lines}")

    elif command == 'build-l1':
        print("Building L1 index...")
        l1 = indexer.get_l1_index()
        print(f"Done in {l1.build_time:.2f}s")
        print(f"Functions: {l1.total_functions}, Classes: {l1.total_classes}")

    elif command == 'search':
        query = sys.argv[3] if len(sys.argv) > 3 else ''
        results = indexer.search(query)
        print(json.dumps(results, indent=2, ensure_ascii=False))

    else:
        stats = indexer.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()