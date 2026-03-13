#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目数据收集器
负责收集结构化数据，供 AI 分析使用

职责边界：
- 脚本负责：数据收集、规则匹配、结构化输出
- AI 负责：语义理解、内容生成、智能决策
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import xml.etree.ElementTree as ET

# 设置 UTF-8 编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# 排除目录
EXCLUDE_DIRS = {
    '.git', '.svn', '.hg', '.repo', '.idea', '.vscode',
    'node_modules', 'venv', '.venv', 'env', '__pycache__',
    '.pytest_cache', '.mypy_cache', 'dist', 'build', 'out',
    'target', 'vendor', 'CMakeFiles', '_deps', 'Output',
    'Listings', 'Objects', 'DebugConfig', 'RTE', '.gradle',
    'Pods', 'DerivedData', '.projmeta', 'test-projects',
}

# 源码文件扩展名
SOURCE_EXTENSIONS = {
    'c': ['.c', '.h', '.cpp', '.hpp', '.cc', '.cxx'],
    'python': ['.py', '.pyw'],
    'java': ['.java', '.kt', '.kts'],
    'javascript': ['.js', '.jsx', '.ts', '.tsx', '.mjs'],
    'go': ['.go'],
    'rust': ['.rs'],
    'shell': ['.sh', '.bash', '.zsh'],
    'cmake': ['.cmake'],
    'make': ['.mk'],
    'config': ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.xml'],
}

# 入口文件模式
ENTRY_PATTERNS = [
    'main.py', 'main.c', 'main.cpp', 'main.go', 'main.rs', 'main.java',
    'app.py', 'app.js', 'app.ts', 'index.js', 'index.ts', 'index.tsx',
    'manage.py', 'run.py', 'server.py', '__main__.py',
    'setup.py', 'setup.cfg', 'pyproject.toml',
    'Makefile', 'CMakeLists.txt', 'build.py',
]

# 配置文件模式
CONFIG_PATTERNS = [
    'config.json', 'config.yaml', 'config.yml', 'config.toml', 'config.ini',
    'settings.py', 'settings.json', 'settings.yaml',
    '.env', '.env.local', '.env.development', '.env.production',
    'requirements.txt', 'package.json', 'Cargo.toml', 'go.mod',
    'pyproject.toml', 'setup.py', 'setup.cfg',
    'Makefile', 'CMakeLists.txt', 'Kconfig',
    'manifest.xml', 'default.xml',
]


@dataclass
class SourceFileGroup:
    """源码文件分组"""
    language: str
    count: int
    files: List[str] = field(default_factory=list)


@dataclass
class SubProject:
    """子项目信息"""
    name: str
    path: str
    revision: str = ""
    project_type: str = "unknown"
    description: str = ""  # AI 填充


@dataclass
class Module:
    """模块信息"""
    name: str
    path: str
    description: str = ""  # AI 填充
    file_count: int = 0
    languages: List[str] = field(default_factory=list)


@dataclass
class ConfigFile:
    """配置文件"""
    path: str
    type: str
    size: int = 0
    content_preview: str = ""  # 前 500 字符


@dataclass
class ProjectData:
    """项目结构化数据"""
    # 基本信息 (脚本收集)
    name: str
    root_path: str
    project_type: str
    confidence: float
    detected_languages: List[str]
    detected_build_systems: List[str]

    # 规模信息
    total_files: int
    total_dirs: int
    total_size: int

    # 目录结构 (脚本生成)
    directory_tree: str

    # 文件清单 (脚本收集)
    source_files: List[SourceFileGroup]
    entry_files: List[str]
    config_files: List[Dict[str, Any]]

    # Repo 项目特有
    is_repo_project: bool = False
    sub_projects: List[Dict[str, Any]] = field(default_factory=list)

    # 模块信息 (脚本收集目录名，AI 生成描述)
    modules: List[Dict[str, Any]] = field(default_factory=list)

    # 依赖 (脚本解析)
    dependencies: List[Dict[str, str]] = field(default_factory=list)

    # 以下字段留给 AI 填充
    ai_analysis: Dict[str, Any] = field(default_factory=dict)

    # 元信息
    collection_time: str = ""
    collection_duration_ms: int = 0


