# 项目初始化详细指南

## 命令

```
/init [目录] [选项]
```

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `目录` | 项目目录 | 当前目录 |
| `--force` | 强制重新扫描 | false |
| `--depth=N` | 扫描深度 | 3 |
| `--quick` | 快速模式 | false |

---

## ⚠️ 输出路径（强制要求）

**唯一正确路径**: `$PROJECT_DIR/.projmeta/project.md`

```
项目根目录/
└── .projmeta/
    └── project.md    ← 必须输出到这里
```

**禁止行为**:
- ❌ 输出到项目根目录（如 `PROJECT.md`、`project.md`）
- ❌ 输出到其他任意位置
- ❌ 更改文件名

---

## 执行流程

```bash
# 1. 探测项目类型
python3 {baseDir}/scripts/detector.py "$PROJECT_DIR"

# 2. 加载子模块
# 根据 project_type 加载 references/templates/ 下对应模板

# 3. 生成文档
# 输出到 .projmeta/project.md
```

---

## 模板格式（必须遵守）

生成的文档**必须**包含以下章节：

| 章节 | 必需 | 说明 |
|------|------|------|
| 基本信息 | ✅ | 项目名称、类型、语言、框架等 |
| 目录结构 | ✅ | 项目目录树 |
| 模块划分 | ✅ | 核心模块和工具模块 |
| 入口点 | ✅ | 主入口和其他入口 |
| 构建指南 | ✅ | 安装、构建、运行命令 |
| 配置文件 | ✅ | 配置项表格 |

详细模板格式见: `references/templates/project-template.md`

## 项目类型映射

| project_type | 模板 |
|-------------|------|
| `android-app` | `templates/mobile/android.md` |
| `ios` | `templates/mobile/ios.md` |
| `stm32/esp32/pico` | `templates/embedded/mcu.md` |
| `freertos/zephyr` | `templates/embedded/rtos.md` |
| `embedded-linux` | `templates/embedded/linux.md` |
| `qnx` | `templates/embedded/qnx.md` |
| `react/vue/angular` | `templates/web/frontend.md` |
| `django/fastapi` | `templates/web/backend.md` |
| `electron/qt` | `templates/desktop/desktop.md` |
| `cmake/makefile` | `templates/system/native.md` |

## 输出结构

```
.projmeta/
├── project.md           # L0 项目概览
├── index/               # 数据索引
│   ├── processes.json
│   ├── ipc.json
│   └── structure.json
├── docs/                # 详细文档（按需生成）
└── cache.json           # 缓存
```

## 大型项目处理

文件数 > 10000 时：
- 自动限制扫描深度到 2
- 跳过 `node_modules`, `build` 等
- 只解析顶层配置