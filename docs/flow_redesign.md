# project-assistant 执行流程重设计

## 核心原则

```
脚本 = 数据收集 + 规则匹配 + 结构化输出
AI   = 语义理解 + 内容生成 + 智能决策
```

## 执行流程图

```
用户触发 /init
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 1: 数据收集 (脚本)                                │
├─────────────────────────────────────────────────────────┤
│  1. 安全扫描 (sensitive_scanner.py)                     │
│  2. 项目探测 (detector.py)                              │
│  3. 结构收集:                                           │
│     - 目录树                                            │
│     - 文件列表 (按类型分组)                             │
│     - 子项目列表 (如果是 mono-repo)                     │
│     - 配置文件内容                                      │
│     - 入口点文件                                        │
│  4. 输出: structured_data.json                          │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 2: AI 分析 (Claude)                              │
├─────────────────────────────────────────────────────────┤
│  输入: structured_data.json + 关键文件内容              │
│                                                         │
│  AI 任务:                                               │
│  1. 项目类型判定 (脚本无法匹配时)                       │
│  2. 模块功能描述生成                                    │
│  3. 核心功能总结                                        │
│  4. 构建/运行命令推断                                   │
│  5. 注意事项生成                                        │
│  6. 技术栈分析                                          │
│                                                         │
│  输出: ai_analysis.json                                 │
└─────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Phase 3: 文档生成 (脚本)                               │
├─────────────────────────────────────────────────────────┤
│  合并 structured_data.json + ai_analysis.json           │
│  渲染模板 → project.md                                  │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1: 数据收集脚本

### 1.1 项目探测规则扩展

```python
# detector.py 新增规则

RULES = [
    # Repo 多仓库项目 (最高优先级)
    ProjectTypeRule(['.repo/manifest.xml'], 'repo-mono', 'multi', 200, 'repo'),

    # Android AOSP / 厂商 SDK
    ProjectTypeRule(['.repo/manifest.xml', 'device/'], 'aosp', 'java', 150, 'soong'),
    ProjectTypeRule(['.repo/manifest.xml', 'vendor/'], 'vendor-sdk', 'c', 150, 'make'),

    # 嵌入式 SDK (BK7258 等芯片 SDK)
    ProjectTypeRule(['.repo/manifest.xml', 'project/'], 'chip-sdk', 'c', 140, 'make'),
    ProjectTypeRule(['sdkconfig', 'Kconfig'], 'esp-idf', 'c', 100, 'idf'),

    # 标准项目类型...
]
```

### 1.2 结构化数据输出

```python
# collector.py - 新增数据收集器

@dataclass
class ProjectData:
    """项目结构化数据"""

    # 基本信息 (脚本收集)
    name: str
    root_path: str
    project_type: str                    # 规则匹配结果
    detected_languages: List[str]        # 文件扩展名统计
    detected_build_systems: List[str]    # 构建文件检测

    # 目录结构 (脚本生成)
    directory_tree: str                  # 树形文本

    # 文件清单 (脚本收集)
    entry_files: List[str]               # 入口文件
    config_files: List[Dict[str, str]]   # 配置文件 + 内容摘要
    source_files: List[str]              # 源码文件 (按类型分组)
    build_files: List[str]               # 构建文件

    # Mono-repo 特有 (脚本收集)
    sub_projects: List[Dict[str, str]]   # 子项目列表

    # 模块信息 (脚本收集目录名，AI 生成描述)
    modules: List[Dict[str, str]]        # {name, path, description: 待AI填充}

    # 依赖 (脚本解析)
    dependencies: List[Dict[str, str]]   # 从配置文件解析

    # 以下字段留给 AI 填充
    ai_project_type: str = ""            # AI 判定类型 (脚本无法匹配时)
    ai_core_features: List[str] = []     # 核心功能
    ai_build_commands: Dict[str, str] = {}  # 构建/运行命令
    ai_notes: List[str] = []             # 注意事项
    ai_tech_stack: List[str] = []        # 技术栈
```

### 1.3 Repo 项目特殊处理

```python
# repo_analyzer.py - 新增

