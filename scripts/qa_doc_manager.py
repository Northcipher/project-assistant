#!/usr/bin/env python3
"""
问答文档管理器
将问答沉淀为文档，支持 Git 变更检测和智能索引
"""

import json
import os
import sys
import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# 问答文档目录名
QA_DOCS_DIR = "docs/qa"
QA_INDEX_FILE = "index/qa_index.json"

# 问题分类
QA_CATEGORIES = {
    "architecture": "架构设计",
    "build": "构建配置",
    "feature": "功能实现",
    "debug": "问题调试",
    "api": "接口说明",
    "module": "模块说明",
    "process": "流程说明",
    "other": "其他"
}

# 默认索引结构
DEFAULT_INDEX = {
    "version": "1.0",
    "entries": [],
    "git_commit": None,
    "updated_at": None
}


def get_qa_dir(project_dir: str) -> str:
    """获取问答文档目录"""
    return os.path.join(project_dir, ".claude", QA_DOCS_DIR)


def get_index_path(project_dir: str) -> str:
    """获取索引文件路径"""
    return os.path.join(project_dir, ".claude", QA_INDEX_FILE)


def ensure_dirs(project_dir: str) -> None:
    """确保目录存在"""
    qa_dir = get_qa_dir(project_dir)
    index_dir = os.path.dirname(get_index_path(project_dir))

    for cat in QA_CATEGORIES:
        os.makedirs(os.path.join(qa_dir, cat), exist_ok=True)
    os.makedirs(index_dir, exist_ok=True)


def get_git_commit(project_dir: str) -> Optional[str]:
    """获取当前 Git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]
    except:
        pass
    return None


def get_file_hash(project_dir: str, file_paths: List[str]) -> str:
    """计算相关文件的哈希值"""
    hasher = hashlib.md5()
    for fp in file_paths:
        full_path = os.path.join(project_dir, fp)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'rb') as f:
                    hasher.update(f.read())
            except:
                pass
    return hasher.hexdigest()[:12]


def categorize_question(question: str) -> str:
    """根据问题内容判断分类"""
    question_lower = question.lower()

    keywords = {
        "architecture": ["架构", "结构", "设计", "分层", "模块划分", "architecture", "design"],
        "build": ["编译", "构建", "make", "cmake", "构建", "build", "编译选项", "配置"],
        "feature": ["怎么实现", "如何实现", "功能", "原理", "流程", "how", "implement"],
        "debug": ["报错", "错误", "问题", "调试", "为什么", "失败", "bug", "error", "debug", "排查"],
        "api": ["接口", "api", "函数", "参数", "返回值", "调用"],
        "module": ["模块", "组件", "component", "module", "目录"],
        "process": ["流程", "步骤", "过程", "启动", "初始化", "process", "flow"]
    }

    for cat, words in keywords.items():
        for word in words:
            if word in question_lower:
                return cat
    return "other"


def generate_filename(question: str) -> str:
    """根据问题生成文件名"""
    # 取问题的前30个字符，过滤特殊字符
    import re
    clean = re.sub(r'[^\w\u4e00-\u9fff]', '_', question[:30])
    clean = re.sub(r'_+', '_', clean).strip('_')
    if not clean:
        clean = "question"
    return clean


def load_index(project_dir: str) -> Dict[str, Any]:
    """加载索引"""
    index_path = get_index_path(project_dir)
    if os.path.exists(index_path):
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_INDEX.copy()


def save_index(project_dir: str, index: Dict[str, Any]) -> bool:
    """保存索引"""
    index_path = get_index_path(project_dir)
    try:
        index["updated_at"] = datetime.now().isoformat()
        index["git_commit"] = get_git_commit(project_dir)
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


def create_qa_doc(project_dir: str, question: str, answer: str,
                   file_refs: List[str] = None, tags: List[str] = None) -> Dict[str, Any]:
    """创建问答文档"""
    ensure_dirs(project_dir)

    category = categorize_question(question)
    filename = generate_filename(question)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_filename = f"{timestamp}_{filename}.md"

    qa_dir = get_qa_dir(project_dir)
    doc_path = os.path.join(qa_dir, category, doc_filename)

    # 生成文档内容
    content = f"""# {question[:50]}{"..." if len(question) > 50 else ""}

> 分类: {QA_CATEGORIES.get(category, "其他")}
> 创建时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}
> Git Commit: {get_git_commit(project_dir) or "N/A"}

## 问题

{question}

## 回答

{answer}

"""

    if file_refs:
        content += "## 相关文件\n\n"
        for ref in file_refs:
            content += f"- `{ref}`\n"

    if tags:
        content += "\n## 标签\n\n"
        content += ", ".join([f"#{tag}" for tag in tags])

    content += f"""
---

