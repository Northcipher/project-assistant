#!/usr/bin/env python3
"""
图表生成器
生成 Mermaid 格式的架构图、时序图、依赖图等

特性：
- 架构图生成
- 时序图生成
- 依赖图生成
- ER 图生成
- 本地计算，零 Token 消耗
"""

import os
import re
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class DiagramNode:
    """图节点"""
    id: str
    label: str
    type: str = "class"  # class, interface, module, database, etc.
    subgraph: str = ""


@dataclass
class DiagramEdge:
    """图边"""
    source: str
    target: str
    label: str = ""
    style: str = "-->"  # -->, --, -.->, ==> etc.


class DiagramGenerator:
    """图表生成器"""

    def __init__(self, project_dir: str = None):
        """初始化生成器

        Args:
            project_dir: 项目目录
        """
        self.project_dir = Path(project_dir) if project_dir else None
        self.nodes: List[DiagramNode] = []
        self.edges: List[DiagramEdge] = []

    def clear(self) -> None:
        """清空图表"""
        self.nodes.clear()
        self.edges.clear()

    def add_node(self, node: DiagramNode) -> None:
        """添加节点"""
        self.nodes.append(node)

    def add_edge(self, edge: DiagramEdge) -> None:
        """添加边"""
        self.edges.append(edge)

    def generate_architecture_diagram(self, project_info: Dict[str, Any]) -> str:
        """生成架构图

        Args:
            project_info: 项目信息

        Returns:
            Mermaid 图表代码
        """
        self.clear()

        # 提取模块信息
        modules = project_info.get('modules', [])
        subsystems = project_info.get('subsystems', [])

        lines = ["graph TD"]

        # 添加子系统分组
        for subsystem in subsystems[:5]:
            lines.append(f"    subgraph {self._sanitize_id(subsystem)}")
            lines.append(f"        {self._sanitize_id(subsystem)}_mod[{subsystem}]")
            lines.append("    end")

        # 添加模块
        for module in modules[:10]:
            module_id = self._sanitize_id(module)
            lines.append(f"    {module_id}[{module}]")

        # 添加入口点
        entry_points = project_info.get('entry_points', [])
        for entry in entry_points[:3]:
            entry_id = self._sanitize_id(entry)
            lines.append(f"    {entry_id}(({entry}))")
            lines.append(f"    {entry_id} --> {self._sanitize_id(modules[0]) if modules else 'app'}")

        # 添加样式
        lines.append("")
        lines.append("    classDef entry fill:#e1f5fe,stroke:#01579b")
        lines.append("    classDef module fill:#fff3e0,stroke:#e65100")
        lines.append("    classDef subsystem fill:#f3e5f5,stroke:#4a148c")

        return "\n".join(lines)

    def generate_sequence_diagram(self, call_chain: List[Dict[str, Any]]) -> str:
        """生成时序图

        Args:
            call_chain: 调用链列表

        Returns:
            Mermaid 时序图代码
        """
        lines = ["sequenceDiagram"]
        participants = set()

        # 提取参与者
        for call in call_chain:
            caller = call.get('caller', 'Unknown')
            callee = call.get('callee', 'Unknown')
            participants.add(caller)
            participants.add(callee)

        # 添加参与者声明
        for p in sorted(participants):
            p_id = self._sanitize_id(p)
            lines.append(f"    participant {p_id} as {p}")

        # 添加调用
        for call in call_chain:
            caller = self._sanitize_id(call.get('caller', 'Unknown'))
            callee = self._sanitize_id(call.get('callee', 'Unknown'))
            method = call.get('method', 'call')
            line_num = call.get('line', '')

            note = f" : {method}"
            if line_num:
                note += f" (L{line_num})"

            lines.append(f"    {caller}-->>{callee}{note}")

        return "\n".join(lines)

    def generate_dependency_graph(self, deps: Dict[str, List[str]]) -> str:
        """生成依赖图

        Args:
            deps: 依赖字典 {module: [dependencies]}

        Returns:
            Mermaid 图表代码
        """
        self.clear()

        lines = ["graph LR"]

        # 添加节点
        all_modules = set(deps.keys())
        for dep_list in deps.values():
            all_modules.update(dep_list)

        for module in sorted(all_modules):
            module_id = self._sanitize_id(module)
            lines.append(f"    {module_id}[{module}]")

        # 添加依赖边
        for module, dependencies in deps.items():
            module_id = self._sanitize_id(module)
            for dep in dependencies:
                dep_id = self._sanitize_id(dep)
                lines.append(f"    {module_id} --> {dep_id}")

        return "\n".join(lines)

    def generate_er_diagram(self, models: List[Dict[str, Any]]) -> str:
        """生成 ER 图

        Args:
            models: 模型列表

        Returns:
            Mermaid ER 图代码
        """
        lines = ["erDiagram"]

        for model in models[:15]:
            name = model.get('name', 'Unknown')
            fields = model.get('fields', [])
            relations = model.get('relations', [])

            # 添加实体
            for field in fields[:10]:
                field_name = field.get('name', 'unknown')
                field_type = field.get('type', 'string')
                lines.append(f"    {name} {{")
                lines.append(f"        {field_type} {field_name}")
                lines.append("    }")

            # 添加关系
            for relation in relations:
                target = relation.get('target', '')
                rel_type = relation.get('type', '||--|{')

                if target:
                    lines.append(f"    {name} {rel_type} {target} : \"has\"")

        return "\n".join(lines)

    def generate_flowchart(self, steps: List[Dict[str, Any]]) -> str:
        """生成流程图

        Args:
            steps: 步骤列表

        Returns:
            Mermaid 流程图代码
        """
        lines = ["flowchart TD"]

        for i, step in enumerate(steps):
            step_id = f"step_{i}"
            step_name = step.get('name', f'Step {i+1}')
            step_type = step.get('type', 'process')
            next_step = step.get('next')

            # 根据类型选择形状
            if step_type == 'start':
                lines.append(f"    {step_id}([{step_name}])")
            elif step_type == 'end':
                lines.append(f"    {step_id}([{step_name}])")
            elif step_type == 'decision':
                lines.append(f"    {step_id}{{{step_name}}}")
            else:
                lines.append(f"    {step_id}[{step_name}]")

            # 添加连接
            if next_step and i < len(steps) - 1:
                next_id = f"step_{i+1}"
                label = step.get('label', '')
                if label:
                    lines.append(f"    {step_id} -->|{label}| {next_id}")
                else:
                    lines.append(f"    {step_id} --> {next_id}")

        return "\n".join(lines)

    def generate_class_diagram(self, classes: List[Dict[str, Any]]) -> str:
        """生成类图

        Args:
            classes: 类列表

        Returns:
            Mermaid 类图代码
        """
        lines = ["classDiagram"]

        for cls in classes[:10]:
            name = cls.get('name', 'Unknown')
            methods = cls.get('methods', [])
            fields = cls.get('fields', [])
            extends = cls.get('extends', '')

            # 添加类
            lines.append(f"    class {name} {{")
            for field in fields[:5]:
                visibility = field.get('visibility', '+')
                field_name = field.get('name', '')
                field_type = field.get('type', '')
                lines.append(f"        {visibility}{field_name} : {field_type}")

            for method in methods[:10]:
                visibility = method.get('visibility', '+')
                method_name = method.get('name', '')
                params = method.get('params', '')
                return_type = method.get('return_type', '')
                lines.append(f"        {visibility}{method_name}({params}) : {return_type}")
            lines.append("    }")

            # 添加继承关系
            if extends:
                lines.append(f"    {extends} <|-- {name}")

        return "\n".join(lines)

    def generate_state_diagram(self, states: List[Dict[str, Any]]) -> str:
        """生成状态图

        Args:
            states: 状态列表

        Returns:
            Mermaid 状态图代码
        """
        lines = ["stateDiagram-v2"]

        for state in states:
            name = state.get('name', '')
            transitions = state.get('transitions', [])

            for transition in transitions:
                target = transition.get('target', '')
                event = transition.get('event', '')

                if target:
                    if event:
                        lines.append(f"    {name} --> {target} : {event}")
                    else:
                        lines.append(f"    {name} --> {target}")

        return "\n".join(lines)

    def generate_mindmap(self, topic: str, branches: List[Dict[str, Any]]) -> str:
        """生成思维导图

        Args:
            topic: 主题
            branches: 分支列表

        Returns:
            Mermaid 思维导图代码
        """
        lines = ["mindmap"]

        def add_branch(prefix: str, branch: Dict[str, Any], depth: int = 1):
            indent = "  " * depth
            name = branch.get('name', '')
            lines.append(f"{prefix}{indent}{name}")

            children = branch.get('children', [])
            for child in children:
                add_branch(prefix, child, depth + 1)

        lines.append(f"  root(({topic}))")

        for branch in branches:
            add_branch("", branch, depth=2)

        return "\n".join(lines)

    def generate_gitgraph(self, commits: List[Dict[str, Any]]) -> str:
        """生成 Git 图

        Args:
            commits: 提交列表

        Returns:
            Mermaid Git 图代码
        """
        lines = ["gitGraph"]

        for commit in commits[:20]:
            commit_type = commit.get('type', 'commit')
            message = commit.get('message', '')[:30]
            branch = commit.get('branch', 'main')

            if commit_type == 'branch':
                lines.append(f"    branch {branch}")
            elif commit_type == 'checkout':
                lines.append(f"    checkout {branch}")
            elif commit_type == 'merge':
                target = commit.get('target', 'main')
                lines.append(f"    merge {target}")
            else:
                lines.append(f"    commit id: \"{message}\"")

        return "\n".join(lines)

    def _sanitize_id(self, text: str) -> str:
        """清理 ID（移除特殊字符）"""
        # 替换特殊字符
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', text)
        # 确保不以数字开头
        if sanitized[0].isdigit():
            sanitized = 'n' + sanitized
        return sanitized

    def wrap_with_mermaid(self, content: str) -> str:
        """包装为 Mermaid 代码块"""
        return f"```mermaid\n{content}\n```"

    def to_html(self, mermaid_code: str, title: str = "Diagram") -> str:
        """转换为 HTML

        Args:
            mermaid_code: Mermaid 代码
            title: 标题

        Returns:
            HTML 代码
        """
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="mermaid">
{mermaid_code}
        </div>
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true }});
    </script>
