#!/usr/bin/env python3
"""
TypeScript 项目分析器
专门用于 TypeScript/JavaScript 项目的深度分析

特性：
- package.json 依赖解析
- 框架检测 (React, Vue, Angular, Next.js 等)
- 组件分析
- 构建工具识别
"""

import os
import re
import json as json_module
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field

try:
    from .base_analyzer import BaseAnalyzer
except ImportError:
    from base_analyzer import BaseAnalyzer


@dataclass
class JSDependency:
    """JavaScript/TypeScript 依赖"""
    name: str
    version: str
    is_dev: bool = False
    source: str = ""


class TypeScriptAnalyzer(BaseAnalyzer):
    """TypeScript 项目分析器"""

    # 前端框架
    FRONTEND_FRAMEWORKS = {
        'react': ['react', 'react-dom', 'React', 'jsx', 'tsx'],
        'vue': ['vue', 'Vue', '.vue'],
        'angular': ['@angular/core', 'angular', 'ngOnInit'],
        'svelte': ['svelte', '.svelte'],
        'solid': ['solid-js', 'Solid'],
        'preact': ['preact', 'Preact'],
    }

    # 元框架
    META_FRAMEWORKS = {
        'next.js': ['next', 'Next.js', '_app', '_document', 'getServerSideProps'],
        'nuxt': ['nuxt', 'Nuxt'],
        'remix': ['remix', '@remix-run'],
        'astro': ['astro', '.astro'],
        'gatsby': ['gatsby'],
    }

    # 后端框架
    BACKEND_FRAMEWORKS = {
        'express': ['express', 'Express'],
        'nestjs': ['@nestjs/core', '@nestjs/common', 'NestFactory'],
        'fastify': ['fastify', 'Fastify'],
        'hono': ['hono', 'Hono'],
        'koa': ['koa', 'Koa'],
    }

    # 测试框架
    TEST_FRAMEWORKS = {
        'jest': ['jest', '@types/jest', 'describe(', 'it('],
        'vitest': ['vitest', '@vitest'],
        'mocha': ['mocha', 'chai'],
        'cypress': ['cypress', 'cy.'],
        'playwright': ['playwright', '@playwright'],
    }

    # 构建工具
    BUILD_TOOLS = {
        'vite': ['vite', 'vite.config'],
        'webpack': ['webpack', 'webpack.config'],
        'rollup': ['rollup', 'rollup.config'],
        'esbuild': ['esbuild'],
        'turbo': ['turbo', 'turbo.json'],
        'nx': ['nx', 'nx.json'],
    }

    def __init__(self, project_dir: str):
        super().__init__(project_dir)
        self.dependencies: List[JSDependency] = []
        self.dev_dependencies: List[JSDependency] = []
        self.frameworks: Set[str] = set()
        self.test_frameworks: Set[str] = set()
        self.build_tools: Set[str] = set()
        self.package_json: Dict[str, Any] = {}

    def analyze(self) -> Dict[str, Any]:
        """执行分析"""
        self._load_package_json()
        self._detect_frameworks()
        self._parse_dependencies()
        self._analyze_structure()

        return {
            'project_type': self._detect_project_type(),
            'language': self._detect_language(),
            'frameworks': list(self.frameworks),
            'test_frameworks': list(self.test_frameworks),
            'build_tools': list(self.build_tools),
            'dependencies': {
                'production': len(self.dependencies),
                'development': len(self.dev_dependencies),
            },
            'scripts': self._get_scripts(),
            'structure': self._get_structure_info(),
            'entry_points': self._find_entry_points(),
        }

    def _load_package_json(self) -> None:
        """加载 package.json"""
        package_path = Path(self.project_dir) / 'package.json'

        if package_path.exists():
            try:
                with open(package_path, 'r', encoding='utf-8') as f:
                    self.package_json = json_module.load(f)
            except Exception:
                self.package_json = {}

    def _detect_project_type(self) -> str:
        """检测项目类型"""
        deps = set(self.package_json.get('dependencies', {}).keys())
        dev_deps = set(self.package_json.get('devDependencies', {}).keys())
        all_deps = deps | dev_deps

        # 元框架优先
        for framework, indicators in self.META_FRAMEWORKS.items():
            for indicator in indicators:
                if indicator in all_deps or indicator in str(self.package_json):
                    return framework

        # 前端框架
        for framework, indicators in self.FRONTEND_FRAMEWORKS.items():
            for indicator in indicators:
                if indicator in all_deps:
                    return framework

        # 后端框架
        for framework, indicators in self.BACKEND_FRAMEWORKS.items():
            for indicator in indicators:
                if indicator in all_deps:
                    return f'{framework}-api'

        # 纯 TypeScript/JavaScript
        if 'typescript' in dev_deps:
            return 'typescript'
        return 'javascript'

    def _detect_language(self) -> str:
        """检测语言"""
        project_path = Path(self.project_dir)

        # 检查 tsconfig.json
        if (project_path / 'tsconfig.json').exists():
            return 'typescript'

        # 检查文件扩展名
        ts_count = 0
        js_count = 0

        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in {'node_modules', 'dist', 'build', '.next', '.nuxt'}]

            for f in files:
                if f.endswith('.ts') or f.endswith('.tsx'):
                    ts_count += 1
                elif f.endswith('.js') or f.endswith('.jsx'):
                    js_count += 1

        if ts_count > js_count:
            return 'typescript'
        elif js_count > 0:
            return 'javascript'

        return 'unknown'

    def _detect_frameworks(self) -> None:
        """检测框架"""
        deps = self.package_json.get('dependencies', {})
        dev_deps = self.package_json.get('devDependencies', {})
        all_deps = set(deps.keys()) | set(dev_deps.keys())

        # 检测前端框架
        for framework, indicators in self.FRONTEND_FRAMEWORKS.items():
            for indicator in indicators:
                if indicator in all_deps:
                    self.frameworks.add(framework)
                    break

        # 检测元框架
        for framework, indicators in self.META_FRAMEWORKS.items():
            for indicator in indicators:
                if indicator in all_deps or indicator in all_deps:
                    self.frameworks.add(framework)
                    break

        # 检测后端框架
        for framework, indicators in self.BACKEND_FRAMEWORKS.items():
            for indicator in indicators:
                if indicator in all_deps:
                    self.frameworks.add(framework)
                    break

        # 检测测试框架
        for framework, indicators in self.TEST_FRAMEWORKS.items():
            for indicator in indicators:
                if indicator in all_deps:
                    self.test_frameworks.add(framework)
                    break

        # 检测构建工具
        for tool, indicators in self.BUILD_TOOLS.items():
            for indicator in indicators:
                if indicator in all_deps:
                    self.build_tools.add(tool)
                    break

        # 检查配置文件
        project_path = Path(self.project_dir)
        if (project_path / 'vite.config.ts').exists() or (project_path / 'vite.config.js').exists():
            self.build_tools.add('vite')
        if (project_path / 'webpack.config.js').exists():
            self.build_tools.add('webpack')
        if (project_path / 'rollup.config.js').exists():
            self.build_tools.add('rollup')

    def _parse_dependencies(self) -> None:
        """解析依赖"""
        deps = self.package_json.get('dependencies', {})
        dev_deps = self.package_json.get('devDependencies', {})

        for name, version in deps.items():
            self.dependencies.append(JSDependency(
                name=name,
                version=version,
                is_dev=False,
                source='package.json',
            ))

        for name, version in dev_deps.items():
            self.dev_dependencies.append(JSDependency(
                name=name,
                version=version,
                is_dev=True,
                source='package.json',
            ))

    def _get_scripts(self) -> Dict[str, str]:
        """获取 npm scripts"""
        return self.package_json.get('scripts', {})

    def _analyze_structure(self) -> None:
        """分析项目结构"""
        project_path = Path(self.project_dir)

        self.has_src = (project_path / 'src').exists()
        self.has_public = (project_path / 'public').exists()
        self.has_components = (project_path / 'src' / 'components').exists()
        self.has_pages = (project_path / 'src' / 'pages').exists() or (project_path / 'pages').exists()
        self.has_api = (project_path / 'src' / 'api').exists() or (project_path / 'api').exists()
        self.has_tests = (project_path / '__tests__').exists() or (project_path / 'tests').exists()
        self.has_cypress = (project_path / 'cypress').exists()
        self.has_e2e = (project_path / 'e2e').exists()

    def _get_structure_info(self) -> Dict[str, Any]:
        """获取结构信息"""
        return {
            'src': getattr(self, 'has_src', False),
            'components': getattr(self, 'has_components', False),
            'pages': getattr(self, 'has_pages', False),
            'api': getattr(self, 'has_api', False),
            'tests': getattr(self, 'has_tests', False),
        }

    def _find_entry_points(self) -> List[str]:
        """查找入口点"""
        entry_points = []
        project_path = Path(self.project_dir)

        candidates = [
            'src/main.tsx', 'src/main.ts', 'src/index.tsx', 'src/index.ts',
            'src/main.jsx', 'src/main.js', 'src/index.jsx', 'src/index.js',
            'main.tsx', 'main.ts', 'index.tsx', 'index.ts',
            'main.jsx', 'main.js', 'index.jsx', 'index.js',
            'src/app.tsx', 'src/app.ts', 'src/App.tsx', 'src/App.ts',
            'pages/index.tsx', 'pages/index.ts',
        ]

        for candidate in candidates:
            if (project_path / candidate).exists():
                entry_points.append(candidate)

        return entry_points

    def find_react_components(self) -> List[Dict[str, str]]:
        """查找 React 组件"""
        components = []
        project_path = Path(self.project_dir)

        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in {'node_modules', 'dist', 'build', '.next'}]

            for f in files:
                if f.endswith('.tsx') or f.endswith('.jsx'):
                    file_path = Path(root) / f

                    # 检查是否是组件目录
                    if 'component' in str(file_path).lower():
                        components.append({
                            'name': f.replace('.tsx', '').replace('.jsx', ''),
                            'path': str(file_path.relative_to(project_path)),
                        })

        return components[:20]

    def find_api_routes(self) -> List[Dict[str, str]]:
        """查找 API 路由"""
        routes = []
        project_path = Path(self.project_dir)

        # Next.js API routes
        api_dir = project_path / 'pages' / 'api'
        if api_dir.exists():
            for f in api_dir.rglob('*'):
                if f.suffix in ('.ts', '.js'):
                    route_path = str(f.relative_to(api_dir)).replace('\\', '/')
                    route_path = route_path.replace('.ts', '').replace('.js', '')
                    if route_path != 'index':
                        route_path = '/' + route_path.replace('/index', '')
                    else:
                        route_path = '/'
                    routes.append({
                        'path': f'/api{route_path}',
                        'file': str(f.relative_to(project_path)),
                        'type': 'next-api',
                    })

        # NestJS controllers
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in {'node_modules', 'dist'}]

            for f in files:
                if f.endswith('.controller.ts'):
                    file_path = Path(root) / f
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        for match in re.finditer(r'@(?:Get|Post|Put|Delete|Patch)\(["\']?([^"\')\s]*)', content):
                            routes.append({
                                'path': match.group(1) or '/',
                                'file': str(file_path.relative_to(project_path)),
                                'type': 'nestjs',
                            })
                    except Exception:
                        continue

        return routes

    def get_recommended_commands(self) -> Dict[str, str]:
        """获取推荐命令"""
        scripts = self._get_scripts()
        commands = {}

        # 安装
        if (Path(self.project_dir) / 'pnpm-lock.yaml').exists():
            commands['install'] = 'pnpm install'
        elif (Path(self.project_dir) / 'yarn.lock').exists():
            commands['install'] = 'yarn'
        else:
            commands['install'] = 'npm install'

        # 开发
        if 'dev' in scripts:
            commands['dev'] = 'npm run dev'
        elif 'start' in scripts:
            commands['dev'] = 'npm start'

        # 构建
        if 'build' in scripts:
            commands['build'] = 'npm run build'

        # 测试
        if 'test' in scripts:
            commands['test'] = 'npm test'

        return commands


def main():
    """命令行接口"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: typescript_analyzer.py <project_dir>")
        sys.exit(1)

    project_dir = sys.argv[1]
    analyzer = TypeScriptAnalyzer(project_dir)
    result = analyzer.analyze()

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()