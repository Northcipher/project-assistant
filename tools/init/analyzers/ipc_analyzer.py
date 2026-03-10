#!/usr/bin/env python3
"""
IPC（跨进程通信）分析器
分析项目中的跨进程通信接口

支持：
- Binder (Android/AIDL)
- DBus
- Socket (TCP/Unix Domain)
- Shared Memory
- Protobuf/gRPC
- SOME/IP (车载)
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field


@dataclass
class IPCInterface:
    """IPC 接口"""
    name: str
    protocol: str                           # binder/dbus/socket/protobuf/someip
    file: str                               # 定义文件
    methods: List[str] = field(default_factory=list)
    clients: List[str] = field(default_factory=list)  # 调用方进程
    server: str = ""                        # 服务方进程
    description: str = ""


@dataclass
class ProcessInfo:
    """进程信息"""
    name: str
    entry_file: str                         # 入口文件
    subsystem: str = ""                     # 所属子系统
    provides: List[str] = field(default_factory=list)  # 提供的接口
    consumes: List[str] = field(default_factory=list)  # 使用的接口
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他进程


class IPCAnalyzer:
    """IPC 分析器"""

    # AIDL 接口定义正则
    AIDL_INTERFACE_PATTERN = re.compile(
        r'interface\s+(\w+)\s*\{([^}]+)\}',
        re.MULTILINE
    )
    AIDL_METHOD_PATTERN = re.compile(
        r'(?:oneway\s+)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)'
    )

    # DBus 接口定义正则 (XML)
    DBUS_INTERFACE_PATTERN = re.compile(
        r'<interface\s+name="([^"]+)"[^>]*>(.*?)</interface>',
        re.DOTALL
    )
    DBUS_METHOD_PATTERN = re.compile(
        r'<method\s+name="([^"]+)"'
    )

    # Protobuf service 定义正则
    PROTO_SERVICE_PATTERN = re.compile(
        r'service\s+(\w+)\s*\{([^}]+)\}',
        re.MULTILINE
    )
    PROTO_RPC_PATTERN = re.compile(
        r'rpc\s+(\w+)\s*\('
    )

    # SOME/IP 接口定义正则
    SOMEIP_INTERFACE_PATTERN = re.compile(
        r'(?:method|event|field)\s+(\w+)'
    )

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir).resolve()
        self.interfaces: Dict[str, IPCInterface] = {}
        self.processes: Dict[str, ProcessInfo] = {}
        self.communication_matrix: List[Dict[str, Any]] = []

    def analyze(self) -> Dict[str, Any]:
        """执行分析"""
        self._scan_aidl_files()
        self._scan_dbus_files()
        self._scan_proto_files()
        self._scan_someip_files()
        self._scan_socket_usage()
        self._build_communication_matrix()
        self._detect_processes()

        return self._generate_report()

    def _scan_aidl_files(self) -> None:
        """扫描 AIDL 文件"""
        for aidl_file in self.project_dir.rglob('*.aidl'):
            try:
                content = aidl_file.read_text(encoding='utf-8', errors='ignore')
                self._parse_aidl(content, str(aidl_file.relative_to(self.project_dir)))
            except Exception:
                pass

    def _parse_aidl(self, content: str, file_path: str) -> None:
        """解析 AIDL 内容"""
        for match in self.AIDL_INTERFACE_PATTERN.finditer(content):
            interface_name = match.group(1)
            methods_block = match.group(2)

            methods = []
            for method_match in self.AIDL_METHOD_PATTERN.finditer(methods_block):
                return_type = method_match.group(1)
                method_name = method_match.group(2)
                params = method_match.group(3)
                methods.append(f"{method_name}({params})")

            key = f"aidl:{interface_name}"
            self.interfaces[key] = IPCInterface(
                name=interface_name,
                protocol="binder",
                file=file_path,
                methods=methods,
            )

    def _scan_dbus_files(self) -> None:
        """扫描 DBus 配置文件"""
        for dbus_file in self.project_dir.rglob('*.xml'):
            # 只处理 DBus introspection 文件
            if 'dbus' not in dbus_file.name.lower():
                continue
            try:
                content = dbus_file.read_text(encoding='utf-8', errors='ignore')
                self._parse_dbus(content, str(dbus_file.relative_to(self.project_dir)))
            except Exception:
                pass

    def _parse_dbus(self, content: str, file_path: str) -> None:
        """解析 DBus XML 内容"""
        for match in self.DBUS_INTERFACE_PATTERN.finditer(content):
            interface_name = match.group(1)
            methods_block = match.group(2)

            methods = []
            for method_match in self.DBUS_METHOD_PATTERN.finditer(methods_block):
                methods.append(method_match.group(1))

            key = f"dbus:{interface_name}"
            self.interfaces[key] = IPCInterface(
                name=interface_name,
                protocol="dbus",
                file=file_path,
                methods=methods,
            )

    def _scan_proto_files(self) -> None:
        """扫描 Protobuf 文件"""
        for proto_file in self.project_dir.rglob('*.proto'):
            try:
                content = proto_file.read_text(encoding='utf-8', errors='ignore')
                self._parse_proto(content, str(proto_file.relative_to(self.project_dir)))
            except Exception:
                pass

    def _parse_proto(self, content: str, file_path: str) -> None:
        """解析 Protobuf 内容"""
        for match in self.PROTO_SERVICE_PATTERN.finditer(content):
            service_name = match.group(1)
            service_block = match.group(2)

            methods = []
            for rpc_match in self.PROTO_RPC_PATTERN.finditer(service_block):
                methods.append(rpc_match.group(1))

            key = f"grpc:{service_name}"
            self.interfaces[key] = IPCInterface(
                name=service_name,
                protocol="grpc",
                file=file_path,
                methods=methods,
            )

    def _scan_someip_files(self) -> None:
        """扫描 SOME/IP 配置文件"""
        # SOME/IP 通常在 JSON/YAML 配置中定义
        for config_file in self.project_dir.rglob('*someip*.json'):
            try:
                content = config_file.read_text(encoding='utf-8', errors='ignore')
                data = json.loads(content)
                self._parse_someip_config(data, str(config_file.relative_to(self.project_dir)))
            except Exception:
                pass

    def _parse_someip_config(self, data: Dict, file_path: str) -> None:
        """解析 SOME/IP 配置"""
        services = data.get('services', [])
        for service in services:
            name = service.get('name', 'unknown')
            methods = []
            for method in service.get('methods', []):
                methods.append(method.get('name', ''))
            for event in service.get('events', []):
                methods.append(f"event:{event.get('name', '')}")

            key = f"someip:{name}"
            self.interfaces[key] = IPCInterface(
                name=name,
                protocol="someip",
                file=file_path,
                methods=methods,
            )

    def _scan_socket_usage(self) -> None:
        """扫描 Socket 使用"""
        # 查找 Unix Domain Socket 和 TCP Socket 使用
        socket_patterns = [
            (r'unix\s*socket.*?(\S+\.sock)', 'unix_socket'),
            (r'connect\s*\([^,]+,\s*"([^"]+)"', 'tcp_socket'),
            (r'bind\s*\([^,]+,\s*"([^"]+)"', 'tcp_socket'),
        ]

        for ext in ['.cpp', '.c', '.java', '.kt', '.py']:
            for source_file in self.project_dir.rglob(f'*{ext}'):
                try:
                    content = source_file.read_text(encoding='utf-8', errors='ignore')
                    for pattern, socket_type in socket_patterns:
                        for match in re.finditer(pattern, content, re.IGNORECASE):
                            socket_path = match.group(1)
                            interface_name = Path(socket_path).stem
                            key = f"socket:{interface_name}"
                            if key not in self.interfaces:
                                self.interfaces[key] = IPCInterface(
                                    name=interface_name,
                                    protocol=socket_type,
                                    file=str(source_file.relative_to(self.project_dir)),
                                    methods=['connect', 'send', 'receive'],
                                )
                except Exception:
                    pass

    def _detect_processes(self) -> None:
        """检测进程定义"""
        # 查找 main 函数作为进程入口
        main_patterns = [
            (r'int\s+main\s*\(', '.cpp'),
            (r'def\s+main\s*\(', '.py'),
            (r'public\s+static\s+void\s+main\s*\(', '.java'),
            (r'fun\s+main\s*\(', '.kt'),
        ]

        for pattern, ext in main_patterns:
            for source_file in self.project_dir.rglob(f'*{ext}'):
                try:
                    content = source_file.read_text(encoding='utf-8', errors='ignore')
                    if re.search(pattern, content):
                        process_name = source_file.parent.name
                        if process_name not in self.processes:
                            self.processes[process_name] = ProcessInfo(
                                name=process_name,
                                entry_file=str(source_file.relative_to(self.project_dir)),
                                subsystem=self._infer_subsystem(source_file),
                            )
                except Exception:
                    pass

    def _infer_subsystem(self, file_path: Path) -> str:
        """推断文件所属子系统"""
        parts = file_path.relative_to(self.project_dir).parts
        if len(parts) > 1:
            return parts[0]
        return "main"

    def _build_communication_matrix(self) -> None:
        """构建通信矩阵"""
        # 分析接口调用关系
        for key, interface in self.interfaces.items():
            # 在源码中查找接口使用
            for ext in ['.cpp', '.c', '.java', '.kt', '.py']:
                for source_file in self.project_dir.rglob(f'*{ext}'):
                    try:
                        content = source_file.read_text(encoding='utf-8', errors='ignore')
                        if interface.name in content:
                            process_name = source_file.parent.name
                            if process_name in self.processes:
                                if interface.server and interface.server != process_name:
                                    interface.clients.append(process_name)
                                    self.processes[process_name].consumes.append(key)
                    except Exception:
                        pass

        # 构建矩阵
        for key, interface in self.interfaces.items():
            for client in interface.clients:
                self.communication_matrix.append({
                    'source': client,
                    'target': interface.server or 'unknown',
                    'protocol': interface.protocol,
                    'interface': interface.name,
                    'file': interface.file,
                })

    def _generate_report(self) -> Dict[str, Any]:
        """生成分析报告"""
        return {
            'summary': {
                'total_interfaces': len(self.interfaces),
                'total_processes': len(self.processes),
                'protocols': list(set(i.protocol for i in self.interfaces.values())),
            },
            'interfaces': [
                {
                    'name': iface.name,
                    'protocol': iface.protocol,
                    'file': iface.file,
                    'methods': iface.methods[:10],  # 限制输出
                    'clients': iface.clients,
                    'server': iface.server,
                }
                for iface in self.interfaces.values()
            ],
            'processes': [
                {
                    'name': proc.name,
                    'entry': proc.entry_file,
                    'subsystem': proc.subsystem,
                    'provides': proc.provides,
                    'consumes': proc.consumes,
                }
                for proc in self.processes.values()
            ],
            'communication_matrix': self.communication_matrix,
        }

    def generate_ipc_document(self) -> str:
        """生成 IPC 文档 (Markdown)"""
        lines = [
            "# IPC 通信概览",
            "",
            f"> 自动生成 | 接口数: {len(self.interfaces)} | 进程数: {len(self.processes)}",
            "",
            "## 通信矩阵",
            "",
            "| 源进程 | 目标进程 | 协议 | 接口 |",
            "|--------|----------|------|------|",
        ]

        for comm in self.communication_matrix:
            lines.append(
                f"| {comm['source']} | {comm['target']} | {comm['protocol']} | {comm['interface']} |"
            )

        lines.extend([
            "",
            "## 接口详情",
            "",
        ])

        for key, iface in self.interfaces.items():
            lines.extend([
                f"### {iface.name}",
                "",
                f"- **协议**: {iface.protocol}",
                f"- **定义文件**: `{iface.file}`",
                f"- **方法数**: {len(iface.methods)}",
                "",
                "**方法列表**:",
                "",
            ])
            for method in iface.methods[:10]:
                lines.append(f"- `{method}`")
            if len(iface.methods) > 10:
                lines.append(f"- ... (共 {len(iface.methods)} 个)")
            lines.append("")

        return "\n".join(lines)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: ipc_analyzer.py <project_dir> [--doc]")
        print("\nOptions:")
        print("  --doc    Generate markdown document")
        sys.exit(1)

    project_dir = sys.argv[1]
    generate_doc = '--doc' in sys.argv

    analyzer = IPCAnalyzer(project_dir)
    result = analyzer.analyze()

    if generate_doc:
        print(analyzer.generate_ipc_document())
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()