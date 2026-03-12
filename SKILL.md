---
name: project-assistant
description: 项目初始化与智能分析工具。当用户要求初始化新项目、分析项目结构、项目问答时使用。触发词：初始化项目、init、分析项目、项目问答。
metadata:
  openclaw:
    emoji: "🚀"
    homepage: "https://github.com/Northcipher/project-assistant"
    requires:
      bins: ["python3"]
---

# project-assistant

项目全能助手，支持 60+ 项目类型，提供智能问答、文档沉淀、飞书集成、安全扫描、AST分析。

## 触发条件

TRIGGER when: 用户询问项目相关问题：
- "这个项目的架构是什么？"
- "XXX功能是怎么实现的？"
- "如何构建/运行这个项目？"
- "修改XXX会影响什么？"
- "扫描项目敏感信息"
- "生成架构图/时序图"
- "分析代码质量"

## 角色视角

| 问题类型 | 角色 | 关注点 |
|---------|------|-------|
| 架构设计 | 架构师 | 系统架构、扩展性 |
| 功能实现 | 开发工程师 | 代码逻辑、调试 |
| 项目进度 | 项目经理 | 里程碑、风险点 |
| 测试质量 | 测试工程师 | 测试用例、覆盖率 |
| 部署运维 | DevOps | 部署流程、环境配置 |

---

## 命令索引

### 配置管理

| 命令 | 说明 | 详细指南 |
|------|------|---------|
| `/set-config <key> <value>` | 设置配置项 | `{baseDir}/references/guides/config.md` |
| `/get-config <key>` | 获取配置项 | - |
| `/show-config` | 显示所有配置 | - |
| `/delete-config <key>` | 删除配置项 | - |

**CLI 命令**：
```bash
python3 {baseDir}/scripts/cli.py config set workdir /path/to/project
python3 {baseDir}/scripts/cli.py config get workdir
python3 {baseDir}/scripts/cli.py config show
python3 {baseDir}/scripts/cli.py config delete workdir
```

### 项目初始化

| 命令 | 说明 | 详细指南 |
|------|------|---------|
| `/init [目录] [选项]` | 初始化项目 | `{baseDir}/references/guides/init.md` |

### 问答文档

| 命令 | 说明 | 详细指南 |
|------|------|---------|
| `/qa [问题] [答案]` | 记录问答（智能模式） | `{baseDir}/references/guides/qa.md` |
| `/search-qa <关键词>` | 搜索历史问答 | - |
| `/list-qa [分类]` | 列出问答文档 | - |
| `/check-qa` | 检查文档过期 | - |
| `/delete-qa <id>` | 删除问答文档 | - |

**智能记录模式**：
- 无参数调用 `/qa`：记录最近一次问答
- 只提供问题：Claude 自动提取答案
- 完整参数：直接创建文档

**CLI 命令**：
```bash
# 列出所有问答
python3 {baseDir}/scripts/cli.py qa --list

# 检查过期问答
python3 {baseDir}/scripts/cli.py qa --check

# 删除问答
python3 {baseDir}/scripts/cli.py qa --delete <qa_id>

# 搜索问答
python3 {baseDir}/scripts/cli.py qa --search "关键词"
```

### 飞书集成

| 命令 | 说明 | 详细指南 |
|------|------|---------|
| `/feishu-report` | 生成更新建议 | `{baseDir}/references/guides/feishu.md` |
| `/feishu-status` | 检查同步状态 | - |
| `/feishu-suggest <file> <type>` | 生成文档建议 | - |

### 安全与监控

| 命令 | 说明 | 示例 |
|------|------|------|
| `/scan-security` | 扫描敏感信息 | 检测密码、密钥、证书等 |
| `/audit-log [limit]` | 查看审计日志 | 最近操作记录 |
| `/watch` | 启动文件监控 | 实时增量更新 |
| `/git-changes` | 查看 Git 变更 | 未提交/未推送的变更 |

### 代码分析

| 命令 | 说明 | 示例 |
|------|------|------|
| `/analyze-deps` | 依赖分析 | 循环依赖、版本冲突 |
| `/analyze-code [文件]` | 代码质量分析 | 代码异味、安全问题 |
| `/parse-ast [文件]` | AST 结构解析 | 函数、类、导入提取 |
| `/call-chain <函数>` | 调用链分析 | 函数调用关系 |

### 图表生成

| 命令 | 说明 | 输出格式 |
|------|------|---------|
| `/diagram architecture` | 架构图 | Mermaid |
| `/diagram sequence [函数]` | 时序图 | Mermaid |
| `/diagram dependency` | 依赖图 | Mermaid |
| `/diagram class [类名]` | 类图 | Mermaid |

**CLI 命令**：
```bash
# 架构图
python3 {baseDir}/scripts/cli.py diagram architecture .

# 时序图（指定函数）
python3 {baseDir}/scripts/cli.py diagram sequence . --function main

# 类图（指定类名）
python3 {baseDir}/scripts/cli.py diagram class . --class-name User

# 依赖图
python3 {baseDir}/scripts/cli.py diagram dependency .
```

### 知识图谱

