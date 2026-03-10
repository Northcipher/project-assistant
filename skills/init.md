# init (项目初始化)

项目初始化主入口。自动探测项目类型，分发到对应的分析子模块，生成项目文档。

## 使用方式

```
/init [目录路径] [选项]
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `目录路径` | 要初始化的项目目录 | 当前目录 |
| `--force` | 强制重新扫描，忽略缓存 | false |
| `--depth=N` | 扫描深度 | 3 |
| `--verbose` | 显示详细日志 | false |
| `--quick` | 快速模式，只扫描顶层 | false |

### 示例

```bash
# 初始化当前目录
/init

# 初始化指定目录
/init /path/to/project

# 强制重新扫描
/init --force

# 限制扫描深度
/init --depth=2
```

## 执行流程

### Step 1: 探测项目类型

运行探测器获取项目信息：

```bash
python3 ~/.claude/tools/init/detector.py "$TARGET_DIR"
```

探测器返回JSON格式：

```json
{
  "project_type": "android-app",
  "secondary_types": ["gradle-java"],
  "language": "kotlin",
  "build_system": "gradle",
  "entry_points": ["app/src/main/java/.../MainActivity.kt"],
  "config_files": ["build.gradle.kts", "AndroidManifest.xml"],
  "dependencies": [...],
  "modules": ["app", "core", "data"],
  "target_platform": "android",
  "confidence": 0.95
}
```

#### 项目类型优先级

当多个规则匹配时，按以下优先级选择：

1. **精确标识文件** (优先级 90-100)
   - `AndroidManifest.xml` → android-app
   - `*.xcodeproj` → ios
   - `*.ioc` → stm32

2. **构建配置文件** (优先级 80-90)
   - `build.gradle` + 目录结构 → android-app
   - `pom.xml` → maven
   - `package.json` + 框架特征 → react/vue/angular

3. **目录结构特征** (优先级 60-80)
   - `frameworks/`, `system/` → aosp
   - `Assets/`, `ProjectSettings/` → unity

#### 歧义处理

当项目类型无法确定时：

```
检测到多个可能的项目类型:
  1. react (置信度: 0.85)
  2. nextjs (置信度: 0.80)

请选择项目类型 [1/2/a(uto)]:
```

选择 `auto` 会自动选择置信度最高的类型。

### Step 2: 加载对应子模块

根据 `project_type` 加载子skill：

| project_type | 子skill | 说明 |
|-------------|---------|------|
| `android-app` | `mobile/android.md` | Android 应用 |
| `android-ndk` | `embedded/android-native.md` | Android NDK |
| `aosp` | `embedded/android-native.md` | AOSP 系统源码 |
| `ios` | `mobile/ios.md` | iOS 应用 |
| `stm32`, `esp32`, `pico`, `keil`, `iar` | `embedded/mcu.md` | MCU 嵌入式 |
| `freertos`, `zephyr`, `rt-thread` | `embedded/rtos.md` | RTOS 项目 |
| `embedded-linux`, `buildroot`, `yocto` | `embedded/linux.md` | 嵌入式 Linux |
| `qnx` | `embedded/qnx.md` | QNX 系统 |
| `react`, `vue`, `angular`, `svelte`, `nextjs`, `nuxt` | `web/frontend.md` | Web 前端 |
| `django`, `fastapi`, `flask` | `web/backend.md` | Web 后端 |
| `electron`, `qt` | `desktop/desktop.md` | 桌面应用 |
| `cmake`, `makefile`, `go`, `rust` | `system/native.md` | 原生/系统项目 |
| `flutter` | `desktop/desktop.md` | Flutter 应用 |
| 未知类型 | 使用通用模板分析 | 通用项目 |

#### 子模块加载失败处理

```
[警告] 子模块 mobile/android.md 不存在
[回退] 使用通用模板进行分析
```

### Step 3: 执行分析

子skill负责：

1. **详细分析项目结构**
   - 目录树生成
   - 模块划分识别
   - 关键目录标注

2. **解析配置文件** (可调用Python工具)
   ```bash
   python3 ~/.claude/tools/init/parsers/gradle_parser.py "$PROJECT_DIR"
   python3 ~/.claude/tools/init/parsers/cmake_parser.py "$PROJECT_DIR"
   python3 ~/.claude/tools/init/parsers/package_json_parser.py "$PROJECT_DIR"
   ```

3. **提取核心功能**
   - 入口点分析
   - 主要模块功能推断
   - API 端点识别

4. **生成项目文档**
   - 输出到 `.claude/project.md`

### Step 4: 输出结果

在目标目录生成 `.claude/project.md`

#### 进度显示

```
[1/4] 探测项目类型... ✓ android-app (置信度: 95%)
[2/4] 分析项目结构... ████████████████████ 100%
[3/4] 解析配置文件... ✓ build.gradle.kts, AndroidManifest.xml
[4/4] 生成项目文档... ✓ .claude/project.md

完成！项目文档已生成。
```

#### 分层文档结构

采用**分层 + 索引**架构，优化 Token 消耗：

```
.claude/
├── project.md           # L0: 项目概览 (~1-2KB)
├── index/               # 数据索引（JSON 格式）
│   ├── subsystems.json  # 子系统索引
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

#### L0: project.md 内容（精简版）

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

#### Token 消耗对比

| 项目规模 | 优化前 project.md | 优化后 L0 | 节省 |
|---------|------------------|----------|------|
| 小型 | 5-10 KB | 1-2 KB | 80% |
| 中型 | 20-50 KB | 2-3 KB | 90% |
| 大型 | 50-100 KB | 3-5 KB | 95% |

#### 文档生成命令