class RepoProjectAnalyzer:
    """分析 repo 管理的多仓库项目"""

    def analyze(self, project_dir: str) -> Dict[str, Any]:
        manifest_path = Path(project_dir) / '.repo' / 'manifest.xml'

        if not manifest_path.exists():
            return {}

        # 解析 manifest.xml
        manifest = self._parse_manifest(manifest_path)

        # 获取子项目列表
        sub_projects = []
        for project in manifest.findall('.//project'):
            sub_projects.append({
                'name': project.get('name'),
                'path': project.get('path'),
                'revision': project.get('revision'),
                'type': self._detect_subproject_type(project.get('path'))
            })

        return {
            'is_repo_project': True,
            'manifest_name': manifest.get('name', 'default'),
            'sub_projects': sub_projects,
            'total_sub_projects': len(sub_projects),
        }

    def _detect_subproject_type(self, path: str) -> str:
        """检测子项目类型"""
        # 根据路径特征判断
        if 'freertos' in path.lower():
            return 'freertos'
        if 'sdk' in path.lower():
            return 'sdk'
        if 'driver' in path.lower():
            return 'driver'
        return 'unknown'
```

---

## Phase 2: AI 分析 Prompt

### 2.1 AI 分析输入

```
你正在分析一个软件项目，请根据以下结构化数据生成项目文档。

## 项目结构数据

```json
{structured_data_json}
```

## 关键文件内容

### 入口文件: {entry_file}
```
{entry_file_content}
```

### 配置文件: {config_file}
```
{config_file_content}
```

### README.md (如果存在)
```
{readme_content}
```

## 任务

请分析以上数据，输出以下信息（JSON 格式）：

1. **project_type**: 项目类型判定
   - 如果脚本已识别为具体类型，请确认是否正确
   - 如果脚本是 "unknown"，请根据目录结构和文件内容判断

2. **modules**: 为每个模块生成功能描述
   - 模块名已由脚本收集
   - 请根据模块名、目录结构、相关文件生成简短描述

3. **core_features**: 列出 3-5 个核心功能

4. **build_commands**: 推断构建命令
   - install: 安装依赖命令
   - build: 构建命令
   - run: 运行命令
   - test: 测试命令

5. **tech_stack**: 技术栈列表

6. **notes**: 重要注意事项

## 输出格式

```json
{
  "project_type": "xxx",
  "modules": [
    {"name": "xxx", "path": "xxx", "description": "功能描述"}
  ],
  "core_features": ["功能1", "功能2"],
  "build_commands": {
    "install": "...",
    "build": "...",
    "run": "...",
    "test": "..."
  },
  "tech_stack": ["技术1", "技术2"],
  "notes": ["注意1", "注意2"]
}
```
```

### 2.2 SKILL.md 中的触发逻辑

```markdown
## 执行流程

### Step 1: 收集数据

```bash
# 运行数据收集脚本
python3 {baseDir}/scripts/collector.py "$PROJECT_DIR" --output .projmeta/structured_data.json
```

### Step 2: 读取数据

读取 `.projmeta/structured_data.json`，获取：
- 项目类型
- 目录结构
- 模块列表
- 入口文件路径
- 配置文件路径

### Step 3: 读取关键文件

读取以下文件内容（如果存在）：
- 入口文件 (如 main.py, main.c)
- 主要配置文件
- README.md

### Step 4: AI 分析

基于结构化数据和关键文件内容，生成：
1. 项目类型确认/纠正
2. 模块功能描述
3. 核心功能列表
4. 构建/运行命令
5. 技术栈
6. 注意事项

### Step 5: 生成文档

将脚本数据 + AI 分析结果合并，渲染模板生成 project.md
```

---

## Phase 3: 文档模板

```markdown
# {name} 项目概览

> 自动生成于 {date}

## 基本信息

| 属性 | 值 |
|------|-----|
| 项目名称 | {name} |
| 项目类型 | {project_type} |
| 主要语言 | {languages} |
| 构建系统 | {build_system} |

## 项目结构

```
{directory_tree}
```

{%- if sub_projects %}

## 子项目

| 项目 | 路径 | 类型 |
|------|------|------|
{% for p in sub_projects %}
| {{p.name}} | `{{p.path}}` | {{p.type}} |
{% endfor %}

{%- endif %}

## 模块划分

| 模块 | 路径 | 功能 |
|------|------|------|
{% for m in modules %}
| {{m.name}} | `{{m.path}}` | {{m.description}} |
{% endfor %}

