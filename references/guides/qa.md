# 问答文档管理指南

## 命令

| 命令 | 说明 |
|------|------|
| `/qa record --question <问题> --answer <答案>` | 记录问答（推荐） |
| `/qa --auto` | 记录最近一次问答 |
| `/search-qa <关键词>` | 搜索历史问答 |
| `/list-qa [分类]` | 列出问答文档 |
| `/check-qa` | 检查文档是否过期 |
| `/delete-qa <id>` | 删除问答文档 |

## CLI 命令

```bash
# 记录问答（推荐）
python3 {baseDir}/scripts/cli.py qa --record --question "问题" --answer "答案"

# 自动记录最近问答
python3 {baseDir}/scripts/cli.py qa --auto

# 搜索问答
python3 {baseDir}/scripts/cli.py qa --search "关键词"

# 列出问答
python3 {baseDir}/scripts/cli.py qa --list --category feature

# 检查过期
python3 {baseDir}/scripts/cli.py qa --check

# 删除问答
python3 {baseDir}/scripts/cli.py qa --delete <id>
```

## 文档分类

| 分类 | 说明 | 关键词 |
|------|------|--------|
| `architecture` | 架构设计 | 架构、设计、结构、分层 |
| `build` | 构建配置 | 编译、构建、make、cmake |
| `feature` | 功能实现 | 怎么实现、如何、功能、原理 |
| `debug` | 问题调试 | 报错、错误、调试、为什么 |
| `api` | 接口说明 | 接口、API、函数、参数 |
| `module` | 模块说明 | 模块、组件、目录 |
| `process` | 流程说明 | 流程、步骤、启动、初始化 |
| `other` | 其他 | - |

## 文档结构

```
项目目录/.projmeta/
├── index/qa_index.json    # 问答索引
└── docs/qa/               # 问答文档
    ├── architecture/
    ├── build/
    ├── feature/
    ├── debug/
    ├── api/
    ├── module/
    ├── process/
    └── other/
```

## 过期检测

自动检测两种过期情况：
1. **Git Commit 变化** - 代码有新提交
2. **文件哈希变化** - 相关文件被修改

## 示例

```bash
# 记录问答
python3 {baseDir}/scripts/cli.py qa --record --question "登录功能怎么实现？" --answer "通过 AuthService 实现..."

# 搜索 WiFi 相关问答
python3 {baseDir}/scripts/cli.py qa --search "WiFi"

# 列出架构类问答
python3 {baseDir}/scripts/cli.py qa --list --category architecture

# 检查文档过期
python3 {baseDir}/scripts/cli.py qa --check
```