class ProjectCollector:
    """项目数据收集器"""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir).resolve()
        self._files: List[str] = []
        self._dirs: List[str] = []

    def collect(self) -> ProjectData:
        """收集项目数据"""
        start_time = time.time()

        print(f"正在收集项目数据: {self.project_dir}")

        # 1. 收集文件和目录
        self._collect_files_and_dirs()
        print(f"  扫描到 {len(self._files)} 个文件, {len(self._dirs)} 个目录")

        # 2. 探测项目类型
        project_type, confidence = self._detect_project_type()
        print(f"  项目类型: {project_type} (置信度: {confidence:.0%})")

        # 3. 统计语言
        source_groups = self._group_source_files()
        languages = [g.language for g in source_groups if g.count > 0]
        print(f"  语言: {', '.join(languages) if languages else '未检测到'}")

        # 4. 探测构建系统
        build_systems = self._detect_build_systems()
        print(f"  构建系统: {', '.join(build_systems) if build_systems else '未检测到'}")

        # 5. 生成目录树
        directory_tree = self._generate_directory_tree()
        print(f"  目录树已生成")

        # 6. 查找入口文件
        entry_files = self._find_entry_files()
        print(f"  入口文件: {len(entry_files)} 个")

        # 7. 收集配置文件
        config_files = self._collect_config_files()
        print(f"  配置文件: {len(config_files)} 个")

        # 8. 检测子项目 (Repo 项目)
        sub_projects = []
        is_repo = False
        if (self.project_dir / '.repo' / 'manifest.xml').exists():
            is_repo = True
            sub_projects = self._parse_repo_manifest()
            print(f"  Repo 子项目: {len(sub_projects)} 个")

        # 9. 识别模块
        modules = self._detect_modules()
        print(f"  模块: {len(modules)} 个")

        # 10. 解析依赖
        dependencies = self._parse_dependencies()
        print(f"  依赖: {len(dependencies)} 个")

        duration = int((time.time() - start_time) * 1000)

        return ProjectData(
            name=self.project_dir.name,
            root_path=str(self.project_dir),
            project_type=project_type,
            confidence=confidence,
            detected_languages=languages,
            detected_build_systems=build_systems,
            total_files=len(self._files),
            total_dirs=len(self._dirs),
            total_size=sum(self._get_file_size(f) for f in self._files),
            directory_tree=directory_tree,
            source_files=[asdict(g) for g in source_groups],
            entry_files=entry_files,
            config_files=config_files,
            is_repo_project=is_repo,
            sub_projects=sub_projects,
            modules=modules,
            dependencies=dependencies,
            collection_time=datetime.now().isoformat(),
            collection_duration_ms=duration,
        )

    def _collect_files_and_dirs(self, max_depth: int = 5):
        """收集文件和目录"""
        for root, dirs, files in os.walk(self.project_dir):
            # 排除特定目录
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            rel_root = os.path.relpath(root, self.project_dir)
            depth = 0 if rel_root == '.' else rel_root.count(os.sep) + 1

            if depth > max_depth:
                dirs[:] = []
                continue

            for f in files:
                rel_path = os.path.join(rel_root, f) if rel_root != '.' else f
                self._files.append(rel_path)

            for d in dirs:
                rel_path = os.path.join(rel_root, d) if rel_root != '.' else d
                self._dirs.append(rel_path)

    def _detect_project_type(self) -> tuple:
        """探测项目类型"""
        files_set = set(self._files)
        dirs_set = set(self._dirs)

        # Repo 项目
        if '.repo/manifest.xml' in files_set:
            if any('project/' in d for d in dirs_set):
                return ('chip-sdk', 0.95)
            if any('device/' in d for d in dirs_set):
                return ('aosp', 0.95)
            if any('vendor/' in d for d in dirs_set):
                return ('android-vendor-sdk', 0.95)
            return ('repo-mono', 0.90)

        # Android
        if 'AndroidManifest.xml' in files_set:
            return ('android-app', 0.95)
        if 'build.gradle' in files_set or 'build.gradle.kts' in files_set:
            return ('android-app', 0.85)

        # 嵌入式
        if any(f.endswith('.ioc') for f in self._files):
            return ('stm32', 0.95)
        if 'sdkconfig' in files_set:
            return ('esp32', 0.90)
        if 'FreeRTOSConfig.h' in files_set:
            return ('freertos', 0.90)

        # Web
        if 'package.json' in files_set:
            if any('src/index.tsx' in f or 'src/main.tsx' in f for f in self._files):
                return ('react', 0.85)
            if 'next.config.js' in files_set or 'next.config.ts' in files_set:
                return ('nextjs', 0.90)
            return ('node', 0.70)

        # Python
        if 'requirements.txt' in files_set or 'pyproject.toml' in files_set:
            if 'manage.py' in files_set:
                return ('django', 0.90)
            if any('fastapi' in f for f in self._files):
                return ('fastapi', 0.80)
            return ('python', 0.70)

        # C/C++
        if 'CMakeLists.txt' in files_set:
            return ('cmake', 0.80)
        if 'Makefile' in files_set:
            return ('makefile', 0.75)

        return ('unknown', 0.0)

    def _group_source_files(self) -> List[SourceFileGroup]:
        """按语言分组源码文件"""
        groups = []

        for lang, exts in SOURCE_EXTENSIONS.items():
            files = [f for f in self._files if any(f.endswith(ext) for ext in exts)]
            if files:
                groups.append(SourceFileGroup(
                    language=lang,
                    count=len(files),
                    files=files[:20]  # 最多保留 20 个示例
                ))

        # 按数量排序
        groups.sort(key=lambda g: g.count, reverse=True)
        return groups

    def _detect_build_systems(self) -> List[str]:
        """探测构建系统"""
        systems = []
        files_set = set(self._files)

        if 'CMakeLists.txt' in files_set:
            systems.append('cmake')
        if 'Makefile' in files_set or any(f.endswith('.mk') for f in self._files):
            systems.append('make')
        if 'package.json' in files_set:
            systems.append('npm')
        if 'requirements.txt' in files_set or 'pyproject.toml' in files_set:
            systems.append('pip')
        if 'Cargo.toml' in files_set:
            systems.append('cargo')
        if 'go.mod' in files_set:
            systems.append('go-mod')
        if 'build.gradle' in files_set or 'build.gradle.kts' in files_set:
            systems.append('gradle')
        if 'pom.xml' in files_set:
            systems.append('maven')
        if '.repo/manifest.xml' in files_set:
            systems.append('repo')

        return systems

    def _generate_directory_tree(self, max_depth: int = 3, max_files_per_dir: int = 10) -> str:
        """生成目录结构树"""
        lines = [f"{self.project_dir.name}/"]

        def get_depth(path: str) -> int:
            return path.count(os.sep)

        # 按目录分组
        dir_files = {}
        for f in self._files:
            parts = f.split(os.sep)
            if len(parts) == 1:
                parent = ''
            else:
                parent = os.sep.join(parts[:-1])

            if parent not in dir_files:
                dir_files[parent] = []
            dir_files[parent].append(parts[-1])

        # 生成树
        visited_dirs = set()

        for d in sorted(self._dirs):
            depth = get_depth(d)
            if depth > max_depth:
                continue

            indent = '  ' * depth
            name = os.path.basename(d)
            lines.append(f"{indent}{name}/")
            visited_dirs.add(d)

            # 显示该目录下的文件
            if d in dir_files:
                for f in sorted(dir_files[d])[:max_files_per_dir]:
                    lines.append(f"{indent}  {f}")
                if len(dir_files[d]) > max_files_per_dir:
                    lines.append(f"{indent}  ... ({len(dir_files[d]) - max_files_per_dir} more)")

        # 根目录文件
        if '' in dir_files:
            indent = '  '
            for f in sorted(dir_files[''])[:max_files_per_dir]:
                lines.append(f"{indent}{f}")

        return '\n'.join(lines[:100])  # 限制行数

    def _find_entry_files(self) -> List[str]:
        """查找入口文件"""
        entries = []
        for pattern in ENTRY_PATTERNS:
            for f in self._files:
                if f.endswith(pattern) or os.path.basename(f) == pattern:
                    entries.append(f)

        # 去重并限制数量
        return list(dict.fromkeys(entries))[:10]

    def _collect_config_files(self) -> List[Dict[str, Any]]:
        """收集配置文件"""
        configs = []

        for pattern in CONFIG_PATTERNS:
            for f in self._files:
                if os.path.basename(f) == pattern:
                    full_path = self.project_dir / f
                    config = {
                        'path': f,
                        'type': pattern,
                        'size': self._get_file_size(f),
                    }

                    # 读取内容预览
                    try:
                        content = full_path.read_text(encoding='utf-8', errors='ignore')
                        config['content_preview'] = content[:500]
                    except Exception:
                        pass

                    configs.append(config)

        return configs[:20]

    def _parse_repo_manifest(self) -> List[Dict[str, Any]]:
        """解析 Repo manifest.xml"""
        manifest_path = self.project_dir / '.repo' / 'manifest.xml'
        sub_projects = []

        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()

            for project in root.findall('.//project'):
                name = project.get('name', '')
                path = project.get('path', name)
                revision = project.get('revision', '')

                # 根据路径推断类型
                proj_type = 'unknown'
                path_lower = path.lower()
                if 'freertos' in path_lower:
                    proj_type = 'freertos'
                elif 'rtos' in path_lower:
                    proj_type = 'rtos'
                elif 'sdk' in path_lower:
                    proj_type = 'sdk'
                elif 'driver' in path_lower or 'drivers' in path_lower:
                    proj_type = 'driver'
                elif 'bsp' in path_lower:
                    proj_type = 'bsp'
                elif 'project' in path_lower:
                    proj_type = 'app'
                elif 'component' in path_lower:
                    proj_type = 'component'
                elif 'tool' in path_lower:
                    proj_type = 'tool'

                sub_projects.append({
                    'name': name,
                    'path': path,
                    'revision': revision,
                    'type': proj_type,
                    'description': '',  # AI 填充
                })

        except Exception as e:
            print(f"  警告: 解析 manifest.xml 失败: {e}")

        return sub_projects

    def _detect_modules(self) -> List[Dict[str, Any]]:
        """识别模块"""
        modules = []

        # 常见模块目录名
        module_patterns = [
            'src', 'lib', 'app', 'core', 'internal', 'cmd',
            'components', 'modules', 'packages', 'services',
            'drivers', 'hal', 'bsp', 'kernel', 'frameworks',
            'utils', 'tools', 'tests', 'docs', 'examples',
            'api', 'web', 'mobile', 'desktop', 'embedded',
        ]

        # 扫描目录
        for d in self._dirs:
            name = os.path.basename(d)

            # 检查是否是模块目录
            if name.lower() in module_patterns:
                # 统计该目录下的文件
                dir_files = [f for f in self._files if f.startswith(d + os.sep)]
                file_count = len(dir_files)

                # 统计语言
                languages = set()
                for f in dir_files:
                    ext = os.path.splitext(f)[1]
                    for lang, exts in SOURCE_EXTENSIONS.items():
                        if ext in exts:
                            languages.add(lang)

                modules.append({
                    'name': name,
                    'path': d,
                    'description': '',  # AI 填充
                    'file_count': file_count,
                    'languages': list(languages),
                })

        # 按文件数排序，取前 15 个
        modules.sort(key=lambda m: m['file_count'], reverse=True)
        return modules[:15]

    def _parse_dependencies(self) -> List[Dict[str, str]]:
        """解析依赖"""
        dependencies = []

        # requirements.txt
        req_path = self.project_dir / 'requirements.txt'
        if req_path.exists():
            try:
                content = req_path.read_text(encoding='utf-8')
                for line in content.strip().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 解析包名和版本
                        if '==' in line:
                            name, version = line.split('==', 1)
                        elif '>=' in line:
                            name, version = line.split('>=', 1)
                            version = f'>={version}'
                        else:
                            name, version = line, ''

                        dependencies.append({
                            'name': name.strip(),
                            'version': version.strip(),
                            'type': 'python',
                        })
            except Exception:
                pass

        # package.json
        pkg_path = self.project_dir / 'package.json'
        if pkg_path.exists():
            try:
                content = pkg_path.read_text(encoding='utf-8')
                data = json.loads(content)

                for dep_type in ['dependencies', 'devDependencies']:
                    deps = data.get(dep_type, {})
                    for name, version in deps.items():
                        dependencies.append({
                            'name': name,
                            'version': version,
                            'type': 'npm',
                            'dev': dep_type == 'devDependencies',
                        })
            except Exception:
                pass

        return dependencies[:30]

    def _get_file_size(self, rel_path: str) -> int:
        """获取文件大小"""
        try:
            return (self.project_dir / rel_path).stat().st_size
        except Exception:
            return 0

    def save(self, output_path: str):
        """保存数据到 JSON"""
        data = self.collect()

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(asdict(data), indent=2, ensure_ascii=False), encoding='utf-8')

        print(f"\n数据已保存到: {output}")
        return data


def main():
    import argparse

    parser = argparse.ArgumentParser(description='项目数据收集器')
    parser.add_argument('project_dir', help='项目目录')
    parser.add_argument('--output', '-o', default='.projmeta/structured_data.json', help='输出文件路径')

    args = parser.parse_args()

    collector = ProjectCollector(args.project_dir)
    collector.save(args.output)


if __name__ == '__main__':
    main()