*此文档由 project-assistant 自动生成*
"""

    # 写入文档
    try:
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        return {"success": False, "error": str(e)}

    # 更新索引
    index = load_index(project_dir)

    entry = {
        "id": hashlib.md5(question.encode()).hexdigest()[:8],
        "question": question,
        "category": category,
        "doc_path": os.path.relpath(doc_path, os.path.join(project_dir, ".claude")),
        "created_at": datetime.now().isoformat(),
        "git_commit": get_git_commit(project_dir),
        "file_refs": file_refs or [],
        "tags": tags or [],
        "file_hash": get_file_hash(project_dir, file_refs) if file_refs else None
    }

    # 检查是否已存在相同问题
    existing = None
    for i, e in enumerate(index["entries"]):
        if e["question"] == question:
            existing = i
            break

    if existing is not None:
        index["entries"][existing] = entry
    else:
        index["entries"].append(entry)

    save_index(project_dir, index)

    return {
        "success": True,
        "doc_path": doc_path,
        "category": category,
        "entry_id": entry["id"]
    }


def search_qa(project_dir: str, query: str) -> List[Dict[str, Any]]:
    """搜索问答"""
    index = load_index(project_dir)
    results = []

    query_lower = query.lower()

    for entry in index["entries"]:
        score = 0

        # 问题匹配
        if query_lower in entry["question"].lower():
            score += 10

        # 标签匹配
        for tag in entry.get("tags", []):
            if query_lower in tag.lower():
                score += 5

        # 分类匹配
        if query_lower in entry.get("category", "").lower():
            score += 3

        if score > 0:
            results.append({
                **entry,
                "score": score
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:10]


def check_outdated(project_dir: str, entry_id: str = None) -> Dict[str, Any]:
    """检查文档是否过期"""
    index = load_index(project_dir)
    current_commit = get_git_commit(project_dir)

    outdated = []

    for entry in index["entries"]:
        if entry_id and entry["id"] != entry_id:
            continue

        reasons = []

        # Git commit 变化
        if entry.get("git_commit") and current_commit:
            if entry["git_commit"] != current_commit:
                reasons.append("代码有新提交")

        # 文件哈希变化
        if entry.get("file_hash") and entry.get("file_refs"):
            current_hash = get_file_hash(project_dir, entry["file_refs"])
            if current_hash and current_hash != entry["file_hash"]:
                reasons.append("相关文件已修改")

        if reasons:
            outdated.append({
                **entry,
                "reasons": reasons
            })

    return {
        "current_commit": current_commit,
        "outdated_count": len(outdated),
        "outdated": outdated
    }


def get_qa_doc_content(project_dir: str, doc_path: str) -> Optional[str]:
    """读取问答文档内容"""
    full_path = os.path.join(project_dir, ".claude", doc_path)
    if os.path.exists(full_path):
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            pass
    return None


def list_qa_docs(project_dir: str, category: str = None) -> List[Dict[str, Any]]:
    """列出问答文档"""
    index = load_index(project_dir)

    if category:
        return [e for e in index["entries"] if e.get("category") == category]
    return index["entries"]


def delete_qa_doc(project_dir: str, entry_id: str) -> Dict[str, Any]:
    """删除问答文档"""
    index = load_index(project_dir)

    for i, entry in enumerate(index["entries"]):
        if entry["id"] == entry_id:
            # 删除文件
            doc_path = os.path.join(project_dir, ".claude", entry["doc_path"])
            if os.path.exists(doc_path):
                os.remove(doc_path)

            # 从索引移除
            index["entries"].pop(i)
            save_index(project_dir, index)

            return {"success": True, "message": "已删除"}

    return {"success": False, "error": "未找到"}


def print_help():
    """打印帮助"""
    help_text = """
问答文档管理器

用法: qa_doc_manager.py <projectDir> <command> [args]

命令:
  create <question> <answer> [file_refs] [tags]
      创建问答文档
      file_refs: 逗号分隔的文件路径
      tags: 逗号分隔的标签

  search <query>
      搜索问答

  list [category]
      列出问答文档

  check [entry_id]
      检查文档是否过期

  get <doc_path>
      获取文档内容

  delete <entry_id>
      删除问答文档

  categories
      显示所有分类

示例:
  # 创建问答
  qa_doc_manager.py ./project create "WiFi怎么连接？" "使用 wifi_connect()..." "src/wifi.c" "wifi,network"

  # 搜索
  qa_doc_manager.py ./project search "WiFi"

  # 检查过期
  qa_doc_manager.py ./project check
"""
    print(help_text)


def main():
    if len(sys.argv) < 3:
        print_help()
        sys.exit(1)

    project_dir = sys.argv[1]
    command = sys.argv[2]

    if command == "create":
        if len(sys.argv) < 5:
            print("用法: qa_doc_manager.py <projectDir> create <question> <answer> [file_refs] [tags]")
            sys.exit(1)

        question = sys.argv[3]
        answer = sys.argv[4]
        file_refs = sys.argv[5].split(",") if len(sys.argv) > 5 else None
        tags = sys.argv[6].split(",") if len(sys.argv) > 6 else None

        result = create_qa_doc(project_dir, question, answer, file_refs, tags)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "search":
        if len(sys.argv) < 4:
            print("用法: qa_doc_manager.py <projectDir> search <query>")
            sys.exit(1)

        results = search_qa(project_dir, sys.argv[3])
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif command == "list":
        category = sys.argv[3] if len(sys.argv) > 3 else None
        results = list_qa_docs(project_dir, category)
        print(json.dumps(results, ensure_ascii=False, indent=2))

    elif command == "check":
        entry_id = sys.argv[3] if len(sys.argv) > 3 else None
        result = check_outdated(project_dir, entry_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "get":
        if len(sys.argv) < 4:
            print("用法: qa_doc_manager.py <projectDir> get <doc_path>")
            sys.exit(1)

        content = get_qa_doc_content(project_dir, sys.argv[3])
        if content:
            print(content)
        else:
            print(json.dumps({"error": "文档不存在"}))

    elif command == "delete":
        if len(sys.argv) < 4:
            print("用法: qa_doc_manager.py <projectDir> delete <entry_id>")
            sys.exit(1)

        result = delete_qa_doc(project_dir, sys.argv[3])
        print(json.dumps(result, ensure_ascii=False))

    elif command == "categories":
        print(json.dumps(QA_CATEGORIES, ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {command}")
        print_help()


if __name__ == "__main__":
    main()