| 命令 | 说明 |
|------|------|
| `/kg-link <qa_id> <文件>` | 关联问答与代码 |
| `/kg-outdated` | 检查过期问答 |
| `/kg-related <文件>` | 获取相关问答 |

### 缓存管理

| 命令 | 说明 |
|------|------|
| `/cache check` | 检查缓存有效性 |
| `/cache update` | 更新缓存 |
| `/cache clear` | 清除缓存 |
| `/cache info` | 查看缓存信息 |

**CLI 命令**：
```bash
python3 {baseDir}/scripts/cli.py cache check
python3 {baseDir}/scripts/cli.py cache update
python3 {baseDir}/scripts/cli.py cache info
```

---

## 执行流程

### Step 0: 安全检查（首次初始化时自动执行）

首次 `/init` 时自动执行敏感信息扫描：

```bash
python3 {baseDir}/scripts/cli.py scan-security "$PROJECT_DIR"
```

⚠️ **安全扫描策略**：
- **首次 `/init`**：强制执行
- **后续分析**：可选执行
- **发现敏感信息**：自动脱敏或警告排除

### Step 1: 确定项目目录

优先级：命令行参数 > 配置的 workdir > 当前目录

```bash
python3 {baseDir}/scripts/cli.py config get workdir
```

### Step 2: 检查项目文档

检查 `$PROJECT_DIR/.projmeta/project.md` 是否存在，不存在则调用 `/init`。

### Step 3: 搜索历史问答

```bash
python3 {baseDir}/scripts/cli.py search-qa "$QUERY"
```

**语义增强**：使用 BM25 + 中文分词，提升匹配准确率

### Step 4: 分析并回答

根据问题意图选择回答策略：

| 意图 | 关键词 | 格式 |
|------|--------|------|
| LOCATION | 在哪、哪个文件 | 简洁路径 |
| EXPLAIN | 怎么实现、原理 | Markdown详情 |
| MODIFY | 如何修改 | 步骤指导 |
| IMPACT | 影响什么 | 影响树 |

### Step 5: 自动记录问答

**自动判断标准**：满足以下任一条件即自动记录

| 条件 | 示例 |
|------|------|
| 回答涉及代码文件 | "这个功能在 src/auth.py 实现" |
| 回答包含流程步骤 | "构建步骤：1. xxx 2. xxx" |
| 回答涉及架构设计 | "系统采用分层架构..." |
| 问题包含"怎么""如何""为什么" | "怎么实现登录？" |

**自动执行**：
```bash
python3 {baseDir}/scripts/cli.py qa --auto
```

---

## 内部优化（透明执行）

以下步骤由系统自动完成，用户无需关心：

### 缓存管理

项目分析结果自动缓存，变更时增量更新：

```bash
# 手动检查缓存（可选）
python3 {baseDir}/scripts/cli.py cache check

# 更新缓存（可选）
python3 {baseDir}/scripts/cli.py cache update
```

### 知识图谱关联

问答与代码自动关联，支持智能推荐：

```bash
# 查看相关问答
python3 {baseDir}/scripts/cli.py kg related --file "$FILE"
```

---

## ⚠️ 输出检查清单（MUST VERIFY）

初始化完成后，**必须**验证以下内容：

```
□ 输出路径正确：$PROJECT_DIR/.projmeta/project.md
□ 包含：基本信息表格（项目名称、类型、语言、框架等）
□ 包含：目录结构
□ 包含：模块划分
□ 包含：入口点
□ 包含：构建指南
□ 包含：配置文件
□ 格式符合模板：references/templates/project-template.md
```

**验证命令**：
```bash
python3 {baseDir}/scripts/validate_output.py "$PROJECT_DIR"
```

---

## 工具命令

### 统一命令入口（推荐）

```bash
# 使用统一 CLI 入口
python3 {baseDir}/scripts/cli.py <command> [options]

# 初始化项目（含安全扫描）
python3 {baseDir}/scripts/cli.py init "$PROJECT_DIR"

# 扫描敏感信息
python3 {baseDir}/scripts/cli.py scan-security "$PROJECT_DIR" --mask

# 启动文件监控
python3 {baseDir}/scripts/cli.py watch "$PROJECT_DIR"

# 查看 Git 变更
python3 {baseDir}/scripts/cli.py git-changes "$PROJECT_DIR"

# 依赖分析
python3 {baseDir}/scripts/cli.py analyze-deps "$PROJECT_DIR"

# 代码质量分析
python3 {baseDir}/scripts/cli.py analyze-code "$PROJECT_DIR"
python3 {baseDir}/scripts/cli.py analyze-code --file "$FILE"

# AST 解析
python3 {baseDir}/scripts/cli.py parse-ast --file "$FILE"
python3 {baseDir}/scripts/cli.py parse-ast --project "$PROJECT_DIR"

# 图表生成
python3 {baseDir}/scripts/cli.py diagram architecture "$PROJECT_DIR"
python3 {baseDir}/scripts/cli.py diagram sequence "$PROJECT_DIR" --function main
python3 {baseDir}/scripts/cli.py diagram dependency "$PROJECT_DIR"
python3 {baseDir}/scripts/cli.py diagram class "$PROJECT_DIR" --class-name User

# 知识图谱
python3 {baseDir}/scripts/cli.py kg outdated "$PROJECT_DIR"
python3 {baseDir}/scripts/cli.py kg related "$PROJECT_DIR" --file "$FILE"

# 搜索问答（语义匹配）
python3 {baseDir}/scripts/cli.py search-qa "$QUERY" "$PROJECT_DIR"

# 记录问答
python3 {baseDir}/scripts/cli.py qa "$PROJECT_DIR" --question "$QUESTION" --answer "$ANSWER"
python3 {baseDir}/scripts/cli.py qa "$PROJECT_DIR" --auto  # 自动记录最近问答

# 缓存管理
python3 {baseDir}/scripts/cli.py cache check "$PROJECT_DIR"
python3 {baseDir}/scripts/cli.py cache update "$PROJECT_DIR"

# 审计日志
python3 {baseDir}/scripts/cli.py audit-log "$PROJECT_DIR" --limit 20
```

