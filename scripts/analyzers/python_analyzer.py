#!/usr/bin/env python3
"""
Python 项目分析器
专门用于 Python 项目的深度分析

特性：
- 依赖解析 (requirements.txt, pyproject.toml, setup.py)
- 虚拟环境检测
- 测试框架检测
- 代码结构分析
"""

import os
import re
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field

try:
    from .base_analyzer import BaseAnalyzer
except ImportError:
    from base_analyzer import BaseAnalyzer


@dataclass
class PythonDependency:
    """Python 依赖"""
    name: str
    version: str = ""
    source: str = ""  # requirements/pyproject/setup


class PythonAnalyzer(BaseAnalyzer):
    """Python 项目分析器"""

    # Web 框架指示器
    WEB_FRAMEWORKS = {
        'django': ['django', 'settings.py', 'urls.py', 'wsgi.py'],
        'flask': ['flask', 'app = Flask', 'from flask import'],
        'fastapi': ['fastapi', 'from fastapi import', 'FastAPI()'],
        'tornado': ['tornado', 'from tornado import'],
        'sanic': ['sanic', 'from sanic import'],
        'aiohttp': ['aiohttp', 'from aiohttp import'],
    }

    # 测试框架指示器
    TEST_FRAMEWORKS = {
        'pytest': ['pytest', 'test_', 'conftest.py'],
        'unittest': ['unittest', 'TestCase'],
        'nose': ['nose', 'nosetests'],
    }

    # 数据科学库
    DATA_SCIENCE_LIBS = {
        'pandas', 'numpy', 'scipy', 'matplotlib', 'seaborn',
        'scikit-learn', 'tensorflow', 'torch', 'keras',
    }

    def __init__(self, project_dir: str):
        super().__init__(project_dir)
        self.dependencies: List[PythonDependency] = []
        self.frameworks: Set[str] = set()
        self.test_frameworks: Set[str] = set()

    def analyze(self) -> Dict[str, Any]:
        """执行分析"""
        self._detect_frameworks()
        self._parse_dependencies()
        self._analyze_structure()

        return {
            'project_type': self._detect_project_type(),
            'python_version': self._detect_python_version(),
            'frameworks': list(self.frameworks),
            'test_frameworks': list(self.test_frameworks),
            'dependencies': {
                'count': len(self.dependencies),
                'list': [{'name': d.name, 'version': d.version} for d in self.dependencies[:20]],
            },
            'structure': self._get_structure_info(),
            'entry_points': self._find_entry_points(),
        }

    def _detect_project_type(self) -> str:
        """检测项目类型"""
        project_path = Path(self.project_dir)

        # Web 框架
        if (project_path / 'manage.py').exists():
            return 'django'
        if (project_path / 'app.py').exists() or (project_path / 'main.py').exists():
            # 检查是否是 Flask/FastAPI
            for f in ['app.py', 'main.py']:
                file_path = project_path / f
                if file_path.exists():
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        if 'FastAPI' in content:
                            return 'fastapi'
                        if 'Flask' in content:
                            return 'flask'
                    except Exception:
                        pass

        # 数据科学
        requirements = project_path / 'requirements.txt'
        if requirements.exists():
            try:
                content = requirements.read_text(encoding='utf-8').lower()
                if any(lib in content for lib in self.DATA_SCIENCE_LIBS):
                    return 'data-science'
            except Exception:
                pass

        # CLI 工具
        if (project_path / 'setup.py').exists() or (project_path / 'pyproject.toml').exists():
            return 'python-package'

        return 'python'

    def _detect_python_version(self) -> Optional[str]:
        """检测 Python 版本要求"""
        project_path = Path(self.project_dir)

        # 检查 pyproject.toml
        pyproject = project_path / 'pyproject.toml'
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding='utf-8')
                match = re.search(r'python\s*=\s*["\']?([^"\']+)["\']?', content)
                if match:
                    return match.group(1)
            except Exception:
                pass

        # 检查 setup.py
        setup_py = project_path / 'setup.py'
        if setup_py.exists():
            try:
                content = setup_py.read_text(encoding='utf-8')
                match = re.search(r'python_requires\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    return match.group(1)
            except Exception:
                pass

        # 检查 .python-version
        version_file = project_path / '.python-version'
        if version_file.exists():
            try:
                return version_file.read_text(encoding='utf-8').strip()
            except Exception:
                pass

        return None

    def _detect_frameworks(self) -> None:
        """检测使用的框架"""
        project_path = Path(self.project_dir)

        # 检查依赖文件
        requirements = project_path / 'requirements.txt'
        if requirements.exists():
            self._detect_frameworks_from_requirements(requirements)

        # 检查源代码
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in {'.venv', 'venv', 'env', '__pycache__', '.git', 'node_modules'}]

            for f in files:
                if f.endswith('.py'):
                    file_path = Path(root) / f
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        self._detect_frameworks_from_content(content)
                    except Exception:
                        continue

    def _detect_frameworks_from_requirements(self, requirements_path: Path) -> None:
        """从 requirements.txt 检测框架"""
        try:
            content = requirements_path.read_text(encoding='utf-8').lower()

            for framework in self.WEB_FRAMEWORKS:
                if framework in content:
                    self.frameworks.add(framework)

            for framework in self.TEST_FRAMEWORKS:
                if framework in content:
                    self.test_frameworks.add(framework)

        except Exception:
            pass

    def _detect_frameworks_from_content(self, content: str) -> None:
        """从源代码检测框架"""
        content_lower = content.lower()

        for framework, indicators in self.WEB_FRAMEWORKS.items():
            for indicator in indicators:
                if indicator.lower() in content_lower:
                    self.frameworks.add(framework)
                    break

        for framework, indicators in self.TEST_FRAMEWORKS.items():
            for indicator in indicators:
                if indicator.lower() in content_lower:
                    self.test_frameworks.add(framework)
                    break

    def _parse_dependencies(self) -> None:
        """解析依赖"""
        project_path = Path(self.project_dir)

        # 解析 requirements.txt
        requirements = project_path / 'requirements.txt'
        if requirements.exists():
            self._parse_requirements(requirements)

        # 解析 pyproject.toml
        pyproject = project_path / 'pyproject.toml'
        if pyproject.exists():
            self._parse_pyproject(pyproject)

        # 解析 setup.py
        setup_py = project_path / 'setup.py'
        if setup_py.exists():
            self._parse_setup_py(setup_py)

    def _parse_requirements(self, requirements_path: Path) -> None:
        """解析 requirements.txt"""
        try:
            content = requirements_path.read_text(encoding='utf-8')

            for line in content.split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # 解析包名和版本
                match = re.match(r'^([a-zA-Z0-9_-]+)\s*([<>=!]+.*)?$', line)
                if match:
                    self.dependencies.append(PythonDependency(
                        name=match.group(1),
                        version=match.group(2) or '',
                        source='requirements',
                    ))

        except Exception:
            pass

    def _parse_pyproject(self, pyproject_path: Path) -> None:
        """解析 pyproject.toml"""
        try:
            content = pyproject_path.read_text(encoding='utf-8')

            # 简单解析 [project.dependencies]
            in_deps = False
            for line in content.split('\n'):
                line = line.strip()

                if line == '[project.dependencies]' or line == '[project.optional-dependencies]':
                    in_deps = True
                    continue

                if line.startswith('['):
                    in_deps = False
                    continue

                if in_deps and line and not line.startswith('#'):
                    match = re.match(r'^([a-zA-Z0-9_-]+)\s*([<>=!]+.*)?$', line)
                    if match:
                        self.dependencies.append(PythonDependency(
                            name=match.group(1),
                            version=match.group(2) or '',
                            source='pyproject',
                        ))

        except Exception:
            pass

    def _parse_setup_py(self, setup_path: Path) -> None:
        """解析 setup.py"""
        try:
            content = setup_path.read_text(encoding='utf-8')

            # 查找 install_requires
            match = re.search(r'install_requires\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if match:
                deps_content = match.group(1)
                for dep_match in re.finditer(r'["\']([^"\']+)["\']', deps_content):
                    dep = dep_match.group(1)
                    parts = re.match(r'^([a-zA-Z0-9_-]+)\s*([<>=!]+.*)?$', dep)
                    if parts:
                        self.dependencies.append(PythonDependency(
                            name=parts.group(1),
                            version=parts.group(2) or '',
                            source='setup.py',
                        ))

        except Exception:
            pass

    def _analyze_structure(self) -> None:
        """分析项目结构"""
        project_path = Path(self.project_dir)

        self.has_src_layout = (project_path / 'src').exists()
        self.has_tests = (project_path / 'tests').exists() or (project_path / 'test').exists()
        self.has_docs = (project_path / 'docs').exists()
        self.has_config = (project_path / 'config').exists()

        # 收集模块
        self.modules = []
        for item in project_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                if (item / '__init__.py').exists():
                    self.modules.append(item.name)

    def _get_structure_info(self) -> Dict[str, Any]:
        """获取结构信息"""
        return {
            'src_layout': getattr(self, 'has_src_layout', False),
            'has_tests': getattr(self, 'has_tests', False),
            'has_docs': getattr(self, 'has_docs', False),
            'modules': getattr(self, 'modules', [])[:10],
        }

    def _find_entry_points(self) -> List[str]:
        """查找入口点"""
        entry_points = []
        project_path = Path(self.project_dir)

        candidates = ['main.py', 'app.py', 'run.py', '__main__.py', 'manage.py', 'wsgi.py', 'asgi.py']

        for candidate in candidates:
            file_path = project_path / candidate
            if file_path.exists():
                entry_points.append(candidate)

        # 检查 src 目录
        src_path = project_path / 'src'
        if src_path.exists():
            for candidate in candidates:
                file_path = src_path / candidate
                if file_path.exists():
                    entry_points.append(f'src/{candidate}')

        return entry_points

    def find_django_apps(self) -> List[str]:
        """查找 Django 应用"""
        apps = []
        project_path = Path(self.project_dir)

        for item in project_path.iterdir():
            if item.is_dir():
                if (item / 'models.py').exists() and (item / 'views.py').exists():
                    apps.append(item.name)

        return apps

    def find_fastapi_routes(self) -> List[Dict[str, str]]:
        """查找 FastAPI 路由"""
        routes = []
        project_path = Path(self.project_dir)

        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in {'.venv', 'venv', '__pycache__'}]

            for f in files:
                if f.endswith('.py'):
                    file_path = Path(root) / f
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')

                        # 查找路由装饰器
                        for match in re.finditer(r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', content, re.IGNORECASE):
                            routes.append({
                                'method': match.group(1).upper(),
                                'path': match.group(2),
                                'file': str(file_path.relative_to(project_path)),
                            })

                    except Exception:
                        continue

        return routes


def main():
    """命令行接口"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python_analyzer.py <project_dir>")
        sys.exit(1)

    project_dir = sys.argv[1]
    analyzer = PythonAnalyzer(project_dir)
    result = analyzer.analyze()

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()