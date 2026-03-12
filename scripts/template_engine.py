#!/usr/bin/env python3
"""
模板引擎
支持模板渲染、继承和组合

特性：
- Jinja2 风格的模板语法
- 模板继承机制
- 变量验证
- 条件渲染
"""

import os
import re
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
from string import Template
import fnmatch


@dataclass
class TemplateVariable:
    """模板变量"""
    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""
    values: List[str] = field(default_factory=list)  # for enum type
    validation: str = ""  # regex pattern


@dataclass
class TemplateConfig:
    """模板配置"""
    id: str
    name: str
    patterns: List[str]
    priority: int = 0
    language: str = "unknown"
    build_system: str = "unknown"
    template: str = ""
    variables: List[TemplateVariable] = field(default_factory=list)
    content_filter: str = ""  # 用于内容匹配


class TemplateEngine:
    """模板引擎"""

    DEFAULT_TEMPLATE_DIR = "references/templates"
    CONFIG_FILE = "references/template-config.yaml"

    def __init__(self, project_dir: str = None, template_dir: str = None):
        """初始化模板引擎

        Args:
            project_dir: 项目目录
            template_dir: 模板目录
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.template_dir = Path(template_dir) if template_dir else (
            self.project_dir / self.DEFAULT_TEMPLATE_DIR
        )

        self._configs: Dict[str, TemplateConfig] = {}
        self._inheritance_map: Dict[str, List[str]] = {}

        self._load_configs()

    def _load_configs(self) -> None:
        """加载模板配置"""
        config_path = self.project_dir / self.CONFIG_FILE

        if not config_path.exists():
            # 尝试当前目录
            config_path = Path(self.CONFIG_FILE)

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}

                # 解析项目类型配置
                for item in data.get('project_types', []):
                    variables = []
                    for var_name, var_data in item.get('variables', {}).items():
                        variables.append(TemplateVariable(
                            name=var_name,
                            type=var_data.get('type', 'string'),
                            required=var_data.get('required', False),
                            default=var_data.get('default'),
                            description=var_data.get('description', ''),
                            values=var_data.get('values', []),
                            validation=var_data.get('validation', ''),
                        ))

                    self._configs[item['id']] = TemplateConfig(
                        id=item['id'],
                        name=item.get('name', item['id']),
                        patterns=item.get('patterns', []),
                        priority=item.get('priority', 0),
                        language=item.get('language', 'unknown'),
                        build_system=item.get('build_system', 'unknown'),
                        template=item.get('template', ''),
                        variables=variables,
                        content_filter=item.get('content_filter', ''),
                    )

                # 解析继承关系
                for item in data.get('template_inheritance', []):
                    parent = item.get('parent', '')
                    children = item.get('children', [])
                    if parent:
                        self._inheritance_map[parent] = children

            except Exception as e:
                print(f"Warning: Failed to load template configs: {e}")

    def get_config(self, project_type: str) -> Optional[TemplateConfig]:
        """获取模板配置"""
        return self._configs.get(project_type)

    def get_all_configs(self) -> Dict[str, TemplateConfig]:
        """获取所有配置"""
        return self._configs

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """渲染模板

        Args:
            template: 模板名称或路径
            variables: 变量字典

        Returns:
            渲染后的内容
        """
        # 加载模板内容
        template_content = self._load_template(template)

        if not template_content:
            return f"Template not found: {template}"

        # 处理模板继承
        template_content = self._process_inheritance(template_content, variables)

        # 渲染变量
        rendered = self._render_variables(template_content, variables)

        # 处理条件块
        rendered = self._render_conditionals(rendered, variables)

        # 处理循环
        rendered = self._render_loops(rendered, variables)

        return rendered

    def _load_template(self, template: str) -> str:
        """加载模板文件"""
        # 如果是路径
        template_path = self.template_dir / template

        if template_path.exists():
            try:
                return template_path.read_text(encoding='utf-8')
            except Exception:
                pass

        # 尝试添加 .md 扩展名
        if not template.endswith('.md'):
            template_path = self.template_dir / f"{template}.md"
            if template_path.exists():
                try:
                    return template_path.read_text(encoding='utf-8')
                except Exception:
                    pass

        return ""

    def _process_inheritance(self, content: str, variables: Dict[str, Any]) -> str:
        """处理模板继承"""
        # 查找 extends 指令
        extends_match = re.search(r'{%\s*extends\s+["\']([^"\']+)["\']\s*%}', content)

        if extends_match:
            parent_template = extends_match.group(1)
            parent_content = self._load_template(parent_template)

            if parent_content:
                # 提取 blocks
                child_blocks = self._extract_blocks(content)
                parent_content = self._replace_blocks(parent_content, child_blocks)

                # 移除 extends 指令
                content = re.sub(r'{%\s*extends\s+["\'][^"\']+["\']\s*%}', '', content)

                # 合并内容
                content = parent_content + "\n" + content

        return content

    def _extract_blocks(self, content: str) -> Dict[str, str]:
        """提取模板块"""
        blocks = {}

        pattern = r'{%\s*block\s+(\w+)\s*%}(.*?){%\s*endblock\s*%}'
        for match in re.finditer(pattern, content, re.DOTALL):
            block_name = match.group(1)
            block_content = match.group(2)
            blocks[block_name] = block_content

        return blocks

    def _replace_blocks(self, content: str, blocks: Dict[str, str]) -> str:
        """替换模板块"""
        def replace_block(match):
            block_name = match.group(1)
            if block_name in blocks:
                return blocks[block_name]
            return match.group(2)  # 保留原内容

        pattern = r'{%\s*block\s+(\w+)\s*%}(.*?){%\s*endblock\s*%}'
        return re.sub(pattern, replace_block, content, flags=re.DOTALL)

    def _render_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """渲染变量"""
        # {{ variable }} 语法
        def replace_var(match):
            var_name = match.group(1).strip()
            # 支持默认值: {{ variable|default('value') }}
            if '|' in var_name:
                parts = var_name.split('|')
                var_name = parts[0].strip()
                for part in parts[1:]:
                    if part.strip().startswith('default('):
                        default_match = re.search(r"default\(['\"](.+?)['\"]\)", part)
                        if default_match:
                            default_value = default_match.group(1)
                            if var_name not in variables or not variables[var_name]:
                                return default_value

            value = variables.get(var_name, f'{{{{ {var_name} }}}}')
            return str(value)

        content = re.sub(r'\{\{\s*(\w+(?:\|[\w\(\)\'\"]+)?)\s*\}\}', replace_var, content)

        # ${variable} 语法（简化版）
        try:
            template = Template(content)
            content = template.safe_substitute(variables)
        except Exception:
            pass

        return content

    def _render_conditionals(self, content: str, variables: Dict[str, Any]) -> str:
        """渲染条件块"""
        # {% if variable %} ... {% endif %}
        pattern = r'{%\s*if\s+(\w+)\s*%}(.*?){%\s*endif\s*%}'

        def replace_conditional(match):
            var_name = match.group(1)
            block_content = match.group(2)

            # 检查变量是否存在且为真
            if variables.get(var_name):
                return block_content
            return ''

        content = re.sub(pattern, replace_conditional, content, flags=re.DOTALL)

        # {% if variable %} ... {% else %} ... {% endif %}
        pattern = r'{%\s*if\s+(\w+)\s*%}(.*?){%\s*else\s*%}(.*?){%\s*endif\s*%}'

        def replace_conditional_else(match):
            var_name = match.group(1)
            if_content = match.group(2)
            else_content = match.group(3)

            if variables.get(var_name):
                return if_content
            return else_content

        content = re.sub(pattern, replace_conditional_else, content, flags=re.DOTALL)

        return content

    def _render_loops(self, content: str, variables: Dict[str, Any]) -> str:
        """渲染循环"""
        # {% for item in items %} ... {% endfor %}
        pattern = r'{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}(.*?){%\s*endfor\s*%}'

        def replace_loop(match):
            item_name = match.group(1)
            list_name = match.group(2)
            template = match.group(3)

            items = variables.get(list_name, [])
            if not isinstance(items, list):
                return ''

            result = []
            for i, item in enumerate(items):
                item_vars = variables.copy()
                item_vars[item_name] = item
                item_vars['index'] = i
                item_vars['index1'] = i + 1

                rendered = self._render_variables(template, item_vars)
                result.append(rendered)

            return ''.join(result)

        return re.sub(pattern, replace_loop, content, flags=re.DOTALL)

    def extend(self, child: str, parent: str) -> str:
        """组合模板

        Args:
            child: 子模板
            parent: 父模板

        Returns:
            组合后的模板
        """
        parent_content = self._load_template(parent)
        child_content = self._load_template(child)

        if not parent_content:
            return child_content

        if not child_content:
            return parent_content

        # 如果子模板有继承指令
        if '{% extends' in child_content:
            return child_content

        # 添加继承指令
        return f"{{% extends '{parent}' %}}\n\n{child_content}"

    def compose(self, templates: List[str], separator: str = "\n\n---\n\n") -> str:
        """多模板组合

        Args:
            templates: 模板列表
            separator: 分隔符

        Returns:
            组合后的内容
        """
        contents = []

        for template in templates:
            content = self._load_template(template)
            if content:
                contents.append(content)

        return separator.join(contents)

    def validate_variables(self, template: str,
                           variables: Dict[str, Any]) -> Dict[str, Any]:
        """验证变量

        Args:
            template: 模板名称
            variables: 变量字典

        Returns:
            验证结果 {'valid': bool, 'errors': [], 'warnings': []}
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
        }

        config = self._configs.get(template)
        if not config:
            return result

        for var in config.variables:
            value = variables.get(var.name)

            # 检查必填
            if var.required and value is None:
                result['valid'] = False
                result['errors'].append(f"Missing required variable: {var.name}")
                continue

            # 检查类型
            if value is not None:
                if var.type == 'number':
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        result['warnings'].append(
                            f"Variable {var.name} should be a number"
                        )

                elif var.type == 'boolean':
                    if str(value).lower() not in ('true', 'false', '1', '0'):
                        result['warnings'].append(
                            f"Variable {var.name} should be boolean"
                        )

                elif var.type == 'enum':
                    if str(value) not in var.values:
                        result['warnings'].append(
                            f"Variable {var.name} should be one of: {var.values}"
                        )

                # 检查正则验证
                if var.validation:
                    if not re.match(var.validation, str(value)):
                        result['warnings'].append(
                            f"Variable {var.name} does not match pattern: {var.validation}"
                        )

        return result

    def get_default_variables(self, template: str) -> Dict[str, Any]:
        """获取模板默认变量"""
        defaults = {}

        config = self._configs.get(template)
        if config:
            for var in config.variables:
                if var.default is not None:
                    defaults[var.name] = var.default

        return defaults

    def match_project_type(self, files: List[str],
                           dirs: List[str],
                           content_checker: callable = None) -> List[str]:
        """匹配项目类型

        Args:
            files: 文件列表
            dirs: 目录列表
            content_checker: 内容检查函数

        Returns:
            匹配的项目类型列表
        """
        files_set = set(files)
        dirs_set = set(dirs)

        matches = []

        for type_id, config in self._configs.items():
            score = 0

            for pattern in config.patterns:
                # 通配符匹配
                if '*' in pattern:
                    if any(fnmatch.fnmatch(f, pattern) for f in files):
                        score += 1
                # 精确文件匹配
                elif pattern in files_set:
                    score += 1.5
                # 目录匹配
                elif pattern in dirs_set or pattern.rstrip('/') in dirs_set:
                    score += 1.2
                # 内容匹配
                elif config.content_filter and content_checker:
                    if content_checker(config.content_filter):
                        score += 0.5

            if score > 0:
                matches.append((type_id, score * (1 + config.priority / 100)))

        # 按分数排序
        matches.sort(key=lambda x: x[1], reverse=True)

        return [m[0] for m in matches]

    def get_template_for_type(self, project_type: str) -> str:
        """获取项目类型对应的模板"""
        config = self._configs.get(project_type)
        if config:
            return config.template

        # 查找继承链
        for parent, children in self._inheritance_map.items():
            if project_type in children:
                return parent

        return "project-template.md"


