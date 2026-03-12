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

### 项目初始化

| 命令 | 说明 | 详细指南 |
|------|------|---------|
| `/init [目录] [选项]` | 初始化项目 | `{baseDir}/references/guides/init.md` |

### 问答文档

| 命令 | 说明 | 详细指南 |
|------|------|---------|
| `/search-qa <关键词>` | 搜索历史问答 | `{baseDir}/references/guides/qa.md` |
| `/list-qa [分类]` | 列出问答文档 | - |
| `/check-qa` | 检查文档过期 | - |
| `/delete-qa <id>` | 删除问答文档 | - |

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

### 知识图谱

| 命令 | 说明 |
|------|------|
| `/kg-link <qa_id> <文件>` | 关联问答与代码 |
| `/kg-outdated` | 检查过期问答 |
| `/kg-related <文件>` | 获取相关问答 |

---

## 执行流程

### Step 0: 安全检查（可选）

**首次分析前**执行敏感信息扫描：

```bash
# 扫描敏感信息
python3 {baseDir}/scripts/security/sensitive_scanner.py "$PROJECT_DIR"

# 发现敏感信息时的处理：
# 1. 警告用户并建议排除
# 2. 自动脱敏后继续分析
# 3. 记录审计日志
```

### Step 1: 确定项目目录（REQUIRED）

```bash
# 读取配置的工作目录
python3 {baseDir}/scripts/config_manager.py {baseDir} get workdir
```

优先级：命令行参数 > 配置的 workdir > 当前目录

### Step 2: 检查项目文档（REQUIRED）

**必须**检查 `$PROJECT_DIR/.projmeta/project.md` 是否存在。

```bash
# 检查文档是否存在
if [ ! -f "$PROJECT_DIR/.projmeta/project.md" ]; then
    # 不存在则调用 /init 生成
    # 详见 references/guides/init.md
fi
```

⚠️ **输出路径强制要求**：
- **唯一正确路径**: `$PROJECT_DIR/.projmeta/project.md`
- **禁止**输出到项目根目录
- **禁止**输出到其他任意位置

### Step 3: 智能缓存检查（REQUIRED）

根据问题类型决定缓存检查策略：

| 问题类型 | 检查策略 | 原因 |
|---------|---------|------|
| LOCATION | 跳过 | 直接搜索即可 |
| CONFIG | 快速 | 只检查时间戳 |
| ARCHITECTURE | 完整 | 需要最新数据 |
| IMPACT | 强制 | 必须最新 |

```bash
python3 {baseDir}/scripts/utils/cache_manager.py check "$PROJECT_DIR" --quick
```

**增量更新**：检测 Git 变更，只更新变更部分

```bash
# 获取变更文件
python3 {baseDir}/scripts/utils/git_watcher.py "$PROJECT_DIR" changes

# 增量更新缓存
python3 {baseDir}/scripts/utils/cache_manager.py incremental "$PROJECT_DIR"
```

### Step 4: 搜索历史问答（REQUIRED）

```bash
python3 {baseDir}/scripts/qa_doc_manager.py "$PROJECT_DIR" search "$QUERY"
```

**语义增强**：使用 BM25 + 中文分词，提升匹配准确率

```bash
# 语义相似度搜索（更精准）
python3 {baseDir}/scripts/utils/qa_cache.py get "$PROJECT_DIR" "$QUERY"
```

匹配策略：
- 精确匹配：问题原文包含关键词
- 语义匹配：BM25 算法计算相似度
- 意图匹配：问题类型（LOCATION/EXPLAIN/MODIFY）加分

### Step 5: 分析并回答

根据问题意图选择回答策略：

| 意图 | 关键词 | 格式 |
|------|--------|------|
| LOCATION | 在哪、哪个文件 | 简洁路径 |
| EXPLAIN | 怎么实现、原理 | Markdown详情 |
| MODIFY | 如何修改 | 步骤指导 |
| IMPACT | 影响什么 | 影响树 |

### Step 6: 沉淀问答文档（REQUIRED）

```bash
python3 {baseDir}/scripts/qa_doc_manager.py "$PROJECT_DIR" create "$QUESTION" "$ANSWER" "$FILES" "$TAGS"
```