```bash
# 生成 L0 项目概览
python3 ~/.claude/tools/init/utils/doc_generator.py l0 "$PROJECT_DIR"

# 生成 L1 子系统文档（按需）
python3 ~/.claude/tools/init/utils/doc_generator.py l1 "$PROJECT_DIR" "vehicle"

# 生成 L2 进程详情（按需）
python3 ~/.claude/tools/init/utils/doc_generator.py l2-process "$PROJECT_DIR" "vehicle" "vehicle_service"

# 生成 L2 IPC 文档（按需）
python3 ~/.claude/tools/init/utils/doc_generator.py l2-ipc "$PROJECT_DIR"

# 查看文档结构
python3 ~/.claude/tools/init/utils/doc_generator.py structure "$PROJECT_DIR"
```

## 大型项目处理策略
| adas_core | adas | `adas/core/main.cpp` | Socket |

## 大型项目处理策略

### 自动检测项目规模

```bash
# detector.py 返回规模信息
{
  "project_type": "embedded-linux",
  "scale": "large",
  "file_count": 15000,
  "subsystems": ["vehicle", "infotainment", "adas"],
  "processes": ["vehicle_service", "media_server", "adas_core"],
  "ipc_protocols": ["binder", "dbus", "socket"]
}
```

### 懒加载详细文档

对于大型项目，详细文档**按需生成**：

```
用户问: "vehicle_service 进程是怎么实现的？"

系统:
1. 检查 .claude/docs/subsystems/vehicle/vehicle_service.md 是否存在
2. 不存在 → 分析代码 → 生成文档 → 缓存
3. 返回答案
```

### IPC 通信分析

```bash
python3 ~/.claude/tools/init/analyzers/ipc_analyzer.py "$PROJECT_DIR"
```

## 缓存机制

### 缓存位置

`.claude/cache.json`

### 缓存有效性检查

```bash
python3 ~/.claude/tools/init/utils/cache_manager.py check "$PROJECT_DIR"
```

缓存失效条件：

| 条件 | 说明 |
|------|------|
| 配置文件变更 | package.json, CMakeLists.txt 等被修改 |
| Git 有未提交变更 | 存在 modified/added/deleted 文件 |
| 新的提交 | HEAD 改变 |
| TTL 过期 | 默认 1 小时 |

### 缓存更新

```bash
# 检查并更新缓存
python3 ~/.claude/tools/init/utils/cache_manager.py update "$PROJECT_DIR"

# 增量更新（保留部分缓存）
python3 ~/.claude/tools/init/utils/cache_manager.py update "$PROJECT_DIR" --incremental

# 清除缓存
python3 ~/.claude/tools/init/utils/cache_manager.py clear "$PROJECT_DIR"
```

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 项目目录不存在 | 返回错误：`Directory not found: {path}` |
| 无法识别项目类型 | 提示用户选择或使用通用模板 |
| 子 skill 不存在 | 回退到通用模板，记录警告 |
| 配置文件解析失败 | 跳过该文件，继续其他分析 |
| 权限不足 | 跳过无法访问的目录 |
| 超大项目 | 自动限制扫描深度和文件数量 |

### 错误示例

```
[错误] 无法解析 build.gradle.kts
  - 原因: 语法错误于第 45 行
  - 跳过该文件，继续分析

[警告] 扫描深度达到限制 (depth=3)
  - 部分深层目录未扫描
  - 使用 --depth=N 增加深度
```

## 大型项目优化

### 自动限制

对于大型项目（文件数 > 10000 或目录数 > 1000）：

- 自动限制扫描深度到 2
- 跳过 `node_modules`, `build`, `.gradle` 等目录
- 只解析顶层配置文件

### 手动控制

```bash
# 快速模式：只扫描顶层
/init --quick

# 限制深度
/init --depth=2

# 详细输出（用于调试）
/init --verbose
```

## 敏感信息处理

- `.env` 等敏感文件只标注存在，不暴露内容
- API 密钥、密码等自动脱敏
- 生产环境配置仅记录结构

## 示例输出

### Android 项目

```
[1/4] 探测项目类型... ✓ android-app
[2/4] 分析项目结构... ✓ 3 个模块
[3/4] 解析配置文件... ✓ build.gradle.kts, AndroidManifest.xml
[4/4] 生成项目文档... ✓

项目: MyAndroidApp
类型: android-app
语言: Kotlin
目标: Android API 34

入口点:
  - app/src/main/java/com/example/MainActivity.kt

构建命令:
  - ./gradlew assembleDebug
  - ./gradlew assembleRelease
```

### React 项目

```
[1/4] 探测项目类型... ✓ react
[2/4] 分析项目结构... ✓ src/, components/, hooks/
[3/4] 解析配置文件... ✓ package.json, tsconfig.json
[4/4] 生成项目文档... ✓

项目: my-react-app
类型: react
语言: TypeScript
构建: Vite

技术栈:
  - React 18
  - TypeScript 5
  - TailwindCSS
  - Zustand

入口点:
  - src/main.tsx

脚本:
  - npm run dev
  - npm run build
  - npm test
```

### 嵌入式项目

```
[1/4] 探测项目类型... ✓ stm32
[2/4] 分析项目结构... ✓ Core/, Drivers/, Middlewares/
[3/4] 解析配置文件... ✓ *.ioc, Makefile
[4/4] 生成项目文档... ✓

项目: STM32F4_Project
类型: stm32
语言: C
MCU: STM32F407VG

工具链:
  - STM32CubeIDE
  - ARM GCC

外设:
  - GPIO, UART, SPI, I2C
  - TIM, ADC, DMA

构建:
  - make all
  - make flash
```