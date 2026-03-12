# Project Assistant 开发者文档

> 本文档详细介绍 project-assistant 的架构设计、模块功能和 API 接口。

---

## 目录

- [架构概览](#架构概览)
- [核心模块](#核心模块)
- [安全体系](#安全体系)
- [文件监控与增量更新](#文件监控与增量更新)
- [智能问答系统](#智能问答系统)
- [AST 代码分析](#ast-代码分析)
- [项目识别与模板](#项目识别与模板)
- [创新功能](#创新功能)
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
│   ├── detector.py             # 项目类型探测器
│   ├── config_manager.py       # 配置管理器
│   ├── qa_doc_manager.py       # 问答文档管理
│   ├── feishu_doc_manager.py   # 飞书集成
│   ├── watcher.py              # 文件监控器 ✨新增
│   ├── knowledge_graph.py      # 知识图谱 ✨新增
│   ├── qa_recommender.py       # 问答推荐 ✨新增
│   ├── ast_parser.py           # AST 解析器 ✨新增
│   ├── template_engine.py      # 模板引擎 ✨新增
│   ├── diagram_generator.py    # 图表生成 ✨新增
│   ├── dependency_analyzer.py  # 依赖分析 ✨新增
│   ├── ai_analyzer.py          # AI 增强 ✨新增
│   │
│   ├── security/               # 安全模块 ✨新增
│   │   ├── sensitive_scanner.py
│   │   ├── security_config.py
│   │   └── audit_logger.py
│   │
│   ├── parsers/                # 配置文件解析器
│   │   ├── android_native_parser.py
│   │   ├── cmake_parser.py
│   │   ├── gradle_parser.py
│   │   ├── maven_parser.py
│   │   ├── package_json_parser.py
│   │   ├── python_parser.py
│   │   ├── rust_parser.py
│   │   └── ...
│   │
│   ├── analyzers/              # 代码分析器
│   │   ├── base_analyzer.py
│   │   ├── c_analyzer.py
│   │   ├── java_analyzer.py    # ✨新增
│   │   ├── python_analyzer.py  # ✨新增
│   │   ├── typescript_analyzer.py # ✨新增
│   │   └── ...
│   │
│   └── utils/
│       ├── cache_manager.py    # 缓存管理
│       ├── call_chain_analyzer.py
│       ├── git_info.py
│       ├── git_watcher.py      # ✨新增
│       ├── qa_cache.py
│       └── logger.py
│
├── references/
│   ├── templates/              # 项目模板
│   ├── guides/                 # 使用指南
│   └── template-config.yaml    # 模板配置 ✨新增
│
└── tests/                      # 测试套件
```

---

## 安全体系

### Phase 0 安全基础设施

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

### Phase 1 增量分析

#### 文件监控器

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

#### 增量缓存更新

**文件**: `scripts/utils/cache_manager.py`

```python
from utils.cache_manager import CacheManager

manager = CacheManager('/path/to/project')

# 增量更新
manager.incremental_update(['src/main.py', 'src/utils.py'])

# 使相关缓存失效
invalidated = manager.invalidate_by_files(['src/auth.py'])

# 获取增量更新信息
info = manager.get_incremental_update_info()
```

---

## 智能问答系统

### Phase 2 语义增强

#### 语义相似度匹配

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
    {'file_path': 'src/api/auth.py', 'symbol': 'authenticate'},
])

# 关联测试
graph.link_qa_to_test('q001', [
    {'test_file': 'tests/test_auth.py', 'test_name': 'test_login'},
])

# 获取文件相关问答
qa_ids = graph.get_related_qa('src/auth.py')

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

# 记录访问
recommender.record_access('q001', user_id='user1', file_context='src/auth.py')

# 基于上下文推荐
recommendations = recommender.recommend_by_context('src/auth.py')

# 基于历史推荐
recommendations = recommender.recommend_by_history('user1')

# 综合推荐
all_recs = recommender.get_recommendations(
    current_file='src/auth.py',
    user_id='user1'
)
```

---

## AST 代码分析

### Phase 3 深度代码分析

#### AST 解析器

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
print(project_result['summary'])
# {
#   'files_parsed': 50,
#   'total_functions': 234,
#   'total_classes': 45,
#   'parse_time': '2.3s'
# }
```

**支持语言**:
- Python
- JavaScript / TypeScript
- Java
- C / C++
- Go
- Rust

#### 调用图构建

**文件**: `scripts/utils/call_chain_analyzer.py`

```python
from utils.call_chain_analyzer import CallChainAnalyzer

analyzer = CallChainAnalyzer('/path/to/project')
result = analyzer.analyze()

# 获取调用链
chain = analyzer.get_call_chain('login', depth=3)

# 影响分析
impact = analyzer.get_impact_analysis('login')
print(impact['direct_callers'])
print(impact['test_callers'])
```

#### 语言专用分析器

**Java 分析器** (`scripts/analyzers/java_analyzer.py`):

```python
from analyzers.java_analyzer import JavaAnalyzer

analyzer = JavaAnalyzer('/path/to/java/project')
result = analyzer.analyze()

# 查找 Spring 组件
controllers = analyzer.find_spring_controllers()
services = analyzer.find_spring_services()
repositories = analyzer.find_spring_repositories()
```

**Python 分析器** (`scripts/analyzers/python_analyzer.py`):

```python
from analyzers.python_analyzer import PythonAnalyzer

analyzer = PythonAnalyzer('/path/to/python/project')
result = analyzer.analyze()

# 查找 Django 应用
apps = analyzer.find_django_apps()

# 查找 FastAPI 路由
routes = analyzer.find_fastapi_routes()
```

**TypeScript 分析器** (`scripts/analyzers/typescript_analyzer.py`):

```python
from analyzers.typescript_analyzer import TypeScriptAnalyzer

analyzer = TypeScriptAnalyzer('/path/to/ts/project')
result = analyzer.analyze()

# 查找 React 组件
components = analyzer.find_react_components()

# 查找 API 路由
routes = analyzer.find_api_routes()

# 获取推荐命令
commands = analyzer.get_recommended_commands()
```

---

## 项目识别与模板

### Phase 4 项目识别扩展

#### 项目类型配置

**文件**: `references/template-config.yaml`

支持 60+ 项目类型识别：

| 分类 | 类型 |
|------|------|
| 嵌入式 MCU | STM32, ESP32, Pico, Keil, IAR, PlatformIO |
| 嵌入式 RTOS | FreeRTOS, Zephyr, RT-Thread |
| 嵌入式 Linux | Buildroot, Yocto, OpenWrt, QNX |
| Android | 应用, NDK, AOSP |
| iOS | Swift, SwiftUI |
| Web 前端 | React, Vue, Angular, Svelte, Next.js, Nuxt |
| Web 后端 | Django, FastAPI, Flask, Spring, Go, Rust |
| 桌面应用 | Qt, Electron, Tauri |
| 游戏开发 | Unity, Unreal, Godot |
| AI/ML | PyTorch, TensorFlow, Jupyter |
| .NET | C#, F# |
| PHP | Laravel, Symfony |
| Scala | sbt 项目 |

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

# 多模板组合
composed = engine.compose(['header.md', 'content.md', 'footer.md'])

# 变量验证
validation = engine.validate_variables('embedded/mcu.md', {'MCU': 'STM32F407'})

# 匹配项目类型
matched = engine.match_project_type(files, dirs)
```

---

## 创新功能

### Phase 5 高级特性

#### 图表生成器

**文件**: `scripts/diagram_generator.py`

```python
from diagram_generator import DiagramGenerator

generator = DiagramGenerator()

# 架构图
arch = generator.generate_architecture_diagram({
    'modules': ['auth', 'api', 'database'],
    'subsystems': ['frontend', 'backend'],
})

# 时序图
seq = generator.generate_sequence_diagram([
    {'caller': 'Client', 'callee': 'Server', 'method': 'login'},
    {'caller': 'Server', 'callee': 'Database', 'method': 'query'},
])

# 依赖图
deps = generator.generate_dependency_graph({
    'app': ['auth', 'database'],
    'auth': ['database'],
})

# ER 图
er = generator.generate_er_diagram([
    {'name': 'User', 'fields': [{'name': 'id', 'type': 'int'}]},
])

# 类图
cls = generator.generate_class_diagram([
    {'name': 'UserService', 'methods': [{'name': 'login'}]},
])

# 包装为 Mermaid 代码块
print(generator.wrap_with_mermaid(arch))
```

#### 依赖分析器

**文件**: `scripts/dependency_analyzer.py`

```python
from dependency_analyzer import DependencyAnalyzer

analyzer = DependencyAnalyzer('/path/to/project')
result = analyzer.analyze()

print(result['total_dependencies'])
print(result['circular_dependencies'])
print(result['version_conflicts'])

# 获取依赖信息
info = analyzer.get_dependency_info('react')

# 查找依赖者
dependents = analyzer.find_dependents('lodash')
```

**支持锁文件**:
- package-lock.json (npm)
- yarn.lock
- pnpm-lock.yaml
- Cargo.lock
- go.sum
- requirements.txt
- poetry.lock
- composer.lock
- Gemfile.lock

#### AI 增强分析

**文件**: `scripts/ai_analyzer.py`

```python
from ai_analyzer import AIAnalyzer

analyzer = AIAnalyzer()

# 分析单个文件
result = analyzer.analyze_file('src/main.py')

print(result['quality'])       # 质量分数
print(result['issues'])        # 安全问题
print(result['code_smells'])   # 代码异味

# 分析整个项目
project_result = analyzer.analyze_project('/path/to/project')

# 重构建议
suggestions = analyzer.suggest_refactoring('src/main.py')
```

**检测能力**:
- 代码质量评分
- 安全漏洞检测
- 代码异味识别
- 重构建议生成

---

## API 参考

### 配置管理 API

```python
# config_manager.py
class ConfigManager:
    def get(self, key: str) -> Any
    def set(self, key: str, value: Any) -> None
    def delete(self, key: str) -> bool
    def show(self) -> Dict[str, Any]
```

### 项目检测 API

```python
# detector.py
class ProjectDetector:
    def detect(self) -> Dict[str, Any]
    def get_subskill_path(self) -> Optional[str]
    def clear_cache(cls) -> None
```

### 问答缓存 API

```python
# qa_cache.py
class QACacheManager:
    def get(self, question: str) -> Optional[QACacheEntry]
    def set(self, question: str, answer: str, **kwargs) -> None
    def find_similar(self, question: str) -> Optional[Tuple]
    def invalidate_files(self, changed_files: List[str]) -> int
    def cleanup_expired(self) -> int
```

### 缓存管理 API

```python
# cache_manager.py
class CacheManager:
    def load(self) -> CacheEntry
    def save(self) -> None
    def check_validity(self, quick: bool = False) -> Dict[str, Any]
    def update(self, analysis_data: Dict = None, incremental: bool = False) -> CacheEntry
    def incremental_update(self, changed_files: List[str]) -> CacheEntry
    def invalidate_by_files(self, files: List[str]) -> List[str]
```

### 安全 API

```python
# sensitive_scanner.py
class SensitiveScanner:
    def scan(self, project_dir: str) -> ScanResult
    def mask_content(self, content: str) -> str
    def should_exclude(self, file: str) -> bool
    def get_safe_content(self, file: str) -> str

# audit_logger.py
class AuditLogger:
    def log_operation(self, operation: str, details: Dict) -> None
    def log_sensitive_access(self, file: str, action: str) -> None
    def get_audit_trail(self, filters: Dict) -> List[LogEntry]
    def get_statistics(self, days: int = 7) -> Dict[str, Any]
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

1. 创建 `scripts/parsers/my_parser.py`:

```python
from parsers.base_parser import BaseParser

class MyParser(BaseParser):
    def parse(self, file_path: str) -> Dict[str, Any]:
        # 解析逻辑
        return {'dependencies': [], 'config': {}}
```

2. 在 `scripts/parsers/__init__.py` 中注册

### 添加新的分析器

1. 创建 `scripts/analyzers/my_analyzer.py`:

```python
from analyzers.base_analyzer import BaseAnalyzer

class MyAnalyzer(BaseAnalyzer):
    def analyze(self) -> Dict[str, Any]:
        # 分析逻辑
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

### v2.0.0 (2026-03-12)

**重大更新：完整的安全与性能增强**

**Phase 0 - 安全基础设施**:
- 新增敏感信息扫描器
- 新增安全配置管理
- 新增审计日志系统

**Phase 1 - 增量更新**:
- 新增文件监控器
- 新增 Git 变更检测
- 增强缓存管理器支持增量更新

**Phase 2 - 语义问答**:
- 新增 BM25 + Jieba 语义匹配
- 新增知识图谱
- 新增智能问答推荐

**Phase 3 - AST 分析**:
- 新增 Tree-sitter AST 解析器（8 种语言）
- 新增 Java/Python/TypeScript 专用分析器
- 增强调用链分析

**Phase 4 - 项目识别**:
- 新增 YAML 模板配置
- 支持项目类型扩展到 60+
- 新增模板引擎（继承、组合）

**Phase 5 - 创新功能**:
- 新增 Mermaid 图表生成
- 新增依赖分析器
- 新增 AI 增强分析

---

## 许可证

MIT License