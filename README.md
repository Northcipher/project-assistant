# Project Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

为 OpenClaw 设计的项目分析工具集，提供项目初始化和智能问答功能。

## 为什么选择 Project Assistant？

### 节省 80-95% Token 消耗

传统方式一次性加载整个项目文档，消耗 50,000-100,000 Token。Project Assistant 采用**分层文档架构**：

| 方式 | Token 消耗 | 节省 |
|------|-----------|------|
| 传统一次性文档 | 50,000-100,000 | - |
| Project Assistant L0 | ~11,500 | **77-88%** |
| 后续问答（缓存命中） | ~0 | **接近 100%** |

### 50+ 项目类型支持

| 分类 | 支持类型 |
|------|---------|
| 嵌入式 MCU | STM32, ESP32, Arduino, Pico, Keil, IAR |
| 嵌入式 RTOS | FreeRTOS, Zephyr, RT-Thread |
| 嵌入式 Linux | Yocto, Buildroot, OpenWrt, QNX |
| Android | 应用, NDK, AOSP |
| iOS | Swift, SwiftUI |
| Web 前端 | React, Vue, Angular, Svelte, Next.js |
| Web 后端 | Django, FastAPI, Flask, Spring |
| 桌面应用 | Qt, Electron, Flutter |
| 系统编程 | C/C++, Rust, Go |

### 核心功能

- **智能问答** - 自动识别问题类型，提供精准回答
- **调用链分析** - 支持 7 种语言的函数调用追踪
- **IPC 分析** - Binder/DBus/gRPC/SOME/IP/Socket
- **影响分析** - 修改代码前预知影响范围
- **大型项目支持** - 自动检测子系统、进程、IPC 协议

## 快速开始

### 安装

```bash
# 通过 ClawHub 安装（推荐）
claw install project-assistant

# 或手动安装
git clone https://github.com/Northcipher/project-assistant.git ~/.claude/skills/project-assistant
```

### 使用

```
/init                    # 初始化当前项目
/init /path/to/project   # 初始化指定项目
/project-assistant       # 项目问答模式
```

### 示例

**初始化项目：**
```
用户: /init
助手: [1/4] 探测项目类型... ✓ react (置信度: 95%)
      [2/4] 分析项目结构... ✓ src/, components/, hooks/
      [3/4] 解析配置文件... ✓ package.json, tsconfig.json
      [4/4] 生成项目文档... ✓ .claude/project.md
```

**智能问答：**
```
用户: 登录功能是怎么实现的？
助手: ## 登录实现

      通过 `AuthService` + `JwtUtil` 实现，主要流程：

      1. 前端提交 → `LoginApi.login()`
      2. 后端验证 → `AuthService.authenticate()`
      3. Token生成 → `JwtUtil.createToken()`

      相关代码：
      - `src/pages/Login.tsx:45-78`
      - `src/api/auth.ts:23-56`

用户: main函数在哪里？
助手: `src/main.ts:15`

用户: 修改 login 函数会影响什么？
助手: ## 影响分析: login

      ### 直接调用者
      - `src/pages/Login.tsx:45` - handleLogin
      - `src/pages/Signup.tsx:78` - autoLogin
      - `src/utils/session.ts:12` - restoreSession

      ### 测试覆盖
      - `src/tests/auth.test.ts` - 3 个测试用例
```

## 飞书群聊场景

接入 OpenClaw 后，不同角色可在飞书群聊中使用：

### 开发工程师

```
@OpenClaw 登录功能在哪？
@OpenClaw 修改 handleLogin 会影响哪些地方？
@OpenClaw 调用链：从 main 到 UserService
```

快速定位代码、了解实现细节、评估修改影响。

### 测试工程师

```
@OpenClaw 登录模块有哪些测试用例？
@OpenClaw 测试覆盖率怎么样？
@OpenClaw 这个接口的边界条件是什么？
```

了解测试覆盖、查找测试用例、分析边界条件。

### 产品经理

```
@OpenClaw 这个项目有多少个模块？
@OpenClaw 支付功能实现了吗？
@OpenClaw 项目的技术栈是什么？
```

了解项目进度、功能实现情况、技术选型。

### 运维工程师

```
@OpenClaw 项目的 CI/CD 配置在哪？
@OpenClaw 需要哪些环境变量？
@OpenClaw 如何构建和部署？
```

了解部署配置、环境依赖、构建流程。

### 新人入职

```
@OpenClaw 帮我初始化这个项目
@OpenClaw 项目的架构是什么？
@OpenClaw 从哪里开始看代码？
```

快速上手项目，减少导师负担。

### 技术 Leader

```
@OpenClaw 这个模块的复杂度如何？
@OpenClaw 有哪些技术债务（TODO）？
@OpenClaw IPC 通信架构是怎样的？
```

架构评审、技术债务追踪、代码审查准备。

## 架构亮点

### 分层文档结构

```
.claude/
├── project.md           # L0: 项目概览 (~1-2KB)
├── index/               # 数据索引 (JSON)
│   ├── processes.json   # 进程索引
│   ├── ipc.json         # IPC 接口索引
│   └── structure.json   # 目录结构索引
├── docs/                # 详细文档（按需生成）
│   └── subsystems/      # 子系统文档
└── qa_cache.json        # Q&A 缓存
```

**按需生成**：详细文档只在需要时才生成，避免不必要的 Token 消耗。

### 缓存机制

缓存失效检测有多重保障，不会频繁重新分析：

- **Git 状态检测** - 有未提交变更时更新
- **配置文件变更** - package.json 等被修改时更新
- **提交变化** - HEAD commit 改变时更新
- **TTL 过期** - 默认 24 小时
- **Q&A 缓存** - 相似问题自动匹配，有效期 7 天

## 项目结构

```
project-assistant/
├── SKILL.md              # 主入口（YAML frontmatter）
├── scripts/              # Python 工具脚本
│   ├── detector.py       # 项目类型探测器
│   ├── parsers/          # 14 个配置文件解析器
│   ├── analyzers/        # 6 个代码分析器
│   └── utils/            # 工具函数
├── references/templates/ # 子 Skill 模板（11 个）
└── tests/                # 测试套件
```

## 依赖

- Python 3.6+
- Git（可选）
- PyYAML（可选，CI/CD 解析）

## 许可证

[MIT License](LICENSE)