#!/usr/bin/env python3
"""
AST 解析器
基于 Tree-sitter 的多语言 AST 解析

特性：
- 支持 8 种主流语言
- 提取函数、类、导入、调用等结构化信息
- 本地计算，不消耗 LLM Token
- 精准定位代码位置
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed


class Language(Enum):
    """支持的语言"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"


@dataclass
class Position:
    """位置信息"""
    row: int
    column: int

    def to_dict(self) -> Dict[str, int]:
        return {'row': self.row, 'column': self.column}


@dataclass
class Range:
    """范围信息"""
    start: Position
    end: Position

    def to_dict(self) -> Dict[str, Any]:
        return {
            'start': self.start.to_dict(),
            'end': self.end.to_dict(),
        }


@dataclass
class Function:
    """函数信息"""
    name: str
    file_path: str
    range: Range
    parameters: List[Dict[str, str]] = field(default_factory=list)
    return_type: str = ""
    docstring: str = ""
    is_async: bool = False
    is_static: bool = False
    visibility: str = ""  # public, private, protected
    body_preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'file_path': self.file_path,
            'range': self.range.to_dict(),
            'parameters': self.parameters,
            'return_type': self.return_type,
            'docstring': self.docstring[:100] if self.docstring else "",
            'is_async': self.is_async,
            'is_static': self.is_static,
            'visibility': self.visibility,
        }


@dataclass
class Class:
    """类信息"""
    name: str
    file_path: str
    range: Range
    methods: List[Function] = field(default_factory=list)
    fields: List[Dict[str, str]] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)
    docstring: str = ""
    is_interface: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'file_path': self.file_path,
            'range': self.range.to_dict(),
            'methods': [m.to_dict() for m in self.methods],
            'fields': self.fields,
            'base_classes': self.base_classes,
            'docstring': self.docstring[:100] if self.docstring else "",
            'is_interface': self.is_interface,
        }


@dataclass
class Import:
    """导入信息"""
    module: str
    names: List[str] = field(default_factory=list)
    alias: str = ""
    is_wildcard: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'module': self.module,
            'names': self.names,
            'alias': self.alias,
            'is_wildcard': self.is_wildcard,
        }


@dataclass
class Call:
    """函数调用"""
    caller: str
    callee: str
    file_path: str
    line: int
    arguments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'caller': self.caller,
            'callee': self.callee,
            'file_path': self.file_path,
            'line': self.line,
            'arguments': self.arguments,
        }


@dataclass
class ASTResult:
    """AST 解析结果"""
    file_path: str
    language: str
    functions: List[Function] = field(default_factory=list)
    classes: List[Class] = field(default_factory=list)
    imports: List[Import] = field(default_factory=list)
    calls: List[Call] = field(default_factory=list)
    variables: List[Dict[str, Any]] = field(default_factory=list)
    parse_time: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_path': self.file_path,
            'language': self.language,
            'functions': [f.to_dict() for f in self.functions],
            'classes': [c.to_dict() for c in self.classes],
            'imports': [i.to_dict() for i in self.imports],
            'calls': [c.to_dict() for c in self.calls],
            'variables': self.variables,
            'parse_time': self.parse_time,
            'error': self.error,
        }


# 文件扩展名到语言的映射
EXTENSION_MAP = {
    '.py': Language.PYTHON,
    '.js': Language.JAVASCRIPT,
    '.jsx': Language.JAVASCRIPT,
    '.mjs': Language.JAVASCRIPT,
    '.cjs': Language.JAVASCRIPT,
    '.ts': Language.TYPESCRIPT,
    '.tsx': Language.TYPESCRIPT,
    '.mts': Language.TYPESCRIPT,
    '.java': Language.JAVA,
    '.c': Language.C,
    '.h': Language.C,
    '.cpp': Language.CPP,
    '.cc': Language.CPP,
    '.cxx': Language.CPP,
    '.hpp': Language.CPP,
    '.hxx': Language.CPP,
    '.go': Language.GO,
    '.rs': Language.RUST,
}


