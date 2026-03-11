#!/usr/bin/env python3
"""
配置管理器
管理工作目录等全局配置，支持跨会话、跨平台使用
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# 配置文件名
CONFIG_FILE = "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "version": "1.0",
    "workdir": None,
    "project_name": None,
    "last_updated": None
}


def get_config_path(base_dir: str) -> str:
    """获取配置文件路径"""
    return os.path.join(base_dir, CONFIG_FILE)


def load_config(base_dir: str) -> Dict[str, Any]:
    """加载配置文件"""
    config_path = get_config_path(base_dir)

    if not os.path.exists(config_path):
        return DEFAULT_CONFIG.copy()

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 合并默认值，确保所有字段存在
            result = DEFAULT_CONFIG.copy()
            result.update(config)
            return result
    except (json.JSONDecodeError, IOError) as e:
        print(f"[警告] 配置文件读取失败: {e}", file=sys.stderr)
        return DEFAULT_CONFIG.copy()


def save_config(base_dir: str, config: Dict[str, Any]) -> bool:
    """保存配置文件"""
    config_path = get_config_path(base_dir)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"[错误] 配置文件保存失败: {e}", file=sys.stderr)
        return False


def get_workdir(base_dir: str) -> Optional[str]:
    """获取工作目录"""
    config = load_config(base_dir)
    workdir = config.get("workdir")

    if workdir and os.path.isdir(workdir):
        return workdir
    return None


def set_workdir(base_dir: str, workdir: str) -> Dict[str, Any]:
    """设置工作目录"""
    workdir = os.path.abspath(workdir)

    if not os.path.isdir(workdir):
        return {
            "success": False,
            "error": f"目录不存在: {workdir}"
        }

    config = load_config(base_dir)
    config["workdir"] = workdir
    config["project_name"] = os.path.basename(workdir)

    from datetime import datetime
    config["last_updated"] = datetime.now().isoformat()

    if save_config(base_dir, config):
        return {
            "success": True,
            "workdir": workdir,
            "project_name": config["project_name"]
        }
    else:
        return {
            "success": False,
            "error": "配置保存失败"
        }


def clear_workdir(base_dir: str) -> Dict[str, Any]:
    """清除工作目录配置"""
    config = load_config(base_dir)
    config["workdir"] = None
    config["project_name"] = None

    if save_config(base_dir, config):
        return {"success": True}
    return {"success": False, "error": "配置保存失败"}


def show_config(base_dir: str) -> Dict[str, Any]:
    """显示当前配置"""
    config = load_config(base_dir)

    result = {
        "version": config.get("version", "1.0"),
        "workdir": config.get("workdir"),
        "project_name": config.get("project_name"),
        "last_updated": config.get("last_updated")
    }

    # 检查工作目录是否有效
    if result["workdir"]:
        if os.path.isdir(result["workdir"]):
            result["workdir_status"] = "valid"
        else:
            result["workdir_status"] = "invalid (目录不存在)"
    else:
        result["workdir_status"] = "not set"

    return result


def main():
    """命令行入口"""
    if len(sys.argv) < 3:
        print("用法: config_manager.py <baseDir> <command> [args]")
        print("命令:")
        print("  get              - 获取工作目录")
        print("  set <path>       - 设置工作目录")
        print("  clear            - 清除工作目录")
        print("  show             - 显示当前配置")
        sys.exit(1)

    base_dir = sys.argv[1]
    command = sys.argv[2]

    if command == "get":
        workdir = get_workdir(base_dir)
        if workdir:
            print(json.dumps({"workdir": workdir}))
        else:
            print(json.dumps({"workdir": None, "error": "工作目录未设置"}))

    elif command == "set":
        if len(sys.argv) < 4:
            print("用法: config_manager.py <baseDir> set <path>")
            sys.exit(1)
        result = set_workdir(base_dir, sys.argv[3])
        print(json.dumps(result, ensure_ascii=False))

    elif command == "clear":
        result = clear_workdir(base_dir)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "show":
        result = show_config(base_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()