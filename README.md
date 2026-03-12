# Project Assistant 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **让 AI 真正理解你的项目，Token 消耗降低 80%-95%**

---

## 💡 这个项目能为你做什么？

### 你是否遇到过这些问题？

| 痛点 | Project Assistant 的解决方案 |
|------|------------------------------|
| 😫 每次问 AI 都要重新解释项目背景 | ✅ 自动生成项目文档，AI 永远记得项目结构 |
| 💰 AI 分析项目 Token 消耗巨大 | ✅ 分层架构 + 增量更新，Token 省掉 80%-95% |
| 🔍 新项目不知道从哪里入手 | ✅ 一键识别 60+ 项目类型，自动分析架构 |
| 📝 团队问过的问题反复问 | ✅ 问答自动沉淀，相似问题秒回 |
| 🔒 担心敏感信息泄露给 AI | ✅ 自动扫描脱敏，审计日志可追溯 |
| 🔄 改了代码不知道影响范围 | ✅ 调用链分析，改动影响一目了然 |

---

## 🎯 核心价值

### 1. 省钱：Token 消耗降低 80%-95%

| 场景 | 传统方式 | 使用本工具 | 节省 |
|------|---------|-----------|------|
| 首次分析项目 | 50,000-100,000 Token | ~11,500 Token | **77-88%** |
| 追问新功能 | 5,000-10,000 Token | ~500-2,000 Token | **80-95%** |
| 相似问题再问 | 5,000 Token | ~0 Token（缓存命中） | **接近 100%** |

**计算示例**：假设 GPT-4 价格 $0.03/1K Token
- 传统方式分析 10 次项目：$15-30
- 使用本工具：$1.5-3
- **每次使用节省 $1.5-2.7**

### 2. 省时：秒级理解任意项目

```
你：这是什么项目？
AI：[自动识别] 这是一个 STM32 + FreeRTOS 的嵌入式项目
    - MCU: STM32F407
    - RTOS: FreeRTOS v10.4
    - 构建系统: CMake + ARM GCC
    - 入口文件: Src/main.c
    - 模块: WiFi、BLE、Sensor、UI
    - 依赖: lwIP、FreeRTOS、STM32 HAL
```

**支持 60+ 项目类型**：嵌入式 MCU/RTOS/Linux、Android、iOS、Web 前后端、桌面应用、游戏、AI/ML...

### 3. 知识沉淀：问过的问题永远记得

```
你：WiFi 连接流程是怎样的？
AI：[回答流程...]

[一周后，另一个团队成员问类似问题]
同事：WiFi 怎么连？
AI：[缓存命中] 我之前回答过类似问题，为您返回：
    1. 调用 wifi_init() 初始化
    2. 调用 wifi_connect() 连接
    ...
    [关联文件: src/wifi.c, docs/wifi.md]
```

### 4. 安全合规：敏感信息不泄露

```
你：帮我分析这个项目
AI：[安全扫描]
    ⚠️ 发现敏感信息：
    - .env 文件包含 API_KEY
    - config.py 包含数据库密码
    已自动脱敏，可安全分析
```

### 5. 改动影响：提前知道改哪里

```
你：修改 wifi_connect() 会影响什么？
AI：[调用链分析]
    直接影响 (3处):
    - src/main.c:45 - 启动时调用
    - src/ble.c:120 - 配网时调用
    - test/wifi_test.c:15 - 测试用例

    间接影响 (5处):
    - docs/api.md - 文档需更新
    - test/integration_test.py - 集成测试
```

---

## 🛠️ 核心功能

### v2.x 基础功能

| 功能 | 价值 | 使用场景 |
|------|------|---------|
| **项目识别** | 秒级理解项目结构 | 新项目上手、项目交接 |
| **智能问答** | 精准回答项目问题 | 日常开发、问题排查 |
| **问答沉淀** | 知识不丢失 | 团队协作、新人培训 |
| **安全扫描** | 防止敏感泄露 | 代码审查、开源前检查 |
| **AST 分析** | 深度理解代码 | 代码审查、重构准备 |
| **调用链分析** | 改动影响可视化 | 重构决策、Bug 定位 |
| **依赖分析** | 发现潜在问题 | 依赖升级、安全检查 |
| **图表生成** | 可视化架构 | 文档编写、技术分享 |
| **知识图谱** | 关联知识管理 | 问答过期检测、智能推荐 |
| **增量更新** | 只处理变更 | 大项目优化、节省时间 |

### v3.0 企业级功能

| 功能 | 价值 | 使用场景 |
|------|------|---------|
| **分层索引** | 百万行代码秒级检索 | 大型项目、微服务架构 |
| **多仓库管理** | 单命令管理多仓库 | Monorepo、前后端分离 |
| **团队知识库** | 团队问答知识共享 | 团队协作、新人培训 |
| **CI/CD 集成** | 流水线自动分析 | PR 审查、自动报告 |
| **向量检索** | 语义级代码搜索 | 模糊搜索、代码发现 |
| **代码补全** | 项目感知智能补全 | IDE 集成、提效 |
| **重构建议** | AI 代码质量建议 | 代码审查、技术债清理 |
| **风险预测** | 代码质量风险评估 | 发布前检查、重构优先级 |

---

## 📦 快速开始

### 安装

```bash
# 方式一：ClawHub 安装（推荐）
claw install project-assistant

# 方式二：手动安装
git clone https://github.com/Northcipher/project-assistant.git ~/.claude/skills/project-assistant
```

