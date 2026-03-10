# Project Assistant

为 OpenClaw 设计的项目分析工具集，提供项目初始化和智能问答功能。

## 特性

- **分层文档结构** - 优化 Token 消耗，大型项目初始化仅 ~1-2KB
- **Q&A 缓存** - 问过的问题快速回答，Token 消耗接近 0
- **IPC 分析** - 支持智能座舱等大型多进程项目的跨进程通信分析
- **懒加载文档** - 详细文档按需生成，减少初始开销
- **自动规模检测** - 自动识别项目规模（小型/中型/大型）
- **TODO/FIXME 提取** - 自动扫描代码中的待办事项
- **测试分析** - 分析测试覆盖率和测试框架
- **CI/CD 解析** - 支持 GitHub Actions、GitLab CI、Jenkins 等
- **环境变量扫描** - 检测配置和敏感信息

## 快速开始

### 1. 放置文件

将本项目内容放到 OpenClaw 能访问的位置：

```
~/.claude/
├── skills/
│   ├── init.md
│   └── project-assistant.md
├── commands/init/
│   ├── embedded/
│   ├── mobile/
│   ├── web/
│   ├── desktop/
│   ├── system/
│   └── templates/
└── tools/init/
    ├── detector.py
    ├── constants.py
    ├── parsers/
    ├── analyzers/
    │   ├── ipc_analyzer.py
    │   ├── todo_extractor.py
    │   ├── test_analyzer.py
    │   ├── env_scanner.py
    │   └── ...
    └── utils/
        ├── cache_manager.py
        ├── qa_cache.py
        ├── doc_generator.py
        └── ...
```

### 2. 使用

```
/init [项目目录]          # 初始化项目
/project-assistant        # 项目百事通，回答项目相关问题
```

## 功能

### `/init` - 项目初始化

自动识别项目类型，生成分层项目文档：

```bash
/init                      # 初始化当前目录
/init /path/to/project     # 初始化指定目录
/init --force              # 强制重新扫描
```

**支持的参数：**

| 参数 | 说明 |
|------|------|
| `--force` | 强制重新扫描，忽略缓存 |
| `--depth=N` | 扫描深度，默认3 |
| `--verbose` | 显示详细日志 |
| `--quick` | 快速模式，只扫描顶层 |

#### 生成的文档结构

```
.claude/
├── project.md           # L0: 项目概览 (~1-2KB)
├── index/               # 数据索引 (JSON)
│   ├── processes.json   # 进程索引
│   ├── ipc.json         # IPC 接口索引
│   └── structure.json   # 目录结构索引
├── docs/                # 详细文档（按需生成）
│   ├── subsystems/      # 子系统文档
│   │   └── {name}/
│   │       ├── index.md     # L1: 子系统摘要
│   │       └── {process}.md # L2: 进程详情
│   └── ipc/
│       └── overview.md      # L2: IPC 详情
├── cache.json           # 缓存
└── qa_cache.json        # Q&A 缓存
```

#### Token 消耗优化

| 项目规模 | 优化前 project.md | 优化后 L0 | 节省 |
|---------|------------------|----------|------|
| 小型 (<500 文件) | 5-10 KB | 1-2 KB | 80% |
| 中型 (500-5000 文件) | 20-50 KB | 2-3 KB | 90% |
| 大型 (>5000 文件) | 50-100 KB | 3-5 KB | 95% |

### `/project-assistant` - 项目百事通

智能问答助手，支持：

```
这个项目的架构是什么？
用户登录功能是怎么实现的？
main函数在哪里？
如何构建这个项目？
修改 login 函数会影响什么？
vehicle_service 进程是怎么实现的？  # 大型项目进程分析
进程间怎么通信的？                   # IPC 分析
项目有哪些 TODO？                    # TODO 提取
测试覆盖率是多少？                   # 测试分析
CI/CD 流程是什么？                   # CI/CD 解析
```

#### Q&A 缓存

问过的问题自动缓存，再次询问 Token 消耗接近 0：

| 场景 | Token 消耗 |
|------|-----------|
| 首次提问 | 正常消耗 |
| 相同问题再问 | ~0 (缓存命中) |
| 相似问题 | 很低 (相似度匹配) |

## 支持的项目类型

| 分类 | 类型 |
|------|------|
| **嵌入式MCU** | STM32, ESP32, Arduino, Pico, Keil, IAR |
| **嵌入式RTOS** | FreeRTOS, Zephyr, RT-Thread |
| **嵌入式Linux** | Yocto, Buildroot, OpenWrt |
| **QNX** | QNX Neutrino |
| **Android** | 应用, NDK, AOSP |
| **iOS** | Swift, SwiftUI |
| **Web前端** | React, Vue, Angular, Svelte, Next.js |
| **Web后端** | Django, FastAPI, Flask, Spring |
| **桌面应用** | Qt, Electron, Flutter |
| **系统编程** | C/C++, Rust, Go |

## 目录结构

