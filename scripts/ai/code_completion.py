#!/usr/bin/env python3
"""
项目感知代码补全
基于项目上下文的智能补全

特性:
- 项目上下文提取
- 相关函数/类查找
- 智能补全建议
"""

import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Position:
    """代码位置"""
    file: str
    line: int
    column: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file': self.file,
            'line': self.line,
            'column': self.column,
        }


@dataclass
class CompletionItem:
    """补全项"""
    text: str
    display_text: str = ""
    kind: str = "text"  # function, class, variable, snippet
    detail: str = ""
    documentation: str = ""
    source: str = ""  # local, project, import
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'display_text': self.display_text or self.text,
            'kind': self.kind,
            'detail': self.detail,
            'documentation': self.documentation,
            'source': self.source,
            'score': self.score,
        }


@dataclass
class CompletionResult:
    """补全结果"""
    items: List[CompletionItem] = field(default_factory=list)
    prefix: str = ""
    context: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'items': [item.to_dict() for item in self.items],
            'prefix': self.prefix,
            'context': self.context,
        }


class ProjectAwareCompletion:
    """项目感知代码补全

    补全来源:
    - 当前文件上下文
    - 项目中的相关函数/类
    - 向量搜索结果
    - 导入的模块
    """

    def __init__(self, project_dir: str):
        """初始化

        Args:
            project_dir: 项目目录
        """
        self.project_dir = Path(project_dir).resolve()
        self._vector_store = None
        self._ast_parser = None

        # 延迟加载
        self._init_components()

    def _init_components(self):
        """初始化组件"""
        try:
            from ai.vector_store import VectorStore
            self._vector_store = VectorStore(str(self.project_dir))
        except ImportError:
            pass

        try:
            from ast_parser import ASTParser
            self._ast_parser = ASTParser()
        except ImportError:
            pass

    def get_completion(self, file: str, position: Position,
                       context: str = "") -> CompletionResult:
        """获取补全建议

        Args:
            file: 文件路径
            position: 光标位置
            context: 当前行上下文

        Returns:
            补全结果
        """
        result = CompletionResult()

        # 1. 获取当前文件上下文
        file_context = self._get_file_context(file, position)
        result.context = file_context

        # 2. 解析前缀
        prefix = self._extract_prefix(context)
        result.prefix = prefix

        # 3. 从当前文件获取补全
        local_items = self._get_local_completion(file, position, prefix)
        result.items.extend(local_items)

        # 4. 从项目获取补全
        project_items = self._get_project_completion(file, prefix)
        result.items.extend(project_items)

        # 5. 从向量搜索获取补全
        vector_items = self._get_vector_completion(prefix, file_context)
        result.items.extend(vector_items)

        # 6. 排序和去重
        result.items = self._deduplicate_and_sort(result.items)

        return result

    def _get_file_context(self, file: str, position: Position) -> str:
        """获取文件上下文"""
        full_path = self.project_dir / file
        if not full_path.exists():
            return ""

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # 获取光标前后的上下文
            start = max(0, position.line - 20)
            end = min(len(lines), position.line + 5)

            return ''.join(lines[start:end])

        except Exception:
            return ""

    def _extract_prefix(self, context: str) -> str:
        """提取补全前缀"""
        if not context:
            return ""

        # 获取最后一个词
        import re
        words = re.findall(r'[\w.]+', context)
        return words[-1] if words else ""

    def _get_local_completion(self, file: str, position: Position,
                               prefix: str) -> List[CompletionItem]:
        """获取当前文件的补全"""
        items = []

        if not self._ast_parser:
            return items

        full_path = self.project_dir / file
        if not full_path.exists():
            return items

        try:
            result = self._ast_parser.parse_file(str(full_path))

            # 函数补全
            for func in result.get('functions', []):
                name = func.get('name', '')
                if name and (not prefix or name.startswith(prefix)):
                    items.append(CompletionItem(
                        text=name,
                        display_text=f"{name}()",
                        kind='function',
                        detail=f"function in {file}",
                        source='local',
                        score=0.9,
                    ))

            # 类补全
            for cls in result.get('classes', []):
                name = cls.get('name', '')
                if name and (not prefix or name.startswith(prefix)):
                    items.append(CompletionItem(
                        text=name,
                        kind='class',
                        detail=f"class in {file}",
                        source='local',
                        score=0.85,
                    ))

            # 变量补全
            for var in result.get('variables', []):
                name = var.get('name', '')
                if name and (not prefix or name.startswith(prefix)):
                    items.append(CompletionItem(
                        text=name,
                        kind='variable',
                        source='local',
                        score=0.8,
                    ))

        except Exception:
            pass

        return items

    def _get_project_completion(self, file: str,
                                  prefix: str) -> List[CompletionItem]:
        """获取项目级别的补全"""
        items = []

        if not self._ast_parser:
            return items

        # 使用 L1 索引
        try:
            from indexer.lazy_indexer import LazyIndexer
            indexer = LazyIndexer(str(self.project_dir))
            l1 = indexer.get_l1_index()

            # 函数补全
            for f, funcs in l1.functions.items():
                if f == file:
                    continue  # 跳过当前文件

                for func in funcs:
                    name = func.get('name', '')
                    if name and (not prefix or name.startswith(prefix)):
                        items.append(CompletionItem(
                            text=name,
                            display_text=f"{name}()",
                            kind='function',
                            detail=f"function in {f}",
                            source='project',
                            score=0.7,
                        ))

            # 类补全
            for f, classes in l1.classes.items():
                if f == file:
                    continue

                for cls in classes:
                    name = cls.get('name', '')
                    if name and (not prefix or name.startswith(prefix)):
                        items.append(CompletionItem(
                            text=name,
                            kind='class',
                            detail=f"class in {f}",
                            source='project',
                            score=0.65,
                        ))

        except Exception:
            pass

        return items[:50]  # 限制数量

    def _get_vector_completion(self, prefix: str,
                                context: str) -> List[CompletionItem]:
        """使用向量搜索获取补全"""
        items = []

        if not self._vector_store:
            return items

        try:
            # 使用上下文搜索
            query = f"{prefix} {context[:100]}"
            results = self._vector_store.search_code(query, top_k=10)

            for r in results:
                # 提取函数/类名
                name = self._extract_name_from_content(r.content, prefix)
                if name:
                    items.append(CompletionItem(
                        text=name,
                        kind='function',
                        detail=f"semantic match (score: {r.score:.2f})",
                        source='vector',
                        score=r.score * 0.6,
                    ))

        except Exception:
            pass

        return items

    def _extract_name_from_content(self, content: str, prefix: str) -> Optional[str]:
        """从内容中提取名称"""
        import re

        # 函数定义
        match = re.search(r'def\s+(\w+)', content)
        if match and match.group(1).startswith(prefix):
            return match.group(1)

        # 类定义
        match = re.search(r'class\s+(\w+)', content)
        if match and match.group(1).startswith(prefix):
            return match.group(1)

        return None

    def _deduplicate_and_sort(self, items: List[CompletionItem]) -> List[CompletionItem]:
        """去重和排序"""
        seen = set()
        unique = []

        for item in items:
            key = (item.text, item.kind)
            if key not in seen:
                seen.add(key)
                unique.append(item)

        # 按分数排序
        unique.sort(key=lambda x: (-x.score, x.text))

        return unique[:30]  # 限制结果数量

    def get_signature_help(self, file: str, position: Position) -> Dict[str, Any]:
        """获取函数签名帮助

        Args:
            file: 文件路径
            position: 光标位置

        Returns:
            签名信息
        """
        result = {
            'signatures': [],
            'active_signature': 0,
            'active_parameter': 0,
        }

        # 获取上下文
        context = self._get_file_context(file, position)

        # 查找函数调用
        import re
        match = re.search(r'(\w+)\s*\([^)]*$', context)
        if match:
            func_name = match.group(1)

            # 查找函数定义
            if self._ast_parser:
                full_path = self.project_dir / file
                try:
                    parse_result = self._ast_parser.parse_file(str(full_path))
                    for func in parse_result.get('functions', []):
                        if func.get('name') == func_name:
                            result['signatures'].append({
                                'label': func.get('signature', f"{func_name}()"),
                                'documentation': func.get('docstring', ''),
                                'parameters': func.get('parameters', []),
                            })
                except Exception:
                    pass

        return result

    def get_hover_info(self, file: str, position: Position) -> Dict[str, Any]:
        """获取悬停信息

        Args:
            file: 文件路径
            position: 光标位置

        Returns:
            悬停信息
        """
        result = {
            'contents': [],
            'range': None,
        }

        # 获取上下文
        context = self._get_file_context(file, position)

        # 查找单词
        import re
        match = re.search(r'\b(\w+)\b', context[max(0, position.column - 50):position.column + 50])
        if not match:
            return result

        word = match.group(1)

        # 查找定义
        if self._ast_parser:
            full_path = self.project_dir / file
            try:
                parse_result = self._ast_parser.parse_file(str(full_path))

                for func in parse_result.get('functions', []):
                    if func.get('name') == word:
                        result['contents'].append(f"```python\ndef {word}(...)\n```")
                        if func.get('docstring'):
                            result['contents'].append(func['docstring'])

                for cls in parse_result.get('classes', []):
                    if cls.get('name') == word:
                        result['contents'].append(f"```python\nclass {word}\n```")

            except Exception:
                pass

        return result


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: code_completion.py <project_dir> [command]")
        print("\nCommands:")
        print("  complete <file> <line> [prefix]    Get completion")
        print("  signature <file> <line>            Get signature help")
        print("  hover <file> <line> <column>       Get hover info")
        sys.exit(1)

    project_dir = sys.argv[1]
    completer = ProjectAwareCompletion(project_dir)

    if len(sys.argv) < 3:
        print("Please specify a command")
        sys.exit(1)

    command = sys.argv[2]

    if command == 'complete':
        if len(sys.argv) < 5:
            print("Usage: code_completion.py <project_dir> complete <file> <line> [prefix]")
            sys.exit(1)
        file = sys.argv[3]
        line = int(sys.argv[4])
        prefix = sys.argv[5] if len(sys.argv) > 5 else ""

        position = Position(file=file, line=line)
        result = completer.get_completion(file, position, prefix)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    elif command == 'signature':
        if len(sys.argv) < 5:
            print("Usage: code_completion.py <project_dir> signature <file> <line>")
            sys.exit(1)
        file = sys.argv[3]
        line = int(sys.argv[4])
        position = Position(file=file, line=line)
        result = completer.get_signature_help(file, position)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == 'hover':
        if len(sys.argv) < 6:
            print("Usage: code_completion.py <project_dir> hover <file> <line> <column>")
            sys.exit(1)
        file = sys.argv[3]
        line = int(sys.argv[4])
        column = int(sys.argv[5])
        position = Position(file=file, line=line, column=column)
        result = completer.get_hover_info(file, position)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()