---

## 子模块索引

按需加载详细指南，**触发条件**明确如下：

| 模块 | 路径 | 触发条件 |
|------|------|---------|
| 配置管理 | `{baseDir}/references/guides/config.md` | 使用 `/set-config`、`/get-config`、`/show-config` 时 |
| 项目初始化 | `{baseDir}/references/guides/init.md` | 首次 `/init` 或需要了解初始化流程时 |
| 问答文档 | `{baseDir}/references/guides/qa.md` | 使用 `/qa`、`/search-qa`、`/list-qa` 时 |
| 飞书集成 | `{baseDir}/references/guides/feishu.md` | 使用 `/feishu-report`、`/feishu-status` 时 |
| 示例对话 | `{baseDir}/references/guides/examples.md` | 需要参考完整使用示例时 |

---

## 项目类型支持

| 分类 | 类型 |
|------|------|
| 嵌入式MCU | STM32, ESP32, Arduino, Pico, Keil, IAR, PlatformIO |
| 嵌入式RTOS | FreeRTOS, Zephyr, RT-Thread |
| 嵌入式Linux | Yocto, Buildroot, OpenWrt, QNX |
| Android | 应用, NDK, AOSP |
| iOS | Swift, SwiftUI |
| Web前端 | React, Vue, Angular, Svelte, Next.js, Nuxt |
| Web后端 | Django, FastAPI, Flask, Spring, Go, Rust |
| 桌面应用 | Qt, Electron, Flutter, Tauri |
| 游戏开发 | Unity, Unreal, Godot |
| AI/ML | PyTorch, TensorFlow, Jupyter |
| 系统编程 | C/C++, Rust, Go, Bazel |

---

## 目录结构

```
project-assistant/
├── SKILL.md                    # 主入口（本文件）
├── scripts/                    # Python 工具脚本
│   ├── config_manager.py       # 配置管理器
│   ├── qa_doc_manager.py       # 问答文档管理器
│   ├── feishu_doc_manager.py   # 飞书文档管理器
│   ├── detector.py             # 项目类型探测器
│   ├── watcher.py              # 文件监控器
│   ├── ast_parser.py           # AST 解析器
│   ├── knowledge_graph.py      # 知识图谱
│   ├── qa_recommender.py       # 问答推荐
│   ├── template_engine.py      # 模板引擎
│   ├── diagram_generator.py    # 图表生成
│   ├── dependency_analyzer.py  # 依赖分析
│   ├── ai_analyzer.py          # AI 分析
│   ├── security/               # 安全模块
│   │   ├── sensitive_scanner.py    # 敏感信息扫描
│   │   ├── security_config.py      # 安全配置
│   │   └── audit_logger.py         # 审计日志
│   ├── parsers/                # 配置文件解析器
│   ├── analyzers/              # 代码分析器
│   └── utils/                  # 工具函数
│       ├── cache_manager.py    # 缓存管理
│       ├── qa_cache.py         # 问答缓存（含BM25）
│       ├── git_watcher.py      # Git 变更检测
│       └── call_chain_analyzer.py  # 调用链分析
├── references/
│   ├── templates/              # 子 Skill 模板
│   ├── guides/                 # 详细指南（按需加载）
│   └── template-config.yaml    # 项目类型配置
├── tests/                      # 测试套件
├── security-config.yaml        # 安全配置
└── README.md
```

## 依赖

### 必需依赖
- Python 3.6+
- PyYAML

### 可选依赖（推荐安装）

| 依赖 | 用途 | 安装命令 |
|------|------|---------|
| Git | 版本检测 | 系统安装 |
| watchdog | 文件监控 | `pip install watchdog` |
| jieba | 中文分词 | `pip install jieba` |
| rank_bm25 | 语义匹配 | `pip install rank_bm25` |
| tree-sitter | AST 解析 | `pip install tree-sitter tree-sitter-languages` |
| toml | TOML 解析 | `pip install toml` |

### 一键安装

```bash
pip install pyyaml watchdog jieba rank_bm25 tree-sitter tree-sitter-languages toml
```

## 许可证

MIT License