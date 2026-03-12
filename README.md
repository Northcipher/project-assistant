# Project Assistant 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 为 OpenClaw 设计的项目分析工具集，群聊单聊都能用！

---

## ✨ 亮点速览

### 💰 Token 消耗直接砍掉 80%-95%！

传统方式一次性加载整个项目文档，动辄 5-10 万 Token 😱

我们采用**分层文档架构 + 增量更新**：

| 对比项 | Token 消耗 | 省了多少 |
|--------|-----------|---------|
| 传统一次性文档 | 50,000-100,000 | - |
| 我们 L0 概览 | ~11,500 | **77-88%** |
| 增量更新（新功能）| ~500-2,000 | **80-95%** |
| 后续问答缓存命中 | ~0 | **接近 100%** |

### 🎯 60+ 项目类型一键识别

| 分类 | 支持类型 |
|------|---------|
| 嵌入式 MCU | STM32, ESP32, Arduino, Pico, Keil, IAR, PlatformIO |
| 嵌入式 RTOS | FreeRTOS, Zephyr, RT-Thread |
| 嵌入式 Linux | Yocto, Buildroot, OpenWrt, QNX |
| Android | 应用, NDK, AOSP |
| iOS | Swift, SwiftUI |
| Web 前端 | React, Vue, Angular, Svelte, Next.js, Nuxt |
| Web 后端 | Django, FastAPI, Flask, Spring, Go, Rust |
| 桌面应用 | Qt, Electron, Flutter, Tauri |
| 游戏开发 | Unity, Unreal, Godot |
| AI/ML | PyTorch, TensorFlow, Jupyter |
| 系统编程 | C/C++, Rust, Go, Bazel |

### 🆕 v2.0 新功能

| 功能 | 说明 |
|------|------|
| 🔐 安全体系 | 敏感信息自动扫描/脱敏，审计日志可追溯 |
| ⚡ 增量更新 | 只处理变更文件，无需全量扫描 |
| 🧠 语义问答 | BM25 + Jieba 语义匹配，准确率 90%+ |
| 🔬 AST 分析 | Tree-sitter 深度解析，支持 8 种语言 |
| 📊 图表生成 | Mermaid 架构图、时序图、依赖图 |
| 🔗 知识图谱 | 问答关联代码/测试，自动过期检测 |

---

## 🛠️ 核心功能

| 功能 | 说明 |
|------|------|
| 🤖 智能问答 | 自动识别问题类型，精准回答 |
| 📝 问答沉淀 | 自动生成文档，Git变更检测，过期提醒 |
| 📋 飞书集成 | 与飞书 Skill 协作，生成文档更新建议 |
| 🔗 调用链分析 | 支持 8 种语言，函数调用一追到底 |
| 📡 IPC 分析 | Binder/DBus/gRPC/SOME/IP/Socket |
| ⚡ 影响分析 | 改代码前就知道会影响谁 |
| 🏗️ 大型项目 | 自动识别子系统、进程、IPC 协议 |
| 💾 智能缓存 | 相似问题秒回，Token 省到底 |
| 🔒 安全扫描 | 敏感信息检测与自动脱敏 |

---

## 📦 快速开始

### 安装

```bash
# ClawHub 安装（推荐）
claw install project-assistant

# 手动安装
git clone https://github.com/Northcipher/project-assistant.git ~/.claude/skills/project-assistant
```

### 安装依赖

```bash
# 核心依赖
pip install pyyaml

# 可选依赖（推荐安装）
pip install watchdog jieba rank_bm25 tree-sitter tree-sitter-languages toml
```

### 基本使用

```
/set-workdir /path/to/project    # 设置工作目录（跨会话有效）
/init                            # 初始化项目
/search-qa WiFi                  # 搜索历史问答
/check-qa                        # 检查问答文档是否过期
```

---

## 🏗️ 架构设计

### 分层文档结构

```
.projmeta/
├── project.md           # L0: 项目概览 (~1-2KB)
├── index/               # 数据索引 (JSON)
├── docs/                # 详细文档（按需生成）
├── cache.json           # 分析缓存
├── qa_cache.json        # Q&A 缓存
├── knowledge_graph.json # 知识图谱
└── audit.log            # 审计日志
```

### 核心模块

```
scripts/
├── security/           # 安全模块（敏感扫描、审计日志）
├── watcher.py          # 文件监控
├── ast_parser.py       # AST 解析器
├── knowledge_graph.py  # 知识图谱
├── diagram_generator.py # 图表生成
├── dependency_analyzer.py # 依赖分析
├── ai_analyzer.py      # AI 增强分析
├── parsers/            # 14 个配置文件解析器
├── analyzers/          # 9 个代码分析器
└── utils/              # 工具函数
```

---

## 📁 详细文档

- [DOCS.md](DOCS.md) - 完整开发者文档
- [references/guides/](references/guides/) - 使用指南

---

## 📋 更新日志

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

---

## 📦 依赖

| 依赖 | 用途 | 必须 |
|------|------|------|
| Python 3.6+ | 运行环境 | ✅ |
| PyYAML | YAML 解析 | ✅ |
| Git | 版本检测 | ❌ |
| watchdog | 文件监控 | ❌ |
| jieba | 中文分词 | ❌ |
| rank_bm25 | 语义匹配 | ❌ |
| tree-sitter | AST 解析 | ❌ |

---

## 📜 许可证

[MIT License](LICENSE)

---

**#OpenClaw #项目分析 #AI助手 #代码分析 #开发工具**