#!/usr/bin/env python3
"""
Java 项目分析器
专门用于 Java 项目的深度分析

特性：
- Maven/Gradle 依赖解析
- Spring 框架识别
- JUnit 测试检测
- 代码结构分析
"""

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field

try:
    from .base_analyzer import BaseAnalyzer
except ImportError:
    from base_analyzer import BaseAnalyzer


@dataclass
class JavaDependency:
    """Java 依赖"""
    group_id: str
    artifact_id: str
    version: str
    scope: str = "compile"
    source: str = ""  # maven/gradle


@dataclass
class JavaClass:
    """Java 类信息"""
    name: str
    package: str
    file_path: str
    is_interface: bool = False
    is_abstract: bool = False
    annotations: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    fields: List[str] = field(default_factory=list)


class JavaAnalyzer(BaseAnalyzer):
    """Java 项目分析器"""

    # Spring 框架注解
    SPRING_ANNOTATIONS = {
        'Controller', 'RestController', 'Service', 'Repository', 'Component',
        'Configuration', 'Bean', 'Autowired', 'RequestMapping', 'GetMapping',
        'PostMapping', 'PutMapping', 'DeleteMapping', 'PatchMapping',
        'SpringBootApplication', 'EnableAutoConfiguration', 'ComponentScan',
    }

    # JUnit 注解
    JUNIT_ANNOTATIONS = {
        'Test', 'BeforeEach', 'AfterEach', 'BeforeAll', 'AfterAll',
        'Disabled', 'RepeatedTest', 'ParameterizedTest', 'TestFactory',
    }

    # 常用框架检测
    FRAMEWORK_INDICATORS = {
        'spring-boot': {'SpringBootApplication', '@EnableAutoConfiguration'},
        'spring-mvc': {'Controller', 'RestController', 'RequestMapping'},
        'spring-data': {'Repository', 'Entity', 'Id', 'Column'},
        'spring-security': {'EnableWebSecurity', 'SecurityConfig'},
        'mybatis': {'Mapper', 'Select', 'Insert', 'Update', 'Delete'},
        'jpa': {'Entity', 'Table', 'Column', 'Id'},
        'lombok': {'Data', 'Getter', 'Setter', 'Builder', 'AllArgsConstructor'},
    }

    def __init__(self, project_dir: str):
        super().__init__(project_dir)
        self.dependencies: List[JavaDependency] = []
        self.classes: List[JavaClass] = []
        self.frameworks: Set[str] = set()

    def analyze(self) -> Dict[str, Any]:
        """执行分析"""
        self._detect_frameworks()
        self._parse_dependencies()
        self._analyze_source_files()
        self._detect_test_files()

        return {
            'project_type': self._detect_project_type(),
            'build_system': self._detect_build_system(),
            'frameworks': list(self.frameworks),
            'dependencies': {
                'count': len(self.dependencies),
                'list': [d.__dict__ for d in self.dependencies[:20]],
            },
            'classes': {
                'count': len(self.classes),
                'list': [{'name': c.name, 'package': c.package} for c in self.classes[:20]],
            },
            'structure': self._analyze_structure(),
            'tests': self._get_test_info(),
        }

    def _detect_project_type(self) -> str:
        """检测项目类型"""
        project_path = Path(self.project_dir)

        # Spring Boot
        if (project_path / 'pom.xml').exists():
            try:
                tree = ET.parse(project_path / 'pom.xml')
                root = tree.getroot()
                ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

                # 查找 Spring Boot parent
                parent = root.find('.//m:parent/m:artifactId', ns)
                if parent is not None and 'spring-boot' in parent.text:
                    return 'spring-boot'
            except Exception:
                pass

        # Gradle 项目
        if (project_path / 'build.gradle').exists() or (project_path / 'build.gradle.kts').exists():
            return 'gradle-java'

        # Maven 项目
        if (project_path / 'pom.xml').exists():
            return 'maven'

        return 'java'

    def _detect_build_system(self) -> str:
        """检测构建系统"""
        project_path = Path(self.project_dir)

        if (project_path / 'pom.xml').exists():
            return 'maven'
        elif (project_path / 'build.gradle.kts').exists():
            return 'gradle-kotlin'
        elif (project_path / 'build.gradle').exists():
            return 'gradle'
        elif (project_path / 'settings.gradle').exists():
            return 'gradle'

        return 'unknown'

    def _detect_frameworks(self) -> None:
        """检测使用的框架"""
        project_path = Path(self.project_dir)

        # 检查依赖文件
        pom_file = project_path / 'pom.xml'
        if pom_file.exists():
            self._detect_frameworks_from_pom(pom_file)

        gradle_file = project_path / 'build.gradle'
        if gradle_file.exists():
            self._detect_frameworks_from_gradle(gradle_file)

        # 检查源代码注解
        self._detect_frameworks_from_source()

    def _detect_frameworks_from_pom(self, pom_file: Path) -> None:
        """从 pom.xml 检测框架"""
        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()
            ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

            # 查找依赖
            for dep in root.findall('.//m:dependency', ns):
                group_id = dep.find('m:groupId', ns)
                if group_id is not None:
                    group = group_id.text or ''
                    if 'spring' in group:
                        self.frameworks.add('spring')
                    if 'mybatis' in group:
                        self.frameworks.add('mybatis')
                    if 'lombok' in group:
                        self.frameworks.add('lombok')
                    if 'junit' in group:
                        self.frameworks.add('junit')
                    if 'mockito' in group:
                        self.frameworks.add('mockito')

        except Exception:
            pass

    def _detect_frameworks_from_gradle(self, gradle_file: Path) -> None:
        """从 build.gradle 检测框架"""
        try:
            content = gradle_file.read_text(encoding='utf-8')

            if 'spring' in content.lower():
                self.frameworks.add('spring')
            if 'mybatis' in content.lower():
                self.frameworks.add('mybatis')
            if 'lombok' in content.lower():
                self.frameworks.add('lombok')
            if 'junit' in content.lower():
                self.frameworks.add('junit')

        except Exception:
            pass

    def _detect_frameworks_from_source(self) -> None:
        """从源代码检测框架"""
        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if d not in {'target', 'build', '.gradle', '.idea'}]

            for f in files:
                if f.endswith('.java'):
                    file_path = Path(root) / f
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')

                        # 检查 Spring 注解
                        for ann in self.SPRING_ANNOTATIONS:
                            if f'@{ann}' in content or f'@org.springframework.{ann}' in content:
                                self.frameworks.add('spring')

                        # 检查其他框架
                        if '@Mapper' in content or '@Select' in content:
                            self.frameworks.add('mybatis')
                        if '@Data' in content or '@Builder' in content:
                            self.frameworks.add('lombok')
                        if '@Test' in content:
                            self.frameworks.add('junit')

                    except Exception:
                        continue

    def _parse_dependencies(self) -> None:
        """解析依赖"""
        project_path = Path(self.project_dir)

        # 解析 pom.xml
        pom_file = project_path / 'pom.xml'
        if pom_file.exists():
            self._parse_pom_dependencies(pom_file)

        # 解析 build.gradle
        gradle_file = project_path / 'build.gradle'
        if gradle_file.exists():
            self._parse_gradle_dependencies(gradle_file)

    def _parse_pom_dependencies(self, pom_file: Path) -> None:
        """解析 pom.xml 依赖"""
        try:
            tree = ET.parse(pom_file)
            root = tree.getroot()
            ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

            for dep in root.findall('.//m:dependency', ns):
                group_id = dep.find('m:groupId', ns)
                artifact_id = dep.find('m:artifactId', ns)
                version = dep.find('m:version', ns)
                scope = dep.find('m:scope', ns)

                if group_id is not None and artifact_id is not None:
                    self.dependencies.append(JavaDependency(
                        group_id=group_id.text or '',
                        artifact_id=artifact_id.text or '',
                        version=version.text if version is not None else '',
                        scope=scope.text if scope is not None else 'compile',
                        source='maven',
                    ))

        except Exception:
            pass

    def _parse_gradle_dependencies(self, gradle_file: Path) -> None:
        """解析 build.gradle 依赖"""
        try:
            content = gradle_file.read_text(encoding='utf-8')

            # 简单匹配: implementation 'group:artifact:version'
            pattern = r"(?:implementation|api|compileOnly|runtimeOnly|testImplementation)\s+['\"]([^'\"]+)['\"]"
            for match in re.finditer(pattern, content):
                parts = match.group(1).split(':')
                if len(parts) >= 2:
                    self.dependencies.append(JavaDependency(
                        group_id=parts[0],
                        artifact_id=parts[1],
                        version=parts[2] if len(parts) > 2 else '',
                        source='gradle',
                    ))

        except Exception:
            pass

    def _analyze_source_files(self) -> None:
        """分析源文件"""
        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if d not in {'target', 'build', '.gradle', '.idea', 'test', 'tests'}]

            for f in files:
                if f.endswith('.java'):
                    self._analyze_java_file(Path(root) / f)

    def _analyze_java_file(self, file_path: Path) -> None:
        """分析单个 Java 文件"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')

            # 提取包名
            package = ""
            package_match = re.search(r'package\s+([\w.]+);', content)
            if package_match:
                package = package_match.group(1)

            # 提取类名
            class_match = re.search(r'(?:public\s+)?(?:abstract\s+)?(?:class|interface|enum)\s+(\w+)', content)
            if class_match:
                class_name = class_match.group(1)
                is_interface = 'interface ' in content
                is_abstract = 'abstract class' in content

                # 提取注解
                annotations = []
                for ann_match in re.finditer(r'@(\w+)', content[:class_match.start()]):
                    annotations.append(ann_match.group(1))

                # 提取方法名
                methods = []
                for method_match in re.finditer(r'(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)+(\w+)\s*\(', content):
                    methods.append(method_match.group(1))

                self.classes.append(JavaClass(
                    name=class_name,
                    package=package,
                    file_path=str(file_path.relative_to(self.project_dir)),
                    is_interface=is_interface,
                    is_abstract=is_abstract,
                    annotations=annotations,
                    methods=methods[:20],
                ))

        except Exception:
            pass

    def _analyze_structure(self) -> Dict[str, Any]:
        """分析项目结构"""
        structure = {
            'src_main_java': False,
            'src_test_java': False,
            'src_main_resources': False,
            'packages': set(),
        }

        project_path = Path(self.project_dir)

        # 检查标准目录结构
        if (project_path / 'src' / 'main' / 'java').exists():
            structure['src_main_java'] = True
        if (project_path / 'src' / 'test' / 'java').exists():
            structure['src_test_java'] = True
        if (project_path / 'src' / 'main' / 'resources').exists():
            structure['src_main_resources'] = True

        # 收集包名
        for cls in self.classes:
            if cls.package:
                structure['packages'].add(cls.package.rsplit('.', 1)[0])

        structure['packages'] = list(structure['packages'])[:20]

        return structure

    def _detect_test_files(self) -> None:
        """检测测试文件"""
        self.test_files = []

        for root, dirs, files in os.walk(self.project_dir):
            if 'test' in root.lower() or 'tests' in root.lower():
                for f in files:
                    if f.endswith('.java') and ('Test' in f or 'test' in f):
                        self.test_files.append(str(Path(root) / f))

    def _get_test_info(self) -> Dict[str, Any]:
        """获取测试信息"""
        return {
            'test_files_count': len(getattr(self, 'test_files', [])),
            'has_unit_tests': len(getattr(self, 'test_files', [])) > 0,
        }

    def find_spring_controllers(self) -> List[Dict[str, str]]:
        """查找 Spring Controller"""
        controllers = []

        for cls in self.classes:
            if any(ann in self.SPRING_ANNOTATIONS for ann in cls.annotations):
                if 'Controller' in cls.annotations or 'RestController' in cls.annotations:
                    controllers.append({
                        'name': cls.name,
                        'package': cls.package,
                        'file': cls.file_path,
                    })

        return controllers

    def find_spring_services(self) -> List[Dict[str, str]]:
        """查找 Spring Service"""
        services = []

        for cls in self.classes:
            if 'Service' in cls.annotations:
                services.append({
                    'name': cls.name,
                    'package': cls.package,
                    'file': cls.file_path,
                })

        return services

    def find_spring_repositories(self) -> List[Dict[str, str]]:
        """查找 Spring Repository"""
        repositories = []

        for cls in self.classes:
            if 'Repository' in cls.annotations:
                repositories.append({
                    'name': cls.name,
                    'package': cls.package,
                    'file': cls.file_path,
                })

        return repositories


def main():
    """命令行接口"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: java_analyzer.py <project_dir>")
        sys.exit(1)

    project_dir = sys.argv[1]
    analyzer = JavaAnalyzer(project_dir)
    result = analyzer.analyze()

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()