### 安装依赖

```bash
# 核心依赖（必须）
pip install pyyaml

# 增强依赖（推荐）
pip install watchdog jieba rank_bm25 tree-sitter tree-sitter-languages toml
```

### 5 分钟上手

```
# 1. 设置工作目录
/set-workdir /path/to/your/project

# 2. 初始化项目（自动分析）
/init

# 3. 开始提问
这个项目的架构是什么？
WiFi 模块是怎么实现的？
修改 main.c 会影响什么？

# 4. 搜索历史问答
/search-qa WiFi

# 5. 生成架构图
/diagram architecture
```

---

## 💬 使用场景示例

### 场景一：新项目上手

```
你：/init
AI：正在分析项目...

    📊 项目概览
    - 类型: React + TypeScript 前端项目
    - 构建: Vite
    - 主要依赖: React 18, React Router, TailwindCSS
    - 目录结构:
      src/
      ├── components/   # 组件
      ├── pages/        # 页面
      ├── hooks/        # 自定义 Hooks
      └── utils/        # 工具函数

    入口文件: src/main.tsx
    配置文件: vite.config.ts, tsconfig.json

你：这个项目的路由是怎么配置的？
AI：[分析 src/App.tsx]
    使用 React Router v6 配置路由...
    [详细回答 + 代码位置]
```

### 场景二：代码审查

```
你：帮我审查 src/auth/login.ts 的代码质量
AI：[AI 分析]

    📊 代码质量评分: 78/100

    ⚠️ 发现问题:
    - 第 23 行: 硬编码密码，存在安全风险
    - 第 45 行: 函数过长 (85 行)，建议拆分
    - 第 67 行: 发现 TODO 未处理

    💡 重构建议:
    1. 将密码改为环境变量
    2. 拆分 validateForm() 函数
    3. 处理 TODO 注释
```

### 场景三：依赖升级

```
你：分析项目依赖
AI：[依赖分析]

    📦 依赖概况: 47 个直接依赖, 312 个间接依赖

    ⚠️ 发现问题:
    - 循环依赖: A → B → C → A
    - 版本冲突: react 需要 17.x，某插件要求 18.x
    - 已废弃: request@2.88.0 (建议替换为 axios)

    💡 建议:
    1. 解除循环依赖 A-B-C
    2. 统一 React 版本
    3. 迁移 request 到 axios
```

---

## 🏗️ 架构设计

### 分层索引架构 (v3.0)

```
.projmeta/
├── project.md           # L0: 项目概览 (~1-2KB, 始终加载)
├── index/               # 分层索引
│   ├── l0_index.json    # L0: 文件列表、类型 (< 1s)
│   ├── l1_index.json    # L1: 函数/类定义 (< 5s)
│   └── l2_index.json    # L2: 调用图、向量嵌入 (< 30s)
├── docs/                # L3: 深度分析（后台）
├── cache.json           # 分析缓存
├── qa_cache.json        # 问答缓存（BM25 索引）
├── knowledge_graph.json # 知识图谱
└── audit.log            # 审计日志
```

**分层加载策略**：
- L0 快速索引：文件元数据，< 1 秒
- L1 结构索引：函数/类定义，< 5 秒
- L2 语义索引：调用图、向量嵌入，< 30 秒
- L3 深度索引：全量 AST、质量分析，后台运行

### 统一 CLI 入口

所有功能通过 `cli.py` 统一调用：

```bash
python3 scripts/cli.py <command> [options]

# 常用命令
python3 scripts/cli.py init .              # 初始化项目
python3 scripts/cli.py search-qa "登录"    # 搜索问答
python3 scripts/cli.py diagram architecture .  # 生成架构图
```

---

## 📁 详细文档

| 文档 | 内容 |
|------|------|
| [DOCS.md](DOCS.md) | 完整开发者文档 |
| [SKILL.md](SKILL.md) | 命令索引与执行流程 |
| [references/guides/](references/guides/) | 各功能详细指南 |

---

## 📦 依赖说明

| 依赖 | 必需 | 用途 |
|------|------|------|
| Python 3.6+ | ✅ | 运行环境 |
| PyYAML | ✅ | YAML 解析 |
| Git | ❌ | 版本检测 |
| watchdog | ❌ | 文件监控 |
| jieba + rank_bm25 | ❌ | 语义匹配 |
| tree-sitter | ❌ | AST 解析 |

### v3.0 可选依赖

| 依赖 | 用途 |
|------|------|
| faiss-cpu / chromadb | 向量检索 |
| flask | Webhook 服务器 |
| PyGithub / python-jira | 企业集成 |

---

## 📈 版本历史

### v3.0.0 (2026-03-12)

**企业级升级**

- 分层延迟索引（L0-L3），百万行代码秒级检索
- 多仓库支持（Monorepo 管理）
- 团队知识库与权限管理
- CI/CD、Issue、代码审查集成
- AI 能力：向量检索、代码补全、重构建议、风险预测

### v2.0.0 (2026-03-11)

**安全与性能增强**

- 安全体系：敏感扫描、审计日志
- 增量更新：文件监控、Git 变更检测
- 语义问答：BM25 + Jieba
- AST 分析：Tree-sitter 8 种语言

### v1.0.0

- 50+ 项目类型识别
- 调用链分析
- 问答沉淀

---

## 📜 许可证

[MIT License](LICENSE)

---

**让 AI 成为真正的项目伙伴，而不是每次都要重新认识你的项目。**