# Project Assistant 开发者文档

> 本文档详细介绍 project-assistant 的架构设计、模块功能和 API 接口。

---

## 目录

- [架构概览](#架构概览)
- [核心模块](#核心模块)
- [项目检测器](#项目检测器)
- [配置文件解析器](#配置文件解析器)
- [代码分析器](#代码分析器)
- [配置管理](#配置管理)
- [缓存系统](#缓存系统)
- [问答文档管理](#问答文档管理)
- [飞书集成](#飞书集成)
- [调用链分析](#调用链分析)
- [安全体系](#安全体系)
- [文件监控与增量更新](#文件监控与增量更新)
- [智能问答增强](#智能问答增强)
- [AST 代码分析](#ast-代码分析)
- [项目识别与模板](#项目识别与模板)
- [创新功能](#创新功能)
- [v3.0 企业级功能](#v30-企业级功能)
- [API 参考](#api-参考)
- [扩展开发](#扩展开发)

---

## 架构概览

### 设计原则

1. **本地计算优先** - 所有分析在本地完成，只有精简摘要发送给 LLM
2. **增量更新** - 只处理变更文件，避免全量扫描
3. **安全第一** - 敏感信息自动脱敏，审计日志可追溯
4. **Token 高效** - 分层文档架构，按需加载

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         用户请求                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     安全网关 (Phase 0)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ 敏感信息扫描    │  │ 内容自动脱敏    │  │ 审计日志记录 ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     文件监控层 (Phase 1)                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ 文件变更检测    │  │ Git 变更追踪    │  │ 增量缓存更新 ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      分析引擎层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ 项目检测器  │  │ AST 解析器  │  │ 调用链分析器        │ │
│  │ (detector)  │  │ (tree-sitter)│  │ (call_chain)       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ 语义匹配器  │  │ 知识图谱    │  │ 依赖分析器          │ │
│  │ (BM25)      │  │ (knowledge) │  │ (dependency)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ 配置解析器  │  │ 代码分析器  │  │ 问答管理器          │ │
│  │ (parsers)   │  │ (analyzers) │  │ (qa_doc)            │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      输出层                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ 项目文档        │  │ 问答缓存        │  │ 图表生成     ││
│  │ (.projmeta/)    │  │ (qa_cache.json) │  │ (Mermaid)    ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## 核心模块

### 目录结构

```
project-assistant/
├── SKILL.md                    # Skill 主入口
├── README.md                   # 项目说明
├── DOCS.md                     # 开发者文档（本文件）
├── config.json                 # 跨会话配置
├── security-config.yaml        # 安全配置
│
├── scripts/
│   ├── cli.py                  # 统一 CLI 入口 ⭐
│   ├── detector.py             # 项目类型探测器
│   ├── config_manager.py       # 配置管理器
│   ├── qa_doc_manager.py       # 问答文档管理
│   ├── feishu_doc_manager.py   # 飞书集成
│   ├── validate_output.py      # 输出校验
│   │
│   ├── # 核心增强模块
│   ├── watcher.py              # 文件监控器
│   ├── knowledge_graph.py      # 知识图谱
│   ├── qa_recommender.py       # 问答推荐
│   ├── ast_parser.py           # AST 解析器
│   ├── template_engine.py      # 模板引擎
│   ├── diagram_generator.py    # 图表生成
│   ├── dependency_analyzer.py  # 依赖分析
│   ├── ai_analyzer.py          # AI 增强
│   │
│   ├── # v3.0 企业级模块
│   ├── indexer/                # 分层索引器
│   │   ├── lazy_indexer.py     # 延迟索引
│   │   └── memory_manager.py   # 内存管理
│   ├── multi_repo/             # 多仓库管理
│   │   ├── mono_manager.py     # Monorepo 管理
│   │   └── repo_linker.py      # 仓库关联
│   ├── team/                   # 团队协作
│   │   ├── team_knowledge.py   # 团队知识库
│   │   ├── team_db.py          # 团队数据库
│   │   ├── permission_manager.py # 权限管理
│   │   └── collaboration.py    # 问答协作
│   ├── integration/            # 企业集成
│   │   ├── ci_cd.py            # CI/CD 集成
│   │   ├── issue_tracker.py    # Issue 集成
│   │   ├── code_review.py      # 代码审查
│   │   └── webhook_server.py   # Webhook 服务
│   ├── ai/                     # AI 能力
│   │   ├── vector_store.py     # 向量检索
│   │   ├── code_completion.py  # 代码补全
│   │   ├── refactoring_advisor.py # 重构建议
│   │   └── quality_predictor.py # 质量预测
│   │
│   ├── security/               # 安全模块
│   │   ├── sensitive_scanner.py
│   │   ├── security_config.py
│   │   └── audit_logger.py
│   │
│   ├── parsers/                # 配置文件解析器
│   │   ├── base_parser.py
│   │   ├── android_native_parser.py
│   │   ├── cicd_parser.py
│   │   ├── cmake_parser.py
│   │   ├── device_tree_parser.py
│   │   ├── go_parser.py
│   │   ├── gradle_parser.py
│   │   ├── kernel_config_parser.py
│   │   ├── linker_parser.py
│   │   ├── manifest_parser.py
│   │   ├── maven_parser.py
│   │   ├── package_json_parser.py
│   │   ├── python_parser.py
│   │   ├── rtos_parser.py
│   │   └── rust_parser.py
│   │
│   ├── analyzers/              # 代码分析器
│   │   ├── base_analyzer.py
│   │   ├── c_analyzer.py
│   │   ├── env_scanner.py
│   │   ├── ipc_analyzer.py
│   │   ├── test_analyzer.py
│   │   ├── todo_extractor.py
│   │   ├── java_analyzer.py
│   │   ├── python_analyzer.py
│   │   └── typescript_analyzer.py
│   │
│   └── utils/
│       ├── cache_manager.py    # 缓存管理
│       ├── call_chain_analyzer.py
│       ├── git_info.py
│       ├── git_watcher.py
│       ├── qa_cache.py
│       ├── doc_generator.py
│       ├── file_utils.py
│       ├── output.py
│       ├── project_query.py
│       └── logger.py
│
├── references/
│   ├── templates/              # 项目模板
│   │   ├── project-template.md
│   │   ├── embedded/
│   │   │   ├── mcu.md
│   │   │   ├── rtos.md
│   │   │   ├── linux.md
│   │   │   ├── qnx.md
│   │   │   └── android-native.md
│   │   ├── mobile/
│   │   │   ├── android.md
│   │   │   └── ios.md
│   │   ├── web/
│   │   │   ├── frontend.md
│   │   │   └── backend.md
│   │   ├── desktop/
│   │   │   └── desktop.md
│   │   └── system/
│   │       └── native.md
│   ├── guides/                 # 使用指南
│   │   ├── config.md
│   │   ├── init.md
│   │   ├── qa.md
│   │   ├── feishu.md
│   │   └── examples.md
│   └── template-config.yaml    # 模板配置
│
└── tests/                      # 测试套件
```

---

## 项目检测器

### 概述

项目检测器是整个系统的入口，负责快速识别项目类型、语言、构建系统等信息。

**文件**: `scripts/detector.py`

### 核心类

```python
class ProjectDetector:
    """项目类型探测器"""

    # 项目类型识别规则
    RULES = [
        # Android (高优先级)
        ProjectTypeRule(['AndroidManifest.xml'], 'android-app', 'kotlin', 100, 'gradle'),
        ProjectTypeRule(['build.gradle', 'app/src/main'], 'android-app', 'kotlin', 90, 'gradle'),

        # iOS
        ProjectTypeRule(['*.xcodeproj'], 'ios', 'swift', 100, 'xcode'),

        # Embedded MCU
        ProjectTypeRule(['*.ioc'], 'stm32', 'c', 95, 'stm32cubeide'),
        ProjectTypeRule(['*.uvprojx'], 'keil', 'c', 95, 'keil'),

        # Web Frontend
        ProjectTypeRule(['package.json', 'src/index.tsx'], 'react', 'typescript', 85, 'npm'),

        # Web Backend
        ProjectTypeRule(['manage.py', 'settings.py'], 'django', 'python', 95, 'pip'),
    ]
```

### 使用方法

```python
from detector import ProjectDetector

# 创建检测器
detector = ProjectDetector('/path/to/project')

# 执行检测
result = detector.detect()

# 结果包含
print(result['project_type'])      # 项目类型
print(result['language'])          # 主要语言
print(result['build_system'])      # 构建系统
print(result['entry_points'])      # 入口点文件
print(result['config_files'])      # 配置文件
print(result['modules'])           # 模块目录
print(result['dependencies'])      # 依赖信息
print(result['scale'])             # 项目规模 (small/medium/large)
print(result['subsystems'])        # 子系统列表
print(result['processes'])         # 进程列表
print(result['ipc_protocols'])     # IPC 协议
```

### 检测能力

| 检测项 | 说明 |
|--------|------|
| 项目类型 | 支持 60+ 种项目类型 |
| 语言识别 | 基于文件扩展名和内容分析 |
| 构建系统 | 识别 Maven、Gradle、npm、pip 等 |
| 入口点 | 查找 main.c、index.ts 等入口文件 |
| 配置文件 | 收集所有关键配置文件 |
| 依赖提取 | 从 package.json、pom.xml 等提取依赖 |
| 项目规模 | 小型/中型/大型项目判断 |
| 子系统检测 | 识别大型项目的子系统 |
| 进程检测 | 通过 main 文件推断进程 |
| IPC 协议 | 检测 Binder、DBus、gRPC 等 |

### 命令行使用

```bash
# 检测项目
python3 scripts/detector.py /path/to/project

# 详细输出
python3 scripts/detector.py /path/to/project --verbose

# 强制刷新缓存
python3 scripts/detector.py /path/to/project --force
```

---

## 配置文件解析器

### 概述

配置文件解析器负责解析各种项目配置文件，提取依赖、脚本、环境配置等信息。

**目录**: `scripts/parsers/`

### 基类

**文件**: `scripts/parsers/base_parser.py`

```python
class BaseParser:
    """解析器基类"""

    def parse(self, file_path: str) -> Dict[str, Any]:
        """解析配置文件

        Returns:
            {
                'dependencies': List[Dict],
                'scripts': Dict[str, str],
                'config': Dict[str, Any],
                'metadata': Dict[str, Any]
            }
        """
        raise NotImplementedError
```

### 支持的配置文件

| 解析器 | 文件 | 支持的配置 |
|--------|------|-----------|
| `package_json_parser.py` | package.json | npm/yarn 项目 |
| `python_parser.py` | requirements.txt, pyproject.toml | Python 项目 |
| `maven_parser.py` | pom.xml | Maven 项目 |
| `gradle_parser.py` | build.gradle, build.gradle.kts | Gradle 项目 |
| `cmake_parser.py` | CMakeLists.txt | CMake 项目 |
| `rust_parser.py` | Cargo.toml | Rust 项目 |
| `go_parser.py` | go.mod | Go 项目 |
| `android_native_parser.py` | Android.mk, Android.bp | Android NDK |
| `manifest_parser.py` | AndroidManifest.xml | Android 应用 |
| `rtos_parser.py` | FreeRTOSConfig.h, rtconfig.h | RTOS 项目 |
| `kernel_config_parser.py` | Kconfig, defconfig | 内核配置 |
| `device_tree_parser.py` | *.dts, *.dtsi | 设备树 |
| `linker_parser.py` | *.ld | 链接脚本 |
| `cicd_parser.py` | .gitlab-ci.yml, Jenkinsfile | CI/CD 配置 |

### 使用示例

#### package.json 解析器

```python
from parsers.package_json_parser import PackageJsonParser

parser = PackageJsonParser()
result = parser.parse('/path/to/package.json')

print(result['dependencies'])
# [{'name': 'react', 'version': '^18.0.0', 'type': 'production'}, ...]

print(result['scripts'])
# {'start': 'vite', 'build': 'vite build', ...}

print(result['dev_dependencies'])
# [{'name': 'typescript', 'version': '^5.0.0'}, ...]
```

#### Maven 解析器

```python
from parsers.maven_parser import MavenParser

parser = MavenParser()
result = parser.parse('/path/to/pom.xml')

print(result['group_id'])      # com.example
print(result['artifact_id'])   # my-app
print(result['version'])       # 1.0.0
print(result['dependencies'])  # 依赖列表
print(result['modules'])       # 多模块项目
```

#### Gradle 解析器

```python
from parsers.gradle_parser import GradleParser

parser = GradleParser()
result = parser.parse('/path/to/build.gradle')

print(result['android'])        # Android 配置
print(result['dependencies'])   # 依赖列表
print(result['plugins'])        # 插件列表
print(result['build_types'])    # buildTypes
```

#### CMake 解析器

```python
from parsers.cmake_parser import CMakeParser

parser = CMakeParser()
result = parser.parse('/path/to/CMakeLists.txt')

print(result['project_name'])    # 项目名称
print(result['cmake_minimum'])   # CMake 版本要求
print(result['sources'])         # 源文件列表
print(result['dependencies'])    # 依赖库
print(result['targets'])         # 构建目标
```

---

## 代码分析器

### 概述

代码分析器对源代码进行深度分析，提取函数、类、注释、TODO 等结构化信息。

**目录**: `scripts/analyzers/`

### 基类

**文件**: `scripts/analyzers/base_analyzer.py`

```python
class BaseAnalyzer:
    """分析器基类"""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir

    def analyze(self) -> Dict[str, Any]:
        """执行分析，返回结构化结果"""
        raise NotImplementedError

    def get_summary(self) -> str:
        """返回分析摘要"""
        raise NotImplementedError
```

### 内置分析器

#### C 语言分析器

**文件**: `scripts/analyzers/c_analyzer.py`

```python
from analyzers.c_analyzer import CAnalyzer

analyzer = CAnalyzer('/path/to/project')
result = analyzer.analyze()

# 结果包含
print(result['functions'])     # 函数列表
print(result['includes'])      # #include 列表
print(result['macros'])        # 宏定义
print(result['structs'])       # 结构体定义
print(result['enums'])         # 枚举定义
print(result['globals'])       # 全局变量
print(result['todos'])         # TODO 注释
```

#### 测试分析器

**文件**: `scripts/analyzers/test_analyzer.py`

```python
from analyzers.test_analyzer import TestAnalyzer

analyzer = TestAnalyzer('/path/to/project')
result = analyzer.analyze()

print(result['test_files'])      # 测试文件列表
print(result['test_cases'])      # 测试用例
print(result['coverage_info'])   # 覆盖率信息
print(result['test_framework'])  # 测试框架
```

#### TODO 提取器

**文件**: `scripts/analyzers/todo_extractor.py`

```python
from analyzers.todo_extractor import TODOExtractor

extractor = TODOExtractor('/path/to/project')
result = extractor.analyze()

# 提取的 TODO 项
for todo in result['todos']:
    print(f"{todo['file']}:{todo['line']}")
    print(f"  Type: {todo['type']}")  # TODO, FIXME, XXX, HACK
    print(f"  Content: {todo['content']}")
    print(f"  Priority: {todo['priority']}")
```

#### IPC 分析器

**文件**: `scripts/analyzers/ipc_analyzer.py`

```python
from analyzers.ipc_analyzer import IPCAnalyzer

analyzer = IPCAnalyzer('/path/to/project')
result = analyzer.analyze()

print(result['ipc_types'])      # ['binder', 'dbus', 'grpc']
print(result['interfaces'])     # IPC 接口定义
print(result['endpoints'])      # 端点信息
print(result['calls'])          # IPC 调用关系
```

#### 环境扫描器

**文件**: `scripts/analyzers/env_scanner.py`

```python
from analyzers.env_scanner import EnvScanner

scanner = EnvScanner('/path/to/project')
result = scanner.scan()

print(result['env_files'])      # 环境变量文件
print(result['variables'])      # 环境变量定义
print(result['secrets'])        # 潜在的敏感信息
print(result['configs'])        # 配置项
```

---

## 配置管理

### 概述

配置管理器提供跨会话的个性化配置存储，支持群聊、单聊共享配置。

**文件**: `scripts/config_manager.py`

### 功能特性

- 跨会话持久化存储
- 支持嵌套键名 (如 `preferences.language`)
- 自动类型转换
- 配置项验证

### 使用方法

```python
from config_manager import ConfigManager

manager = ConfigManager('/path/to/project')

# 设置配置
manager.set('workdir', '/home/user/projects/my-project')
manager.set('build_command', 'make all')
manager.set('preferences.language', 'zh')
manager.set('custom.board_type', 'bk7258')

# 获取配置
workdir = manager.get('workdir')
language = manager.get('preferences.language', default='en')

# 显示所有配置
all_config = manager.show()

# 删除配置
manager.delete('custom.board_type')

# 清空所有配置
manager.clear()
```

### 预定义配置项

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `workdir` | 工作目录 | `/home/user/projects/my-project` |
| `build_command` | 构建命令 | `make all` |
| `run_command` | 运行命令 | `./myapp` |
| `test_command` | 测试命令 | `pytest tests/` |
| `preferences.language` | 偏好语言 | `zh` / `en` |
| `preferences.output_format` | 输出格式 | `markdown` / `json` |
| `custom.*` | 自定义配置 | 任意键值对 |

### 命令行使用

```bash
# 设置配置
python3 scripts/config_manager.py /path/to/skill set workdir /home/user/project

# 获取配置
python3 scripts/config_manager.py /path/to/skill get workdir

# 显示所有配置
python3 scripts/config_manager.py /path/to/skill show

# 删除配置
python3 scripts/config_manager.py /path/to/skill delete custom.key
```

---

## 缓存系统

### 概述

缓存系统负责管理项目分析结果，支持 TTL 过期、Git 状态检测、增量更新。

**文件**: `scripts/utils/cache_manager.py`

### 缓存结构

```python
@dataclass
class CacheEntry:
    """缓存条目"""
    version: str = "1.0"
    timestamp: str = ""
    project_hash: str = ""
    file_hashes: Dict[str, str] = field(default_factory=dict)
    git_status: Dict[str, Any] = field(default_factory=dict)
    analysis_cache: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    scale: str = "small"
    subsystems: List[str] = field(default_factory=list)
    modules: List[str] = field(default_factory=list)
    processes: List[str] = field(default_factory=list)
    ipc_protocols: List[str] = field(default_factory=list)
```

### 使用方法

```python
from utils.cache_manager import CacheManager

manager = CacheManager('/path/to/project')

# 加载缓存
cache = manager.load()

# 检查缓存有效性
validity = manager.check_validity(quick=False)
print(validity['is_valid'])
print(validity['reason'])
print(validity['changed_files'])

# 更新缓存
manager.update(analysis_data={'key': 'value'})

# 增量更新
manager.incremental_update(['src/main.py', 'src/utils.py'])

# 使相关缓存失效
invalidated = manager.invalidate_by_files(['src/auth.py'])

# 获取 Git 状态
git_status = manager.get_git_status()

# 计算文件哈希
file_hash = manager.compute_file_hash('/path/to/file')
```

### 缓存策略

| 策略 | 说明 |
|------|------|
| TTL 过期 | 默认 24 小时 |
| Git 状态检测 | 有未提交变更时更新 |
| 配置文件变更 | package.json 等被修改时更新 |
| 提交变化 | HEAD commit 改变时更新 |
| 文件哈希比较 | 关键文件哈希变化时更新 |

### 命令行使用

```bash
# 检查缓存有效性
python3 scripts/utils/cache_manager.py check /path/to/project

# 快速检查
python3 scripts/utils/cache_manager.py check /path/to/project --quick

# 更新缓存
python3 scripts/utils/cache_manager.py update /path/to/project

# 清除缓存
python3 scripts/utils/cache_manager.py clear /path/to/project

# 清理过期缓存
python3 scripts/utils/cache_manager.py cleanup /home/user
```

---

## 问答文档管理

### 概述

问答文档管理器自动将问答沉淀为 Markdown 文档，支持分类归档、过期检测。

**文件**: `scripts/qa_doc_manager.py`

### 功能特性

- 自动生成 Markdown 文档
- 按 8 种分类自动归档
- 记录 Git commit hash
- 检测文档过期
- 相似问题搜索

### 文档分类

| 分类 | 标签 | 说明 |
|------|------|------|
| 架构 | architecture | 架构设计相关 |
| 构建 | build | 构建、编译、部署 |
| 功能 | feature | 功能实现说明 |
| 调试 | debug | 问题排查、调试 |
| API | api | 接口文档 |
| 配置 | config | 配置说明 |
| 测试 | test | 测试相关 |
| 其他 | other | 其他问题 |

### 使用方法

```python
from qa_doc_manager import QADocManager

manager = QADocManager('/path/to/project')

# 创建问答文档
manager.create(
    question="登录功能是怎么实现的？",
    answer="通过 AuthService + JwtUtil 实现...",
    file_refs=["src/auth.py", "src/api/auth.py"],
    tags=["feature", "auth"]
)

# 搜索问答
results = manager.search("登录")
for r in results:
    print(f"ID: {r['id']}")
    print(f"问题: {r['question']}")
    print(f"分类: {r['category']}")

# 列出所有问答
all_qa = manager.list(category='feature')

# 检查过期
outdated = manager.check_outdated()

# 删除问答
manager.delete('20260311_120000_登录功能是怎么实现的')

# 获取统计
stats = manager.get_stats()
```

### 文档结构

```
.projmeta/
└── docs/
    └── qa/
        ├── architecture/
        │   └── 20260311_120000_项目架构说明.md
        ├── feature/
        │   ├── 20260311_130000_登录功能是怎么实现的.md
        │   └── 20260311_140000_支付流程说明.md
        └── debug/
            └── 20260311_150000_WiFi连接失败怎么办.md
```

### 文档格式

每个问答文档包含：

```markdown
# 问题：登录功能是怎么实现的？

**分类**: feature
**创建时间**: 2026-03-11 13:00:00
**相关文件**: src/auth.py, src/api/auth.py
**Commit**: 1e5c122

---

## 答案

通过 `AuthService` + `JwtUtil` 实现：

1. 前端提交 → `LoginApi.login()`
2. 后端验证 → `AuthService.authenticate()`
3. Token生成 → `JwtUtil.createToken()`

相关代码：
- `src/pages/Login.tsx:45-78`
- `src/api/auth.ts:23-56`
```

### 命令行使用

```bash
# 搜索问答
python3 scripts/qa_doc_manager.py /path/to/project search "登录"

# 列出问答
python3 scripts/qa_doc_manager.py /path/to/project list feature

# 检查过期
python3 scripts/qa_doc_manager.py /path/to/project check

# 删除问答
python3 scripts/qa_doc_manager.py /path/to/project delete <id>
```

---

## 飞书集成

### 概述

飞书集成模块用于与飞书 Skill 协作，生成文档更新建议报告。

**文件**: `scripts/feishu_doc_manager.py`

### 功能特性

- 分析项目变更，生成更新建议
- 按优先级分类（高/中/低）
- 不直接修改文档，只生成建议
- 与飞书 Skill 协作

### 使用方法

```python
from feishu_doc_manager import FeishuDocManager

manager = FeishuDocManager('/path/to/project')

# 生成更新报告
report = manager.generate_update_report()
print(report['high_priority'])   # 高优先级更新
print(report['medium_priority']) # 中优先级更新
print(report['low_priority'])    # 低优先级更新

# 检查同步状态
status = manager.check_sync_status()
print(status['synced'])
print(status['outdated'])

# 生成单个文件建议
suggestion = manager.generate_suggestion(
    file_path='src/auth.py',
    doc_type='feature'
)
```

### 更新建议格式

```python
{
    "high_priority": [
        {
            "file": "src/auth.py",
            "reason": "核心认证逻辑已修改",
            "suggestion": "更新登录流程说明",
            "related_docs": ["docs/auth.md"]
        }
    ],
    "medium_priority": [...],
    "low_priority": [...]
}
```

### 命令行使用

```bash
# 生成更新报告
python3 scripts/feishu_doc_manager.py /path/to/project report

# 检查同步状态
python3 scripts/feishu_doc_manager.py /path/to/project status

# 生成单个文件建议
python3 scripts/feishu_doc_manager.py /path/to/project suggest src/auth.py feature
```

---

## 调用链分析

### 概述

调用链分析器分析函数/方法的调用关系，支持多种编程语言。

**文件**: `scripts/utils/call_chain_analyzer.py`

### 支持的语言

- Python
- JavaScript / TypeScript
- Java
- C / C++
- Go
- Rust

### 使用方法

```python
from utils.call_chain_analyzer import CallChainAnalyzer

analyzer = CallChainAnalyzer('/path/to/project')

# 执行分析
result = analyzer.analyze()
print(f"发现 {result['summary']['total_functions']} 个函数")
print(f"分析耗时: {result['summary']['analysis_time']}")

# 查找函数
locations = analyzer.find_function('login')

# 获取调用链
chain = analyzer.get_call_chain(
    func_name='login',
    depth=3,
    direction='both'  # 'calls', 'called_by', 'both'
)

# 影响分析
impact = analyzer.get_impact_analysis('login')
print(impact['direct_callers'])   # 直接调用者
print(impact['test_callers'])     # 测试调用者
print(impact['total_impact'])     # 总影响数
```

### 输出格式

```python
# 调用链示例
{
    'function': 'login',
    'definitions': [
        {'file': 'src/auth.py', 'line': 23, 'end_line': 45}
    ],
    'calls': [
        {
            'function': 'authenticate',
            'file': 'src/api/auth.py',
            'line': 12,
            'children': [...]
        }
    ],
    'called_by': [
        {
            'function': 'handleLogin',
            'file': 'src/pages/Login.tsx',
            'line': 45,
            'parents': [...]
        }
    ]
}
```

### 命令行使用

```bash
# 分析项目
python3 scripts/utils/call_chain_analyzer.py /path/to/project

# 获取调用链
python3 scripts/utils/call_chain_analyzer.py /path/to/project login --depth=3

# 影响分析
python3 scripts/utils/call_chain_analyzer.py /path/to/project login --impact
```

---

## 安全体系

### 安全体系

### 敏感信息扫描器

项目内置完整的安全体系，保护敏感信息。

#### 敏感信息扫描器

**文件**: `scripts/security/sensitive_scanner.py`

```python
from security import SensitiveScanner, scan_project

# 扫描项目
scanner = SensitiveScanner()
result = scanner.scan('/path/to/project')

# 结果
print(result.sensitive_files)  # 敏感文件列表
print(result.matches)          # 敏感内容匹配

# 脱敏处理
masked_content = scanner.mask_content('password = "secret123"')
# 输出: password = "***MASKED***"
```

**检测能力**:
- 敏感文件: `.env`, `*.pem`, `*.key`, `credentials.json` 等
- 敏感内容: 密码、API Key、Token、私钥等
- 云服务凭证: AWS, Azure, GCP

#### 安全配置

**文件**: `security-config.yaml`

```yaml
sensitive:
  exclude_files:
    - '.env*'
    - '*.pem'
    - 'credentials.json'

  on_sensitive_found: warn  # warn | error | ignore

audit:
  enabled: true
  log_file: .projmeta/audit.log
  log_level: info
```

#### 审计日志

**文件**: `scripts/security/audit_logger.py`

```python
from security import AuditLogger

logger = AuditLogger('/path/to/project')

# 记录操作
logger.log_operation('scan', {'files': 100, 'time': '2.5s'})
logger.log_sensitive_access('.env', 'read', masked=True)

# 查询审计记录
trail = logger.get_audit_trail({'operation': 'scan'})
```

---

## 文件监控与增量更新

### 文件监控器

**文件**: `scripts/watcher.py`

```python
from watcher import ProjectWatcher

def on_change(batch):
    print(f"检测到 {batch.file_count} 个文件变更")
    for change in batch.changes:
        print(f"  - {change.change_type.value}: {change.file_path}")

watcher = ProjectWatcher('/path/to/project', callback=on_change)
watcher.start()

# 或获取变更文件（同步方式）
changes = watcher.get_changed_files()
```

**特性**:
- 基于 watchdog 实时监控
- 智能过滤（排除 node_modules、.git 等）
- 防抖处理，避免频繁触发
- 回调机制，支持自定义处理

#### Git 变更检测

**文件**: `scripts/utils/git_watcher.py`

```python
from utils.git_watcher import GitWatcher

watcher = GitWatcher('/path/to/project')

# 获取未提交变更
changes = watcher.get_uncommitted_changes()
for change in changes:
    print(f"{change.change_type.value}: {change.file_path}")

# 获取提交间差异
diff = watcher.get_diff_files('HEAD~5', 'HEAD')

# 获取文件差异内容
file_diff = watcher.get_file_diff('src/main.py')
```

---

## 智能问答增强

### 语义相似度匹配

**文件**: `scripts/utils/qa_cache.py`

```python
from utils.qa_cache import QACacheManager, SemanticMatcher

# 问答缓存
qa = QACacheManager('/path/to/project')

# 查找相似问题（支持语义匹配）
entry = qa.get("登录怎么实现")
# 可匹配: "登录功能如何实现", "如何实现登录" 等

# 语义匹配器
matcher = SemanticMatcher(use_jieba=True)
matcher.build_index(["登录怎么实现", "如何进行用户认证"])
results = matcher.search("登录功能", top_k=3)
```

**算法**:
- BM25 排序算法
- Jieba 中文分词
- TF-IDF 回退方案

#### 知识图谱

**文件**: `scripts/knowledge_graph.py`

```python
from knowledge_graph import KnowledgeGraph

graph = KnowledgeGraph('/path/to/project')

# 添加问答
graph.add_qa('q001', '登录功能怎么实现？')

# 关联代码
graph.link_qa_to_code('q001', [
    {'file_path': 'src/auth.py', 'symbol': 'login'},
])

# 检查问答是否过期
result = graph.check_qa_outdated('q001')

# 影响分析
impact = graph.get_impact_analysis(['src/auth.py'])
```

#### 智能推荐

**文件**: `scripts/qa_recommender.py`

```python
from qa_recommender import QARecommender

recommender = QARecommender('/path/to/project')

# 基于上下文推荐
recommendations = recommender.recommend_by_context('src/auth.py')

# 综合推荐
all_recs = recommender.get_recommendations(
    current_file='src/auth.py',
    user_id='user1'
)
```

---

## AST 代码分析

### AST 解析器

**文件**: `scripts/ast_parser.py`

```python
from ast_parser import ASTParser

parser = ASTParser()

# 解析单个文件
result = parser.parse('src/main.py')

print(result.functions)  # 函数列表
print(result.classes)    # 类列表
print(result.imports)    # 导入列表

# 解析整个项目
project_result = parser.parse_project('/path/to/project')
```

**支持语言**: Python, JavaScript/TypeScript, Java, C/C++, Go, Rust

#### 语言专用分析器

**Java 分析器** (`scripts/analyzers/java_analyzer.py`):

```python
from analyzers.java_analyzer import JavaAnalyzer

analyzer = JavaAnalyzer('/path/to/java/project')
result = analyzer.analyze()

controllers = analyzer.find_spring_controllers()
services = analyzer.find_spring_services()
```

**Python 分析器** (`scripts/analyzers/python_analyzer.py`):

```python
from analyzers.python_analyzer import PythonAnalyzer

analyzer = PythonAnalyzer('/path/to/python/project')
apps = analyzer.find_django_apps()
routes = analyzer.find_fastapi_routes()
```

**TypeScript 分析器** (`scripts/analyzers/typescript_analyzer.py`):

```python
from analyzers.typescript_analyzer import TypeScriptAnalyzer

analyzer = TypeScriptAnalyzer('/path/to/ts/project')
components = analyzer.find_react_components()
routes = analyzer.find_api_routes()
```

---

## 项目识别与模板

### 项目类型配置

**文件**: `references/template-config.yaml`

支持 60+ 项目类型识别。

#### 模板引擎

**文件**: `scripts/template_engine.py`

```python
from template_engine import TemplateEngine

engine = TemplateEngine()

# 渲染模板
content = engine.render('embedded/mcu.md', {
    'MCU': 'STM32F407',
    'ARCH': 'ARM Cortex-M4',
})

# 模板继承
combined = engine.extend('child.md', 'parent.md')

# 匹配项目类型
matched = engine.match_project_type(files, dirs)
```

---

## 创新功能

### 图表生成器

**文件**: `scripts/diagram_generator.py`

```python
from diagram_generator import DiagramGenerator

generator = DiagramGenerator()

# 架构图
arch = generator.generate_architecture_diagram({
    'modules': ['auth', 'api', 'database'],
})

# 时序图
seq = generator.generate_sequence_diagram([...])

# 依赖图、ER图、类图等
```

#### 依赖分析器

**文件**: `scripts/dependency_analyzer.py`

```python
from dependency_analyzer import DependencyAnalyzer

analyzer = DependencyAnalyzer('/path/to/project')
result = analyzer.analyze()

print(result['circular_dependencies'])
print(result['version_conflicts'])
```

#### AI 增强分析

**文件**: `scripts/ai_analyzer.py`

```python
from ai_analyzer import AIAnalyzer

analyzer = AIAnalyzer()
result = analyzer.analyze_file('src/main.py')

print(result['quality'])       # 质量分数
print(result['issues'])        # 安全问题
print(result['code_smells'])   # 代码异味
```

---

## v3.0 企业级功能

### 分层延迟索引器

**文件**: `scripts/indexer/lazy_indexer.py`

```python
from indexer.lazy_indexer import LazyIndexer

indexer = LazyIndexer('/path/to/project')

# 获取 L0 快速索引 (< 1s)
l0 = indexer.get_l0_index()
print(l0.files)  # 文件列表

# 获取 L1 结构索引 (< 5s)
l1 = indexer.get_l1_index()
print(l1.functions)  # 函数定义

# 预热 L2 语义索引 (后台)
indexer.warmup_l2(priority_files=['src/main.py'])
```

**分层架构**:
- L0 快速索引：文件元数据，< 1 秒
- L1 结构索引：函数/类定义，< 5 秒
- L2 语义索引：调用图、向量嵌入，< 30 秒
- L3 深度索引：全量 AST、质量分析，后台运行

### 多仓库管理器

**文件**: `scripts/multi_repo/mono_manager.py`

```python
from multi_repo.mono_manager import MonoRepoManager

manager = MonoRepoManager('/path/to/monorepo')

# 添加仓库
manager.add_repo('frontend', '../frontend', 'react')
manager.add_repo('backend', '../backend', 'spring-boot')

# 跨仓库搜索
results = manager.cross_repo_search('登录功能')

# 获取仓库依赖图
dep_graph = manager.get_dep_graph()
```

### 团队知识库

**文件**: `scripts/team/team_knowledge.py`

```python
from team.team_knowledge import TeamKnowledgeBase

kb = TeamKnowledgeBase('/path/to/project')

# 分享问答到团队
kb.share_qa('q001', 'backend-team')

# 导入团队知识
qa_list = kb.import_team_qa('backend-team')

# 合并知识库
kb.merge_qa('source_team', 'target_team')
```

### CI/CD 集成

**文件**: `scripts/integration/ci_cd.py`

```python
from integration.ci_cd import CICDIntegration

ci = CICDIntegration('/path/to/project')

# PR 创建时触发
report = ci.on_pr_created(pr_info)

# 生成分析报告
report = ci.generate_report(format='markdown')
```

### 向量检索引擎

**文件**: `scripts/ai/vector_store.py`

```python
from ai.vector_store import VectorStore

store = VectorStore('/path/to/project')

# 构建索引
store.build_index()

# 语义搜索
results = store.search_code('用户认证流程', top_k=10)
```

### 重构顾问

**文件**: `scripts/ai/refactoring_advisor.py`

```python
from ai.refactoring_advisor import RefactoringAdvisor

advisor = RefactoringAdvisor('/path/to/project')

# 分析重构建议
suggestions = advisor.analyze('src/auth.py')

# 生成报告
report = advisor.get_refactoring_report()
```

### 质量预测器

**文件**: `scripts/ai/quality_predictor.py`

```python
from ai.quality_predictor import QualityPredictor

predictor = QualityPredictor('/path/to/project')

# 预测风险
assessment = predictor.predict_risk('src/auth.py')
print(assessment.score)  # 风险评分 0-100
print(assessment.level)  # low/medium/high/critical

# 项目风险摘要
summary = predictor.get_project_risk_summary()
```

---

## API 参考

### 配置管理 API

```python
class ConfigManager:
    def get(self, key: str) -> Any
    def set(self, key: str, value: Any) -> None
    def delete(self, key: str) -> bool
    def show(self) -> Dict[str, Any]
```

### 项目检测 API

```python
class ProjectDetector:
    def detect(self) -> Dict[str, Any]
    def get_subskill_path(self) -> Optional[str]
    def clear_cache(cls) -> None
```

### 缓存管理 API

```python
class CacheManager:
    def load(self) -> CacheEntry
    def save(self) -> None
    def check_validity(self, quick: bool = False) -> Dict[str, Any]
    def update(self, analysis_data: Dict = None, incremental: bool = False) -> CacheEntry
    def incremental_update(self, changed_files: List[str]) -> CacheEntry
    def invalidate_by_files(self, files: List[str]) -> List[str]
```

### 问答缓存 API

```python
class QACacheManager:
    def get(self, question: str) -> Optional[QACacheEntry]
    def set(self, question: str, answer: str, **kwargs) -> None
    def find_similar(self, question: str) -> Optional[Tuple]
    def invalidate_files(self, changed_files: List[str]) -> int
```

### 安全 API

```python
class SensitiveScanner:
    def scan(self, project_dir: str) -> ScanResult
    def mask_content(self, content: str) -> str
    def should_exclude(self, file: str) -> bool

class AuditLogger:
    def log_operation(self, operation: str, details: Dict) -> None
    def log_sensitive_access(self, file: str, action: str) -> None
    def get_audit_trail(self, filters: Dict) -> List[LogEntry]
```

---

## 扩展开发

### 添加新的项目类型

1. 编辑 `references/template-config.yaml`:

```yaml
project_types:
  - id: my-framework
    name: My Framework
    patterns:
      - "my-config.yaml"
    priority: 85
    language: typescript
    build_system: npm
    template: "web/my-framework.md"
```

2. 创建模板文件 `references/templates/web/my-framework.md`

### 添加新的解析器

```python
# scripts/parsers/my_parser.py
from parsers.base_parser import BaseParser

class MyParser(BaseParser):
    def parse(self, file_path: str) -> Dict[str, Any]:
        return {'dependencies': [], 'config': {}}
```

### 添加新的分析器

```python
# scripts/analyzers/my_analyzer.py
from analyzers.base_analyzer import BaseAnalyzer

class MyAnalyzer(BaseAnalyzer):
    def analyze(self) -> Dict[str, Any]:
        return {}
```

---

## 性能优化建议

1. **使用增量更新** - 只处理变更文件
2. **启用缓存** - 合理配置 TTL
3. **并行处理** - 设置合适的 max_workers
4. **排除目录** - 配置 exclude_dirs 跳过无关目录
5. **敏感信息扫描** - 建议在首次初始化时运行

---

## 依赖列表

```
# 核心依赖
pyyaml>=6.0

# 可选依赖
watchdog>=3.0.0        # 文件监控
jieba>=0.42.1          # 中文分词
rank_bm25>=0.2.2       # BM25 算法
tree-sitter>=0.20.0    # AST 解析
tree-sitter-languages>=1.8.0
toml>=0.10.2           # TOML 解析
networkx>=3.0          # 图算法（可选）
```

---

## 版本历史

### v3.0.0 (2026-03-12)

**企业级升级：百万行代码、多仓库、微服务架构**

- **性能优化**：分层延迟索引（L0-L3）、多仓库支持、内存优化
- **团队协作**：团队知识库、权限管理、问答协作、审计合规
- **企业集成**：CI/CD 集成、Issue 系统、代码审查、Webhook
- **AI 能力**：向量检索、代码补全、重构建议、质量预测
- **CLI 增强**：统一入口、新增命令、参数完善

### v2.0.0 (2026-03-12)

**重大更新：完整的安全与性能增强**

- **Phase 0**: 安全基础设施（敏感扫描、审计日志）
- **Phase 1**: 增量更新（文件监控、Git 变更检测）
- **Phase 2**: 语义问答（BM25 + Jieba、知识图谱）
- **Phase 3**: AST 分析（Tree-sitter、8 种语言）
- **Phase 4**: 项目识别扩展（60+ 类型、模板引擎）
- **Phase 5**: 创新功能（图表生成、依赖分析、AI 增强）

### v1.5.0 (2026-03-11)

- Token 消耗大幅降低（89%）
- 分层架构设计
- 飞书文档集成

### v1.4.0 (2026-03-11)

- 新增飞书文档集成
- 文档更新建议报告

### v1.3.0 (2026-03-11)

- 新增问答文档沉淀系统
- Git commit hash 记录
- 过期检测功能

### v1.2.0 (2026-03-11)

- 新增通用个性化配置系统
- 支持嵌套键名

### v1.1.0 (2026-03-11)

- 新增跨会话工作目录配置
- 群聊单聊配置共享

### v1.0.0

- 初始版本
- 50+ 项目类型识别
- 调用链分析
- 缓存机制

---

## 许可证

MIT License