```
skills/                    # Skill 定义文件
├── init.md               # 项目初始化入口
└── project-assistant.md  # 项目百事通入口

commands/init/             # 子 Skill 定义
├── embedded/             # 嵌入式项目分析
│   ├── mcu.md           # MCU 项目
│   ├── rtos.md          # RTOS 项目
│   ├── linux.md         # 嵌入式 Linux
│   ├── qnx.md           # QNX 项目
│   └── android-native.md # Android NDK/AOSP
├── mobile/               # 移动端项目分析
│   ├── android.md
│   └── ios.md
├── web/                  # Web项目分析
│   ├── frontend.md
│   └── backend.md
├── desktop/              # 桌面应用分析
│   └── desktop.md
├── system/               # 系统编程分析
│   └── native.md
└── templates/            # 文档模板
    └── project-template.md

tools/init/                # Python 工具
├── detector.py           # 项目类型探测器
├── constants.py          # 统一常量定义
├── parsers/              # 配置文件解析器
│   ├── base_parser.py    # 解析器基类
│   ├── cmake_parser.py
│   ├── gradle_parser.py
│   ├── cicd_parser.py    # CI/CD 解析器
│   └── ...
├── analyzers/            # 代码分析器
│   ├── ipc_analyzer.py   # IPC 分析器
│   ├── todo_extractor.py # TODO/FIXME 提取器
│   ├── test_analyzer.py  # 测试分析器
│   ├── env_scanner.py    # 环境变量扫描器
│   └── ...
└── utils/                # 工具函数
    ├── cache_manager.py      # 缓存管理
    ├── qa_cache.py           # Q&A 缓存
    ├── doc_generator.py      # 分层文档生成
    ├── call_chain_analyzer.py
    ├── git_info.py
    └── logger.py

tests/                     # 测试套件
├── conftest.py           # pytest fixtures
├── test_detector.py      # detector 测试
├── test_cache_manager.py # cache_manager 测试
└── test_parsers/         # parser 测试
```

## 工具命令

```bash
# 项目类型探测
python ~/.claude/tools/init/detector.py ./project

# 大型项目探测输出示例:
# {
#   "project_type": "embedded-linux",
#   "language": "cpp",
#   "build_system": "cmake",
#   "scale": "large",
#   "subsystems": ["vehicle", "infotainment", "adas"],
#   "processes": 15,
#   "ipc_protocols": ["binder", "dbus", "someip"]
# }

# 缓存管理
python ~/.claude/tools/init/utils/cache_manager.py check ./project
python ~/.claude/tools/init/utils/cache_manager.py update ./project

# Q&A 缓存
python ~/.claude/tools/init/utils/qa_cache.py stats ./project
python ~/.claude/tools/init/utils/qa_cache.py cleanup ./project

# 分层文档生成
python ~/.claude/tools/init/utils/doc_generator.py structure ./project
python ~/.claude/tools/init/utils/doc_generator.py l1 ./project "subsystem"

# IPC 分析（大型项目）
python ~/.claude/tools/init/analyzers/ipc_analyzer.py ./project
python ~/.claude/tools/init/analyzers/ipc_analyzer.py ./project --doc

# 调用链分析
python ~/.claude/tools/init/utils/call_chain_analyzer.py ./project main

# Git 信息
python ~/.claude/tools/init/utils/git_info.py ./project info

# TODO/FIXME 提取
python ~/.claude/tools/init/analyzers/todo_extractor.py ./project
python ~/.claude/tools/init/analyzers/todo_extractor.py ./project --md

# 测试分析
python ~/.claude/tools/init/analyzers/test_analyzer.py ./project

# CI/CD 配置解析
python ~/.claude/tools/init/parsers/cicd_parser.py ./project

# 环境变量扫描
python ~/.claude/tools/init/analyzers/env_scanner.py ./project
```

## 大型项目支持

针对智能座舱等大型多进程项目：

### 自动规模检测

探测器自动识别项目规模：

| 规模 | 文件数 | 目录数 | 特征 |
|------|--------|--------|------|
| 小型 | <500 | <50 | 单模块 |
| 中型 | 500-5000 | 50-500 | 多模块 |
| 大型 | >5000 | >500 | 多进程/多子系统 |

### IPC 分析

自动分析跨进程通信：

| 协议 | 支持 |
|------|------|
| Binder | AIDL 接口解析 |
| DBus | XML 配置解析 |
| Socket | Unix Domain / TCP |
| gRPC | Protobuf 服务定义 |
| SOME/IP | 车载协议 |

### 分层检索流程

```
用户问: "vehicle_service 进程是怎么实现的？"

系统执行:
1. 检查 qa_cache.json → 命中？返回
2. 检查 docs/subsystems/vehicle/vehicle_service.md → 存在？返回
3. 不存在 → 分析代码 → 生成文档 → 缓存
4. 返回答案
```

### L0 文档示例

```markdown
# 智能座舱系统

> 类型: embedded-linux | 进程: 15 | 接口: 23

## 子系统

| 子系统 | 进程数 | 说明 |
|--------|--------|------|
| vehicle | 5 | 车辆控制 |
| infotainment | 6 | 信息娱乐 |
| adas | 4 | 辅助驾驶 |

## 快速命令

```bash
make all      # 构建
make run      # 运行
```

## 数据索引

| 数据 | 文件 |
|------|------|
| 进程列表 | index/processes.json |
| IPC 接口 | index/ipc.json |

## 详细文档

详细文档按需生成，参见 `docs/` 目录
```