def main():
    """命令行接口"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: template_engine.py <command> [args]")
        print("\nCommands:")
        print("  render <template> <var1=value1> ...    Render template")
        print("  list                                    List all templates")
        print("  info <template>                         Show template info")
        print("  match <project_dir>                     Match project type")
        sys.exit(1)

    command = sys.argv[1]

    engine = TemplateEngine()

    if command == 'render':
        if len(sys.argv) < 3:
            print("Usage: template_engine.py render <template> [var=value ...]")
            sys.exit(1)

        template = sys.argv[2]
        variables = {}

        for arg in sys.argv[3:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                variables[key] = value

        # 合并默认变量
        defaults = engine.get_default_variables(template)
        defaults.update(variables)
        variables = defaults

        # 验证
        validation = engine.validate_variables(template, variables)
        if not validation['valid']:
            print("Validation errors:")
            for err in validation['errors']:
                print(f"  - {err}")
            sys.exit(1)

        result = engine.render(template, variables)
        print(result)

    elif command == 'list':
        print("Available templates:")
        for type_id, config in engine._configs.items():
            print(f"  - {type_id}: {config.name}")

    elif command == 'info':
        if len(sys.argv) < 3:
            print("Usage: template_engine.py info <template>")
            sys.exit(1)

        template = sys.argv[2]
        config = engine._configs.get(template)

        if config:
            print(f"Name: {config.name}")
            print(f"Language: {config.language}")
            print(f"Build System: {config.build_system}")
            print(f"Template: {config.template}")
            print(f"Variables:")
            for var in config.variables:
                required = " (required)" if var.required else ""
                default = f" [default: {var.default}]" if var.default else ""
                print(f"  - {var.name}: {var.type}{required}{default}")
                if var.description:
                    print(f"    {var.description}")
        else:
            print(f"Template not found: {template}")

    elif command == 'match':
        if len(sys.argv) < 3:
            print("Usage: template_engine.py match <project_dir>")
            sys.exit(1)

        project_dir = sys.argv[2]

        # 收集文件和目录
        files = []
        dirs = []
        for item in Path(project_dir).iterdir():
            if item.is_file():
                files.append(item.name)
            else:
                dirs.append(item.name)

        matches = engine.match_project_type(files, dirs)
        print("Matched project types:")
        for m in matches[:5]:
            print(f"  - {m}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()