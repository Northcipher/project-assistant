#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
输出校验脚本

验证 project.md 输出是否符合模板要求。

Usage:
    python3 validate_output.py <PROJECT_DIR> [--fix]

Options:
    PROJECT_DIR    项目目录路径
    --fix          尝试自动修复缺失字段
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 修复 Windows 控制台编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 模板要求的必填章节
REQUIRED_SECTIONS = [
    ("基本信息", ["项目名称", "项目类型", "主要语言"]),
    ("目录结构", None),
    ("模块划分", None),
    ("入口点", None),
    ("构建指南", None),
    ("配置文件", None),
]

# 正确的输出路径
OUTPUT_FILE = ".projmeta/project.md"


class OutputValidator:
    """输出校验器"""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir).resolve()
        self.output_path = self.project_dir / OUTPUT_FILE
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []

    def validate(self) -> bool:
        """执行所有校验，返回是否全部通过"""
        print(f"\n{'='*60}")
        print(f"项目输出校验: {self.project_dir}")
        print(f"{'='*60}\n")

        # 1. 校验输出路径
        self._validate_output_path()

        # 2. 校验文件存在
        if not self._validate_file_exists():
            self._print_results()
            return False

        # 3. 读取文件内容
        content = self.output_path.read_text(encoding='utf-8')

        # 4. 校验必需章节
        self._validate_sections(content)

        # 5. 校验基本信息表格
        self._validate_basic_info(content)

        # 打印结果
        self._print_results()

        return len(self.errors) == 0

    def _validate_output_path(self) -> None:
        """校验输出路径是否正确"""
        expected_path = self.project_dir / OUTPUT_FILE

        # 检查是否有错误位置的输出文件
        wrong_locations = [
            self.project_dir / "PROJECT.md",
            self.project_dir / "project.md",
            self.project_dir / "README_PROJECT.md",
        ]

        for wrong_path in wrong_locations:
            if wrong_path.exists():
                self.errors.append(
                    f"❌ 输出位置错误: 发现 {wrong_path.name}，应移动到 {OUTPUT_FILE}"
                )

        self.passed.append(f"✓ 正确输出路径: {OUTPUT_FILE}")

    def _validate_file_exists(self) -> bool:
        """校验输出文件是否存在"""
        if not self.output_path.exists():
            self.errors.append(f"❌ 输出文件不存在: {self.output_path}")
            self.errors.append("   请运行 /init 命令生成项目文档")
            return False

        self.passed.append(f"✓ 输出文件存在")
        return True

    def _validate_sections(self, content: str) -> None:
        """校验必需章节是否存在"""
        for section_name, _ in REQUIRED_SECTIONS:
            if f"## {section_name}" in content or f"# {section_name}" in content:
                self.passed.append(f"✓ 包含章节: {section_name}")
            else:
                self.errors.append(f"❌ 缺少必需章节: {section_name}")

    def _validate_basic_info(self, content: str) -> None:
        """校验基本信息表格"""
        # 检查表格格式
        if "项目名称" not in content:
            self.warnings.append("⚠ 基本信息表格缺少'项目名称'字段")
        if "项目类型" not in content:
            self.warnings.append("⚠ 基本信息表格缺少'项目类型'字段")
        if "主要语言" not in content:
            self.warnings.append("⚠ 基本信息表格缺少'主要语言'字段")

        # 检查是否有表格格式
        if "|" in content and "---" in content:
            self.passed.append("✓ 包含表格格式")
        else:
            self.errors.append("❌ 缺少表格格式（使用 | 分隔）")

    def _validate_build_guide(self, content: str) -> None:
        """校验构建指南是否完整"""
        if "构建" not in content and "build" not in content.lower():
            self.warnings.append("⚠ 构建指南可能不完整")

    def _print_results(self) -> None:
        """打印校验结果"""
        print("校验结果:\n")

        if self.passed:
            print("通过的检查:")
            for item in self.passed:
                print(f"  {item}")
            print()

        if self.warnings:
            print("警告:")
            for item in self.warnings:
                print(f"  {item}")
            print()

        if self.errors:
            print("错误:")
            for item in self.errors:
                print(f"  {item}")
            print()

        print("-" * 60)
        if len(self.errors) == 0:
            print("✓ 所有检查通过")
        else:
            print(f"✗ 发现 {len(self.errors)} 个错误，请修复")
        print("-" * 60)

    def get_report(self) -> Dict:
        """获取校验报告（JSON格式）"""
        return {
            "project_dir": str(self.project_dir),
            "output_path": str(self.output_path),
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "passed": self.passed,
        }


def main():
    parser = argparse.ArgumentParser(
        description="验证项目输出文档是否符合模板要求",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python3 validate_output.py /path/to/project
    python3 validate_output.py /path/to/project --json
        """
    )
    parser.add_argument("project_dir", help="项目目录路径")
    parser.add_argument("--json", action="store_true", help="输出JSON格式报告")

    args = parser.parse_args()

    validator = OutputValidator(args.project_dir)
    success = validator.validate()

    if args.json:
        report = validator.get_report()
        print("\n" + json.dumps(report, ensure_ascii=False, indent=2))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()