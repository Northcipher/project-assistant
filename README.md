# Project Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

OpenClaw 项目分析工具集，提供项目初始化和智能问答功能。

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

```
用户: /init
助手: [1/4] 探测项目类型... ✓ react (置信度: 95%)
      [2/4] 分析项目结构... ✓
      [3/4] 解析配置文件... ✓ package.json, tsconfig.json
      [4/4] 生成项目文档... ✓ .claude/project.md

用户: 登录功能是怎么实现的？
助手: ## 登录实现
      通过 `AuthService` + `JwtUtil` 实现...

用户: main函数在哪里？
助手: `src/main.ts:15`
```

## 特性

| 特性 | 说明 |
|------|------|
| **50+ 项目类型** | 嵌入式、移动端、Web、桌面、系统编程 |
| **分层文档** | L0/L1/L2 三级，节省 80-95% Token |
| **Q&A 缓存** | 缓存命中 Token 消耗接近 0 |
| **IPC 分析** | Binder/DBus/gRPC/SOME/IP/Socket |
| **大型项目** | 自动检测规模、子系统、进程 |

## 支持的项目类型

| 分类 | 类型 |
|------|------|
| 嵌入式 MCU | STM32, ESP32, Arduino, Pico, Keil, IAR |
| 嵌入式 RTOS | FreeRTOS, Zephyr, RT-Thread |
| 嵌入式 Linux | Yocto, Buildroot, OpenWrt, QNX |
| Android | 应用, NDK, AOSP |
| iOS | Swift, SwiftUI |
| Web 前端 | React, Vue, Angular, Svelte, Next.js |
| Web 后端 | Django, FastAPI, Flask, Spring |
| 桌面应用 | Qt, Electron, Flutter |
| 系统编程 | C/C++, Rust, Go |

## 目录结构

```
project-assistant/
├── SKILL.md              # 主入口（YAML frontmatter）
├── scripts/              # Python 工具脚本
│   ├── detector.py       # 项目类型探测器
│   ├── parsers/          # 配置文件解析器
│   ├── analyzers/        # 代码分析器
│   └── utils/            # 工具函数
├── references/templates/ # 子 Skill 模板
└── tests/                # 测试套件
```

## 依赖

- Python 3.6+
- Git（可选）
- PyYAML（可选，CI/CD 解析）

## 许可证

[MIT License](LICENSE)