## 不同角色问答场景分析

基于飞书机器人群聊场景，不同角色的问题覆盖情况：

### 角色覆盖率

| 角色 | 覆盖率 | 主要支持功能 |
|------|--------|-------------|
| 开发工程师 | 90% | 代码定位、调用链、修改影响分析 |
| 新入职员工 | 85% | 项目概览、快速上手、代码结构 |
| 项目经理 | 70% | 子系统、依赖、最近提交 |
| 架构师 | 70% | IPC 通信、架构概览 |
| 测试工程师 | 75% | 测试分析、覆盖率统计 |
| DevOps | 80% | 构建、配置文件、CI/CD |
| 技术主管 | 70% | 代码量、贡献者、TODO 管理 |
| 产品经理 | 50% | 功能定位、版本变化 |

### 各角色典型问题示例

**开发工程师** ✓ 90%
```
"main 函数在哪里？"              → detector.py entry_points
"登录功能怎么实现的？"           → call_chain_analyzer.py
"修改 login 函数会影响什么？"    → call_chain_analyzer.py --impact
"vehicle 和 infotainment 怎么通信？" → ipc_analyzer.py
```

**项目经理** ✓ 70%
```
"项目有多少个子系统？"           → detector.py subsystems
"最近提交了什么？"               → git_info.py
"项目依赖了哪些第三方库？"       → detector.py dependencies
"项目有哪些待办事项？"           → todo_extractor.py
```

**测试工程师** ✓ 75%
```
"项目有测试代码吗？在哪？"       → test_analyzer.py
"测试覆盖率是多少？"             → test_analyzer.py
"如何运行测试？"                 → 项目文档 build_cmd
```

**DevOps** ✓ 80%
```
"怎么构建这个项目？"             → 项目文档 build_cmd
"配置文件在哪？"                 → detector.py config_files
"CI/CD 流程是什么？"             → cicd_parser.py
"环境变量有哪些？"               → env_scanner.py
```

## 开发待办项 (TODO)

### 高优先级

| 功能 | 描述 | 受益角色 | 状态 |
|------|------|---------|------|
| ~~测试分析器~~ | 扫描 test/ 目录，提取测试用例，统计覆盖率 | 测试工程师 | ✅ 已完成 |
| ~~TODO/FIXME 提取~~ | 正则扫描代码注释，提取待办事项 | 技术主管、PM | ✅ 已完成 |
| ~~CI/CD 配置解析~~ | 解析 .gitlab-ci.yml, Jenkinsfile, GitHub Actions | DevOps | ✅ 已完成 |

### 中优先级

| 功能 | 描述 | 受益角色 | 状态 |
|------|------|---------|------|
| ~~环境变量扫描~~ | 扫描 .env, config 文件，提取配置项 | DevOps | ✅ 已完成 |
| 代码质量检测 | 集成 pylint/eslint 等工具输出 | 架构师、技术主管 | 待开发 |
| API 文档生成 | 从代码注释生成 API 文档 | 开发工程师 | 待开发 |
| 性能热点分析 | 识别性能瓶颈代码 | 架构师 | 待开发 |

### 低优先级

| 功能 | 描述 | 受益角色 | 状态 |
|------|------|---------|------|
| 里程碑管理 | 集成项目管理工具 | PM | 待评估 |
| 需求追踪 | 关联代码与需求 | 产品经理 | 待评估 |
| 多语言文档 | 支持英文文档生成 | 国际化团队 | 待评估 |

## 测试

```bash
# 运行测试
pytest tests/ -v

# 测试覆盖率
pytest --cov=tools tests/
```

## 性能优化

| 优化项 | 优化前 | 优化后 | 提升 |
|--------|--------|--------|------|
| Git 命令执行 | 串行 ~30s | 并行 ~10s | 66% |
| IPC 分析文件遍历 | 6 次 rglob | 1 次 walk | 83% |
| 缓存检查 | 全量检查 | 懒加载 + 快速检查 | 50%+ |

## 依赖

- Python 3.6+
- Git（可选，用于Git信息功能）
- PyYAML（可选，用于 CI/CD 解析）

## 环境变量配置

```bash
export CLAUDE_LOG_LEVEL=DEBUG      # 日志级别
export CLAUDE_LOG_FILE=/path/log   # 日志文件
export CLAUDE_CACHE_TTL=7200       # 缓存TTL（秒）
```

## 更新日志

### v1.2.0
- 新增: TODO/FIXME 提取器
- 新增: 测试分析器
- 新增: CI/CD 配置解析器
- 新增: 环境变量扫描器
- 新增: 统一常量模块 constants.py
- 新增: 解析器基类 base_parser.py
- 新增: 测试框架 (pytest)
- 优化: Git 命令并行执行
- 优化: IPC 分析单次文件遍历
- 优化: 日志系统集成
- 修复: 裸异常捕获问题

### v1.1.0
- 初始版本

## 许可证

MIT License