## 核心功能

{% for f in core_features %}
- {{f}}
{% endfor %}

## 技术栈

{% for t in tech_stack %}
- {{t}}
{% endfor %}

## 构建指南

```bash
# 安装依赖
{build_commands.install}

# 构建
{build_commands.build}

# 运行
{build_commands.run}

# 测试
{build_commands.test}
```

## 注意事项

{% for n in notes %}
- {{n}}
{% endfor %}

## 相关文件

- 入口: `{entry_file}`
- 配置: {config_files}

---

*此文档由 project-assistant 自动生成*
```

---

## 实现优先级

1. **P0 - 修复检测规则**
   - 添加 repo 项目识别
   - 添加芯片 SDK 类型

2. **P1 - 数据收集器**
   - 实现 collector.py
   - 输出 structured_data.json

3. **P2 - AI 分析流程**
   - 更新 SKILL.md 触发逻辑
   - 设计 Prompt 模板

4. **P3 - 文档模板优化**
   - 支持多项目类型模板
   - 支持子项目展示

---

## 示例: bk7258 项目

### 脚本收集的数据

```json
{
  "name": "bk7258",
  "project_type": "chip-sdk",
  "detected_languages": ["c", "python", "shell"],
  "directory_tree": "...",
  "sub_projects": [
    {"name": "project", "path": "project/", "type": "main-app"},
    {"name": "sdk", "path": "sdk/", "type": "sdk"},
    {"name": "embedded-software/autoai-freertos", "path": "...", "type": "freertos"}
  ],
  "modules": [
    {"name": "components", "path": "project/components/"},
    {"name": "bk3515_ota", "path": "project/components/bk3515_ota/"},
    ...
  ],
  "entry_files": [".repo/repo/main.py"],
  "config_files": [
    {"path": ".repo/manifest.xml", "type": "repo-manifest"}
  ]
}
```

### AI 生成的分析

```json
{
  "project_type": "bk7258-sdk",
  "project_type_description": "BK7258 芯片 SDK，基于 FreeRTOS 的嵌入式开发平台",
  "modules": [
    {"name": "components", "description": "组件库，包含 OTA、音频播放等服务"},
    {"name": "bk3515_ota", "description": "OTA 固件升级组件"},
    {"name": "bk_mp3_play", "description": "MP3 音频播放组件"},
    ...
  ],
  "core_features": [
    "BK7258 芯片 SDK 开发环境",
    "FreeRTOS 实时操作系统",
    "OTA 固件升级支持",
    "音频播放/录制服务",
    "WiFi 连接管理"
  ],
  "build_commands": {
    "install": "参考 SDK 文档安装工具链",
    "build": "make 或参考 project/ 目录下的构建脚本",
    "run": "烧录到 BK7258 开发板",
    "test": "参考测试文档"
  },
  "tech_stack": [
    "C 语言",
    "FreeRTOS",
    "BK7258 SDK",
    "Python (repo 工具)"
  ],
  "notes": [
    "这是一个 repo 管理的多仓库项目",
    "使用 `repo sync` 同步所有子项目",
    "需要 BK7258 专用工具链"
  ]
}
```

### 最终生成的文档

```markdown
# bk7258 项目概览

> BK7258 芯片 SDK，基于 FreeRTOS 的嵌入式开发平台

## 基本信息

| 属性 | 值 |
|------|-----|
| 项目名称 | bk7258 |
| 项目类型 | BK7258 芯片 SDK |
| 主要语言 | C, Python |
| 构建系统 | Make, Repo |

## 项目结构

```
bk7258/
├── project/          # 主应用项目
│   └── components/   # 组件库
├── sdk/              # SDK 核心
└── .repo/            # Repo 配置
```

## 子项目

| 项目 | 类型 |
|------|------|
| project | 主应用 |
| sdk | SDK 核心 |
| embedded-software/autoai-freertos | FreeRTOS |

## 模块划分

| 模块 | 功能 |
|------|------|
| components | 组件库，包含 OTA、音频等服务 |
| bk3515_ota | OTA 固件升级组件 |
| bk_mp3_play | MP3 播放组件 |
...

## 核心功能

- BK7258 芯片 SDK 开发环境
- FreeRTOS 实时操作系统
- OTA 固件升级支持
...
```