class ASTParser:
    """基于 Tree-sitter 的 AST 解析器"""

    def __init__(self, use_tree_sitter: bool = True):
        """初始化解析器

        Args:
            use_tree_sitter: 是否使用 Tree-sitter（False 则回退到正则）
        """
        self.use_tree_sitter = use_tree_sitter
        self._tree_sitter_available = False
        self._parsers: Dict[Language, Any] = {}

        if use_tree_sitter:
            self._init_tree_sitter()

    def _init_tree_sitter(self) -> None:
        """初始化 Tree-sitter"""
        try:
            import tree_sitter_python
            import tree_sitter_javascript
            import tree_sitter_typescript
            import tree_sitter_java
            import tree_sitter_c
            import tree_sitter_cpp
            import tree_sitter_go
            import tree_sitter_rust
            from tree_sitter import Language, Parser

            # 注册语言
            languages = {
                Language.PYTHON: tree_sitter_python.language(),
                Language.JAVASCRIPT: tree_sitter_javascript.language(),
                Language.TYPESCRIPT: tree_sitter_typescript.language_typescript(),
                Language.JAVA: tree_sitter_java.language(),
                Language.C: tree_sitter_c.language(),
                Language.CPP: tree_sitter_cpp.language(),
                Language.GO: tree_sitter_go.language(),
                Language.RUST: tree_sitter_rust.language(),
            }

            for lang, lang_obj in languages.items():
                parser = Parser(lang_obj)
                self._parsers[lang] = parser

            self._tree_sitter_available = True

        except ImportError as e:
            print(f"Warning: Tree-sitter not fully available: {e}")
            print("Falling back to regex-based parsing")
            self._tree_sitter_available = False

    def detect_language(self, file_path: str) -> Optional[Language]:
        """检测文件语言

        Args:
            file_path: 文件路径

        Returns:
            语言枚举或 None
        """
        ext = Path(file_path).suffix.lower()
        return EXTENSION_MAP.get(ext)

    def parse(self, file_path: str, content: str = None) -> ASTResult:
        """解析文件 AST

        Args:
            file_path: 文件路径
            content: 文件内容（可选，默认读取文件）

        Returns:
            AST 解析结果
        """
        start_time = time.time()

        lang = self.detect_language(file_path)
        if not lang:
            return ASTResult(
                file_path=file_path,
                language="unknown",
                error="Unsupported file type",
            )

        # 读取内容
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                return ASTResult(
                    file_path=file_path,
                    language=lang.value,
                    error=str(e),
                )

        # 解析
        if self._tree_sitter_available and lang in self._parsers:
            result = self._parse_with_tree_sitter(file_path, content, lang)
        else:
            result = self._parse_with_regex(file_path, content, lang)

        elapsed = time.time() - start_time
        result.parse_time = f"{elapsed:.3f}s"

        return result

    def _parse_with_tree_sitter(self, file_path: str, content: str,
                                 lang: Language) -> ASTResult:
        """使用 Tree-sitter 解析"""
        parser = self._parsers.get(lang)
        if not parser:
            return ASTResult(
                file_path=file_path,
                language=lang.value,
                error="Parser not available",
            )

        tree = parser.parse(bytes(content, 'utf-8'))
        root = tree.root_node

        result = ASTResult(
            file_path=file_path,
            language=lang.value,
        )

        # 根据语言选择解析策略
        if lang == Language.PYTHON:
            self._parse_python_tree(root, content, result)
        elif lang in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            self._parse_js_ts_tree(root, content, result, lang)
        elif lang == Language.JAVA:
            self._parse_java_tree(root, content, result)
        elif lang in (Language.C, Language.CPP):
            self._parse_c_cpp_tree(root, content, result, lang)
        elif lang == Language.GO:
            self._parse_go_tree(root, content, result)
        elif lang == Language.RUST:
            self._parse_rust_tree(root, content, result)

        return result

    def _parse_python_tree(self, root, content: str, result: ASTResult) -> None:
        """解析 Python AST"""
        lines = content.split('\n')

        def get_text(node):
            return content[node.start_byte:node.end_byte].decode('utf-8') if isinstance(content, bytes) else content[node.start_byte:node.end_byte]

        for node in root.children:
            # 函数定义
            if node.type == 'function_definition':
                func = self._extract_python_function(node, content, result.file_path)
                if func:
                    result.functions.append(func)

            # 类定义
            elif node.type == 'class_definition':
                cls = self._extract_python_class(node, content, result.file_path)
                if cls:
                    result.classes.append(cls)

            # 导入
            elif node.type in ('import_statement', 'import_from_statement'):
                imp = self._extract_python_import(node, content)
                if imp:
                    result.imports.append(imp)

    def _extract_python_function(self, node, content: str, file_path: str) -> Optional[Function]:
        """提取 Python 函数"""
        name = ""
        for child in node.children:
            if child.type == 'identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        # 检查是否异步
        is_async = any(c.type == 'async' for c in node.children)

        # 提取参数
        params = []
        for child in node.children:
            if child.type == 'parameters':
                params = self._extract_python_params(child, content)

        # 提取文档字符串
        docstring = ""
        body = node.child_by_field_name('body')
        if body and body.children:
            first_child = body.children[0]
            if first_child and first_child.type == 'expression_statement':
                expr = first_child.children[0] if first_child.children else None
                if expr and expr.type == 'string':
                    docstring = content[expr.start_byte:expr.end_byte].strip('"\'')

        return Function(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
            parameters=params,
            is_async=is_async,
            docstring=docstring,
        )

    def _extract_python_params(self, node, content: str) -> List[Dict[str, str]]:
        """提取 Python 参数"""
        params = []
        for child in node.children:
            if child.type in ('identifier', 'typed_parameter', 'default_parameter'):
                param_text = content[child.start_byte:child.end_byte]
                param_name = param_text.split('=')[0].split(':')[0].strip()
                params.append({'name': param_name, 'raw': param_text})
        return params

    def _extract_python_class(self, node, content: str, file_path: str) -> Optional[Class]:
        """提取 Python 类"""
        name = ""
        for child in node.children:
            if child.type == 'identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        # 提取基类
        base_classes = []
        for child in node.children:
            if child.type == 'argument_list':
                for arg in child.children:
                    if arg.type == 'identifier':
                        base_classes.append(content[arg.start_byte:arg.end_byte])

        # 提取方法
        methods = []
        body = node.child_by_field_name('body')
        if body:
            for child in body.children:
                if child.type == 'function_definition':
                    func = self._extract_python_function(child, content, file_path)
                    if func:
                        methods.append(func)

        return Class(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
            methods=methods,
            base_classes=base_classes,
        )

    def _extract_python_import(self, node, content: str) -> Optional[Import]:
        """提取 Python 导入"""
        text = content[node.start_byte:node.end_byte]

        if node.type == 'import_statement':
            # import x, y
            names = []
            for child in node.children:
                if child.type == 'identifier':
                    names.append(content[child.start_byte:child.end_byte])
                elif child.type == 'dotted_name':
                    names.append(content[child.start_byte:child.end_byte])
            return Import(module=names[0] if names else "", names=names)

        elif node.type == 'import_from_statement':
            # from x import y
            module = ""
            names = []
            for child in node.children:
                if child.type == 'dotted_name':
                    module = content[child.start_byte:child.end_byte]
                elif child.type == 'import_list':
                    for name in child.children:
                        if name.type == 'identifier':
                            names.append(content[name.start_byte:name.end_byte])
            return Import(module=module, names=names)

        return None

    def _parse_js_ts_tree(self, root, content: str, result: ASTResult, lang: Language) -> None:
        """解析 JavaScript/TypeScript AST"""
        for node in root.children:
            # 函数声明
            if node.type == 'function_declaration':
                func = self._extract_js_function(node, content, result.file_path)
                if func:
                    result.functions.append(func)

            # 类声明
            elif node.type == 'class_declaration':
                cls = self._extract_js_class(node, content, result.file_path)
                if cls:
                    result.classes.append(cls)

            # 导入
            elif node.type == 'import_statement':
                imp = self._extract_js_import(node, content)
                if imp:
                    result.imports.append(imp)

            # 变量声明中的箭头函数
            elif node.type == 'variable_declaration':
                for child in node.children:
                    if child.type == 'variable_declarator':
                        func = self._extract_arrow_function(child, content, result.file_path)
                        if func:
                            result.functions.append(func)

    def _extract_js_function(self, node, content: str, file_path: str) -> Optional[Function]:
        """提取 JavaScript/TypeScript 函数"""
        name = ""
        for child in node.children:
            if child.type == 'identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        # 提取参数
        params = []
        for child in node.children:
            if child.type == 'formal_parameters':
                for param in child.children:
                    if param.type == 'identifier':
                        params.append({'name': content[param.start_byte:param.end_byte]})

        return Function(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
            parameters=params,
        )

    def _extract_js_class(self, node, content: str, file_path: str) -> Optional[Class]:
        """提取 JavaScript/TypeScript 类"""
        name = ""
        for child in node.children:
            if child.type == 'identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        # 提取方法
        methods = []
        body = node.child_by_field_name('body')
        if body:
            for child in body.children:
                if child.type == 'method_definition':
                    func = self._extract_js_method(child, content, file_path)
                    if func:
                        methods.append(func)

        return Class(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
            methods=methods,
        )

    def _extract_js_method(self, node, content: str, file_path: str) -> Optional[Function]:
        """提取 JavaScript/TypeScript 方法"""
        name = ""
        for child in node.children:
            if child.type == 'property_identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        return Function(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
        )

    def _extract_js_import(self, node, content: str) -> Optional[Import]:
        """提取 JavaScript/TypeScript 导入"""
        source = ""
        names = []

        for child in node.children:
            if child.type == 'string':
                source = content[child.start_byte:child.end_byte].strip('\'"')
            elif child.type == 'identifier':
                names.append(content[child.start_byte:child.end_byte])
            elif child.type == 'named_imports':
                for name in child.children:
                    if name.type == 'identifier':
                        names.append(content[name.start_byte:name.end_byte])

        return Import(module=source, names=names)

    def _extract_arrow_function(self, node, content: str, file_path: str) -> Optional[Function]:
        """提取箭头函数"""
        name = ""
        for child in node.children:
            if child.type == 'identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        return Function(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
        )

    def _parse_java_tree(self, root, content: str, result: ASTResult) -> None:
        """解析 Java AST"""
        for node in root.children:
            if node.type == 'method_declaration':
                func = self._extract_java_method(node, content, result.file_path)
                if func:
                    result.functions.append(func)
            elif node.type == 'class_declaration':
                cls = self._extract_java_class(node, content, result.file_path)
                if cls:
                    result.classes.append(cls)
            elif node.type == 'import_declaration':
                imp = self._extract_java_import(node, content)
                if imp:
                    result.imports.append(imp)

    def _extract_java_method(self, node, content: str, file_path: str) -> Optional[Function]:
        """提取 Java 方法"""
        name = ""
        for child in node.children:
            if child.type == 'identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        # 检查修饰符
        is_static = False
        visibility = ""
        for child in node.children:
            if child.type == 'modifiers':
                for mod in child.children:
                    mod_text = content[mod.start_byte:mod.end_byte]
                    if mod_text == 'static':
                        is_static = True
                    elif mod_text in ('public', 'private', 'protected'):
                        visibility = mod_text

        return Function(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
            is_static=is_static,
            visibility=visibility,
        )

    def _extract_java_class(self, node, content: str, file_path: str) -> Optional[Class]:
        """提取 Java 类"""
        name = ""
        for child in node.children:
            if child.type == 'identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        return Class(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
        )

    def _extract_java_import(self, node, content: str) -> Optional[Import]:
        """提取 Java 导入"""
        text = content[node.start_byte:node.end_byte]
        # import package.Class;
        if text.startswith('import '):
            text = text[7:].rstrip(';')
            is_wildcard = text.endswith('.*')
            return Import(module=text.rstrip('.*'), is_wildcard=is_wildcard)
        return None

    def _parse_c_cpp_tree(self, root, content: str, result: ASTResult, lang: Language) -> None:
        """解析 C/C++ AST"""
        for node in root.children:
            if node.type == 'function_definition':
                func = self._extract_c_function(node, content, result.file_path)
                if func:
                    result.functions.append(func)
            elif node.type == 'class_specifier':
                cls = self._extract_cpp_class(node, content, result.file_path)
                if cls:
                    result.classes.append(cls)
            elif node.type == 'preproc_include':
                imp = self._extract_c_include(node, content)
                if imp:
                    result.imports.append(imp)

    def _extract_c_function(self, node, content: str, file_path: str) -> Optional[Function]:
        """提取 C/C++ 函数"""
        name = ""
        for child in node.children:
            if child.type == 'identifier':
                name = content[child.start_byte:child.end_byte]
                break
            elif child.type == 'function_declarator':
                for sub in child.children:
                    if sub.type == 'identifier':
                        name = content[sub.start_byte:sub.end_byte]
                        break

        if not name:
            return None

        return Function(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
        )

    def _extract_cpp_class(self, node, content: str, file_path: str) -> Optional[Class]:
        """提取 C++ 类"""
        name = ""
        for child in node.children:
            if child.type == 'type_identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        return Class(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
        )

    def _extract_c_include(self, node, content: str) -> Optional[Import]:
        """提取 C/C++ include"""
        for child in node.children:
            if child.type == 'string_literal':
                path = content[child.start_byte:child.end_byte].strip('<>"')
                return Import(module=path)
            elif child.type == 'system_lib_string':
                path = content[child.start_byte:child.end_byte].strip('<>')
                return Import(module=path)
        return None

    def _parse_go_tree(self, root, content: str, result: ASTResult) -> None:
        """解析 Go AST"""
        for node in root.children:
            if node.type == 'function_declaration':
                func = self._extract_go_function(node, content, result.file_path)
                if func:
                    result.functions.append(func)
            elif node.type == 'method_declaration':
                func = self._extract_go_method(node, content, result.file_path)
                if func:
                    result.functions.append(func)
            elif node.type == 'import_declaration':
                imp = self._extract_go_import(node, content)
                if imp:
                    result.imports.append(imp)

    def _extract_go_function(self, node, content: str, file_path: str) -> Optional[Function]:
        """提取 Go 函数"""
        name = ""
        for child in node.children:
            if child.type == 'identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        return Function(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
        )

    def _extract_go_method(self, node, content: str, file_path: str) -> Optional[Function]:
        """提取 Go 方法"""
        name = ""
        for child in node.children:
            if child.type == 'field_identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        return Function(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
        )

    def _extract_go_import(self, node, content: str) -> Optional[Import]:
        """提取 Go 导入"""
        for child in node.children:
            if child.type == 'import_spec':
                for sub in child.children:
                    if sub.type == 'interpreted_string_literal':
                        path = content[sub.start_byte:sub.end_byte].strip('"')
                        return Import(module=path)
        return None

    def _parse_rust_tree(self, root, content: str, result: ASTResult) -> None:
        """解析 Rust AST"""
        for node in root.children:
            if node.type == 'function_item':
                func = self._extract_rust_function(node, content, result.file_path)
                if func:
                    result.functions.append(func)
            elif node.type == 'struct_item':
                cls = self._extract_rust_struct(node, content, result.file_path)
                if cls:
                    result.classes.append(cls)
            elif node.type == 'use_declaration':
                imp = self._extract_rust_use(node, content)
                if imp:
                    result.imports.append(imp)

    def _extract_rust_function(self, node, content: str, file_path: str) -> Optional[Function]:
        """提取 Rust 函数"""
        name = ""
        for child in node.children:
            if child.type == 'identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        return Function(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
        )

    def _extract_rust_struct(self, node, content: str, file_path: str) -> Optional[Class]:
        """提取 Rust struct"""
        name = ""
        for child in node.children:
            if child.type == 'type_identifier':
                name = content[child.start_byte:child.end_byte]
                break

        if not name:
            return None

        return Class(
            name=name,
            file_path=file_path,
            range=Range(
                start=Position(row=node.start_point[0], column=node.start_point[1]),
                end=Position(row=node.end_point[0], column=node.end_point[1]),
            ),
        )

    def _extract_rust_use(self, node, content: str) -> Optional[Import]:
        """提取 Rust use"""
        text = content[node.start_byte:node.end_byte]
        # use std::collections::HashMap;
        if text.startswith('use '):
            text = text[4:].rstrip(';')
            return Import(module=text)
        return None

    def _parse_with_regex(self, file_path: str, content: str, lang: Language) -> ASTResult:
        """使用正则表达式解析（回退方案）"""
        result = ASTResult(
            file_path=file_path,
            language=lang.value,
        )

        if lang == Language.PYTHON:
            result.functions = self._regex_parse_python(content, file_path)
        elif lang in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            result.functions = self._regex_parse_js(content, file_path)
        elif lang == Language.JAVA:
            result.functions = self._regex_parse_java(content, file_path)
        elif lang in (Language.C, Language.CPP):
            result.functions = self._regex_parse_c(content, file_path)
        elif lang == Language.GO:
            result.functions = self._regex_parse_go(content, file_path)
        elif lang == Language.RUST:
            result.functions = self._regex_parse_rust(content, file_path)

        return result

    def _regex_parse_python(self, content: str, file_path: str) -> List[Function]:
        """正则解析 Python"""
        import re
        functions = []

        pattern = r'^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\):'
        for match in re.finditer(pattern, content, re.MULTILINE):
            line_num = content[:match.start()].count('\n') + 1
            functions.append(Function(
                name=match.group(1),
                file_path=file_path,
                range=Range(
                    start=Position(row=line_num, column=0),
                    end=Position(row=line_num, column=0),
                ),
            ))

        return functions

    def _regex_parse_js(self, content: str, file_path: str) -> List[Function]:
        """正则解析 JavaScript/TypeScript"""
        import re
        functions = []

        # function name()
        pattern = r'function\s+(\w+)\s*\('
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            functions.append(Function(
                name=match.group(1),
                file_path=file_path,
                range=Range(
                    start=Position(row=line_num, column=0),
                    end=Position(row=line_num, column=0),
                ),
            ))

        # const name = () =>
        pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\('
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            functions.append(Function(
                name=match.group(1),
                file_path=file_path,
                range=Range(
                    start=Position(row=line_num, column=0),
                    end=Position(row=line_num, column=0),
                ),
            ))

        return functions

    def _regex_parse_java(self, content: str, file_path: str) -> List[Function]:
        """正则解析 Java"""
        import re
        functions = []

        pattern = r'(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{'
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            functions.append(Function(
                name=match.group(1),
                file_path=file_path,
                range=Range(
                    start=Position(row=line_num, column=0),
                    end=Position(row=line_num, column=0),
                ),
            ))

        return functions

    def _regex_parse_c(self, content: str, file_path: str) -> List[Function]:
        """正则解析 C/C++"""
        import re
        functions = []

        pattern = r'(?:static\s+)?(?:inline\s+)?(?:\w+\s+)+(\w+)\s*\([^)]*\)\s*\{'
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            functions.append(Function(
                name=match.group(1),
                file_path=file_path,
                range=Range(
                    start=Position(row=line_num, column=0),
                    end=Position(row=line_num, column=0),
                ),
            ))

        return functions

    def _regex_parse_go(self, content: str, file_path: str) -> List[Function]:
        """正则解析 Go"""
        import re
        functions = []

        pattern = r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\('
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            functions.append(Function(
                name=match.group(1),
                file_path=file_path,
                range=Range(
                    start=Position(row=line_num, column=0),
                    end=Position(row=line_num, column=0),
                ),
            ))

        return functions

    def _regex_parse_rust(self, content: str, file_path: str) -> List[Function]:
        """正则解析 Rust"""
        import re
        functions = []

        pattern = r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)'
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count('\n') + 1
            functions.append(Function(
                name=match.group(1),
                file_path=file_path,
                range=Range(
                    start=Position(row=line_num, column=0),
                    end=Position(row=line_num, column=0),
                ),
            ))

        return functions

    def parse_project(self, project_dir: str, max_workers: int = 4) -> Dict[str, Any]:
        """解析整个项目

        Args:
            project_dir: 项目目录
            max_workers: 最大并行数

        Returns:
            解析结果汇总
        """
        start_time = time.time()
        project_path = Path(project_dir).resolve()

        # 收集源文件
        source_files = []
        exclude_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'build', 'dist', 'target'}

        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                if self.detect_language(f):
                    source_files.append(os.path.join(root, f))

        # 并行解析
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.parse, f): f for f in source_files}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pass

        # 汇总
        total_functions = sum(len(r.functions) for r in results)
        total_classes = sum(len(r.classes) for r in results)
        total_imports = sum(len(r.imports) for r in results)

        elapsed = time.time() - start_time

        return {
            'summary': {
                'files_parsed': len(results),
                'total_functions': total_functions,
                'total_classes': total_classes,
                'total_imports': total_imports,
                'parse_time': f"{elapsed:.2f}s",
            },
            'files': [r.to_dict() for r in results],
        }


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: ast_parser.py <file_or_project> [--json]")
        print("\nCommands:")
        print("  parse <file>           Parse single file")
        print("  parse-project <dir>    Parse entire project")
        sys.exit(1)

    if sys.argv[1] == 'parse' and len(sys.argv) > 2:
        file_path = sys.argv[2]
        output_json = '--json' in sys.argv

        parser = ASTParser()
        result = parser.parse(file_path)

        if output_json:
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(f"\n=== {file_path} ===")
            print(f"Language: {result.language}")
            print(f"Functions: {len(result.functions)}")
            for f in result.functions[:10]:
                print(f"  - {f.name} (line {f.range.start.row})")
            print(f"Classes: {len(result.classes)}")
            for c in result.classes[:5]:
                print(f"  - {c.name}")
            if result.error:
                print(f"Error: {result.error}")

    elif sys.argv[1] == 'parse-project' and len(sys.argv) > 2:
        project_dir = sys.argv[2]
        parser = ASTParser()
        result = parser.parse_project(project_dir)
        print(json.dumps(result['summary'], indent=2, ensure_ascii=False))

    else:
        print(f"Invalid arguments")
        sys.exit(1)


if __name__ == '__main__':
    main()