</body>
</html>"""


def main():
    """命令行接口"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: diagram_generator.py <command> [args]")
        print("\nCommands:")
        print("  architecture <project_dir>    Generate architecture diagram")
        print("  sequence <call_chain.json>    Generate sequence diagram")
        print("  dependency <deps.json>        Generate dependency graph")
        print("  class <classes.json>          Generate class diagram")
        print("  --html                        Output as HTML")
        sys.exit(1)

    command = sys.argv[1]
    output_html = '--html' in sys.argv

    generator = DiagramGenerator()

    if command == 'architecture':
        if len(sys.argv) < 3:
            print("Usage: diagram_generator.py architecture <project_dir>")
            sys.exit(1)

        project_dir = sys.argv[2]

        # 简单收集项目信息
        project_info = {
            'modules': [],
            'subsystems': [],
            'entry_points': [],
        }

        path = Path(project_dir)
        for item in path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                project_info['modules'].append(item.name)
                if item.name.lower() in {'src', 'lib', 'app', 'core', 'api'}:
                    project_info['subsystems'].append(item.name)

        result = generator.generate_architecture_diagram(project_info)

    elif command == 'sequence':
        if len(sys.argv) < 3:
            print("Usage: diagram_generator.py sequence <call_chain.json>")
            sys.exit(1)

        with open(sys.argv[2], 'r') as f:
            call_chain = json.load(f)

        result = generator.generate_sequence_diagram(call_chain)

    elif command == 'dependency':
        if len(sys.argv) < 3:
            print("Usage: diagram_generator.py dependency <deps.json>")
            sys.exit(1)

        with open(sys.argv[2], 'r') as f:
            deps = json.load(f)

        result = generator.generate_dependency_graph(deps)

    elif command == 'class':
        if len(sys.argv) < 3:
            print("Usage: diagram_generator.py class <classes.json>")
            sys.exit(1)

        with open(sys.argv[2], 'r') as f:
            classes = json.load(f)

        result = generator.generate_class_diagram(classes)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    if output_html:
        print(generator.to_html(result))
    else:
        print(generator.wrap_with_mermaid(result))


if __name__ == '__main__':
    main()