### Step 7: 知识图谱关联（可选）

将问答与代码、测试关联，支持后续智能推荐：

```bash
# 关联问答与代码文件
python3 {baseDir}/scripts/knowledge_graph.py "$PROJECT_DIR" link "$QA_ID" "$FILE_PATHS"

# 记录审计日志
python3 {baseDir}/scripts/security/audit_logger.py "$PROJECT_DIR" log "qa_create" "$QA_ID"
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
python3 {baseDir}/scripts/cli.py diagram dependency "$PROJECT_DIR"

# 知识图谱
python3 {baseDir}/scripts/cli.py kg outdated "$PROJECT_DIR"
python3 {baseDir}/scripts/cli.py kg related "$PROJECT_DIR" --file "$FILE"

# 搜索问答（语义匹配）
python3 {baseDir}/scripts/cli.py search-qa "$QUERY" "$PROJECT_DIR"

# 审计日志
python3 {baseDir}/scripts/cli.py audit-log "$PROJECT_DIR" --limit 20
```

### 独立脚本调用

```bash
# 配置管理
python3 {baseDir}/scripts/config_manager.py {baseDir} <get|set|delete|show> [args]

# 项目探测
python3 {baseDir}/scripts/detector.py "$PROJECT_DIR"

# 问答文档
python3 {baseDir}/scripts/qa_doc_manager.py "$PROJECT_DIR" <search|list|check|create|delete> [args]

# 飞书集成
python3 {baseDir}/scripts/feishu_doc_manager.py "$PROJECT_DIR" <report|status|suggest> [args]

# 缓存管理
python3 {baseDir}/scripts/utils/cache_manager.py <check|update|clear> "$PROJECT_DIR"

# 调用链分析
python3 {baseDir}/scripts/utils/call_chain_analyzer.py "$PROJECT_DIR" "$FUNCTION" --impact

# 输出校验（MUST）
python3 {baseDir}/scripts/validate_output.py "$PROJECT_DIR"

# 安全扫描
python3 {baseDir}/scripts/security/sensitive_scanner.py "$PROJECT_DIR" [--mask]

# 审计日志
python3 {baseDir}/scripts/security/audit_logger.py "$PROJECT_DIR" tail [limit]

# 文件监控
python3 {baseDir}/scripts/watcher.py "$PROJECT_DIR" [--daemon]

# Git 变更检测
python3 {baseDir}/scripts/utils/git_watcher.py "$PROJECT_DIR" changes

# 依赖分析
python3 {baseDir}/scripts/dependency_analyzer.py "$PROJECT_DIR"

# 代码质量分析
python3 {baseDir}/scripts/ai_analyzer.py "$PROJECT_DIR" --project
python3 {baseDir}/scripts/ai_analyzer.py "$FILE"  # 单文件分析

# AST 解析
python3 {baseDir}/scripts/ast_parser.py parse "$FILE"
python3 {baseDir}/scripts/ast_parser.py project "$PROJECT_DIR"

# 图表生成
python3 {baseDir}/scripts/diagram_generator.py architecture "$PROJECT_DIR"
python3 {baseDir}/scripts/diagram_generator.py sequence "$CALL_CHAIN.json"
python3 {baseDir}/scripts/diagram_generator.py dependency "$DEPS.json"

# 知识图谱
python3 {baseDir}/scripts/knowledge_graph.py "$PROJECT_DIR" <link|outdated|related> [args]

# 语义相似度（BM25）
python3 {baseDir}/scripts/utils/qa_cache.py search "$PROJECT_DIR" "$QUERY"
```

---

## 子模块索引

按需加载详细指南：

| 模块 | 路径 | 内容 |
|------|------|------|
| 配置管理 | `{baseDir}/references/guides/config.md` | 配置项详细说明 |
| 项目初始化 | `{baseDir}/references/guides/init.md` | 初始化流程详解 |
| 问答文档 | `{baseDir}/references/guides/qa.md` | 问答功能详解 |
| 飞书集成 | `{baseDir}/references/guides/feishu.md` | 飞书协作详解 |
| 示例对话 | `{baseDir}/references/guides/examples.md` | 完整示例 |

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