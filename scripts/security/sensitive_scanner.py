#!/usr/bin/env python3
"""
敏感信息扫描器
自动扫描项目中的敏感信息，支持自动脱敏

特性：
- 敏感文件检测
- 敏感内容模式匹配
- 自动脱敏处理
- 可配置排除规则
"""

import os
import re
import fnmatch
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class SensitiveType(Enum):
    """敏感信息类型"""
    PASSWORD = "password"
    API_KEY = "api_key"
    SECRET = "secret"
    TOKEN = "token"
    PRIVATE_KEY = "private_key"
    CERTIFICATE = "certificate"
    DATABASE_URL = "database_url"
    CREDENTIALS = "credentials"
    ENV_FILE = "env_file"


@dataclass
class SensitiveMatch:
    """敏感信息匹配结果"""
    file_path: str
    line_number: int
    sensitive_type: SensitiveType
    original: str
    masked: str
    pattern: str
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class ScanResult:
    """扫描结果"""
    project_dir: str
    scanned_files: int = 0
    sensitive_files: List[str] = field(default_factory=list)
    matches: List[SensitiveMatch] = field(default_factory=list)
    excluded_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    scan_time: str = ""

    @property
    def has_sensitive(self) -> bool:
        return bool(self.sensitive_files or self.matches)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'project_dir': self.project_dir,
            'scanned_files': self.scanned_files,
            'sensitive_files': self.sensitive_files,
            'matches_count': len(self.matches),
            'matches': [
                {
                    'file': m.file_path,
                    'line': m.line_number,
                    'type': m.sensitive_type.value,
                    'masked': m.masked,
                    'severity': m.severity,
                }
                for m in self.matches[:20]  # 限制输出数量
            ],
            'excluded_count': len(self.excluded_files),
            'has_sensitive': self.has_sensitive,
            'scan_time': self.scan_time,
        }


class SensitiveScanner:
    """敏感信息扫描器"""

    # 敏感文件模式
    SENSITIVE_FILE_PATTERNS = [
        # 环境变量文件
        '.env', '.env.local', '.env.development', '.env.production',
        '.env.test', '.env.staging', '.env.*.local',

        # 密钥和证书
        '*.pem', '*.key', '*.p12', '*.pfx', '*.jks', '*.keystore',
        'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
        '*.crt', '*.cer', '*.der',

        # 凭证文件
        'credentials.json', 'secrets.json', 'secrets.yaml', 'secrets.yml',
        'credentials.yml', 'credentials.yaml',
        'service-account.json', 'service_account.json',
        '*.secret', 'secret.*',

        # 配置文件中的敏感部分
        'htpasswd', '.htpasswd',
        'shadow', 'passwd',
        '.pgpass', '.my.cnf',
        'netrc', '.netrc',

        # 云服务凭证
        '.aws/credentials', '.azure/credentials',
        '.gcloud/credentials', 'applicationDefault_credentials.json',
    ]

    # 敏感目录
    SENSITIVE_DIR_PATTERNS = [
        'secrets/', '.secrets/', 'private/', 'credentials/',
        '.ssh/', '.gnupg/', '.config/gcloud/',
    ]

    # 敏感内容正则模式
    CONTENT_PATTERNS = [
        # 密码
        (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\'}\]]{4,})["\']?',
         SensitiveType.PASSWORD, "high"),

        # API Key
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?([^\s"\'}\]]{10,})["\']?',
         SensitiveType.API_KEY, "high"),

        # Secret
        (r'(?i)(secret[_-]?key|secretkey|secret)\s*[=:]\s*["\']?([^\s"\'}\]]{8,})["\']?',
         SensitiveType.SECRET, "high"),

        # Token
        (r'(?i)(access[_-]?token|auth[_-]?token|token)\s*[=:]\s*["\']?([^\s"\'}\]]{10,})["\']?',
         SensitiveType.TOKEN, "high"),

        # 私钥
        (r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----',
         SensitiveType.PRIVATE_KEY, "critical"),

        # 证书
        (r'-----BEGIN CERTIFICATE-----',
         SensitiveType.CERTIFICATE, "medium"),

        # 数据库连接串
        (r'(?i)(mysql|postgres|mongodb|redis)://[^\s@]+:[^\s@]+@[^\s]+',
         SensitiveType.DATABASE_URL, "high"),

        # AWS 密钥
        (r'(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}',
         SensitiveType.API_KEY, "critical"),

        # 通用凭证模式
        (r'(?i)(client[_-]?id|client[_-]?secret)\s*[=:]\s*["\']?([^\s"\'}\]]{8,})["\']?',
         SensitiveType.CREDENTIALS, "medium"),
    ]

    # 排除目录
    DEFAULT_EXCLUDE_DIRS = {
        '.git', '.svn', '.hg',
        'node_modules', 'venv', '.venv', 'env',
        '__pycache__', '.pytest_cache',
        'dist', 'build', 'target', 'out',
        '.gradle', '.idea', '.vscode',
    }

    # 排除文件
    DEFAULT_EXCLUDE_FILES = {
        '*.min.js', '*.min.css',
        '*.lock', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
        '*.map', '*.pyc', '*.pyo',
    }

    def __init__(self, config: Dict[str, Any] = None):
        """初始化扫描器

        Args:
            config: 安全配置
        """
        self.config = config or {}

        # 自定义排除规则
        self.exclude_dirs = self.DEFAULT_EXCLUDE_DIRS | set(
            self.config.get('exclude_dirs', [])
        )
        self.exclude_files = self.DEFAULT_EXCLUDE_FILES | set(
            self.config.get('exclude_files', [])
        )

        # 自定义敏感文件模式
        self.sensitive_patterns = self.SENSITIVE_FILE_PATTERNS + list(
            self.config.get('sensitive_patterns', [])
        )

        # 行为模式: warn, error, ignore
        self.on_sensitive_found = self.config.get('on_sensitive_found', 'warn')

    def scan(self, project_dir: str, max_files: int = 1000) -> ScanResult:
        """扫描项目敏感信息

        Args:
            project_dir: 项目目录
            max_files: 最大扫描文件数

        Returns:
            ScanResult: 扫描结果
        """
        import time
        start_time = time.time()

        result = ScanResult(project_dir=project_dir)
        project_path = Path(project_dir).resolve()

        if not project_path.exists():
            result.errors.append(f"Project directory not found: {project_dir}")
            return result

        # 遍历文件
        for root, dirs, files in os.walk(project_path):
            # 排除目录
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for f in files:
                if result.scanned_files >= max_files:
                    break

                file_path = Path(root) / f
                rel_path = file_path.relative_to(project_path)
                rel_path_str = str(rel_path).replace('\\', '/')

                # 检查是否应排除
                if self._should_exclude_file(f, rel_path_str):
                    result.excluded_files.append(rel_path_str)
                    continue

                # 检查敏感文件
                if self._is_sensitive_file(f, rel_path_str):
                    result.sensitive_files.append(rel_path_str)
                    if self.on_sensitive_found != 'ignore':
                        result.matches.append(SensitiveMatch(
                            file_path=rel_path_str,
                            line_number=0,
                            sensitive_type=SensitiveType.ENV_FILE,
                            original="",
                            masked="***SENSITIVE FILE***",
                            pattern="file_pattern",
                            severity="high",
                        ))
                    continue

                # 扫描文件内容
                if self._should_scan_content(f):
                    try:
                        matches = self._scan_file_content(file_path, rel_path_str)
                        result.matches.extend(matches)
                    except Exception as e:
                        result.errors.append(f"{rel_path_str}: {str(e)}")

                result.scanned_files += 1

        elapsed = time.time() - start_time
        result.scan_time = f"{elapsed:.2f}s"

        return result

    def _should_exclude_file(self, filename: str, rel_path: str) -> bool:
        """判断是否应排除文件"""
        for pattern in self.exclude_files:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return True
        return False

    def _is_sensitive_file(self, filename: str, rel_path: str) -> bool:
        """判断是否是敏感文件"""
        for pattern in self.sensitive_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return True
        return False

    def _should_scan_content(self, filename: str) -> bool:
        """判断是否应扫描文件内容"""
        # 只扫描文本文件
        text_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.kt', '.swift',
            '.c', '.cpp', '.h', '.hpp', '.cc', '.go', '.rs', '.rb', '.php',
            '.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.conf', '.cfg',
            '.sh', '.bash', '.zsh', '.bat', '.ps1',
            '.md', '.txt', '.rst', '.env',
            '.html', '.css', '.scss', '.less', '.vue', '.svelte',
        }

        ext = Path(filename).suffix.lower()
        return ext in text_extensions

    def _scan_file_content(self, file_path: Path, rel_path: str) -> List[SensitiveMatch]:
        """扫描文件内容"""
        matches = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            return matches

        for i, line in enumerate(lines, 1):
            for pattern, sensitive_type, severity in self.CONTENT_PATTERNS:
                for match in re.finditer(pattern, line):
                    original = match.group(0)
                    masked = self.mask_content(original, sensitive_type)

                    matches.append(SensitiveMatch(
                        file_path=rel_path,
                        line_number=i,
                        sensitive_type=sensitive_type,
                        original=original,
                        masked=masked,
                        pattern=pattern[:50] + "..." if len(pattern) > 50 else pattern,
                        severity=severity,
                    ))

        return matches

    def mask_content(self, content: str, sensitive_type: SensitiveType = None) -> str:
        """脱敏处理

        Args:
            content: 原始内容
            sensitive_type: 敏感信息类型

        Returns:
            脱敏后的内容
        """
        # 私钥和证书特殊处理
        if sensitive_type in (SensitiveType.PRIVATE_KEY, SensitiveType.CERTIFICATE):
            if '-----BEGIN' in content:
                return '***MASKED SENSITIVE DATA***'

        # 替换敏感值
        for pattern, st, _ in self.CONTENT_PATTERNS:
            if sensitive_type and st != sensitive_type:
                continue

            def replace_sensitive(m):
                # 保留键名，只替换值
                groups = m.groups()
                if len(groups) >= 2:
                    key = groups[0]
                    return f'{key}="***MASKED***"'
                return '***MASKED***'

            content = re.sub(pattern, replace_sensitive, content)

        return content

    def mask_file(self, file_path: str, output_path: str = None) -> Dict[str, Any]:
        """脱敏整个文件

        Args:
            file_path: 原始文件路径
            output_path: 输出文件路径（可选，默认原地修改）

        Returns:
            处理结果
        """
        result = {
            'file': file_path,
            'masked_count': 0,
            'success': False,
            'error': None,
        }

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.read()

            masked_content = self.mask_content(original_content)

            # 计算脱敏数量
            result['masked_count'] = original_content.count('***MASKED***') - \
                                    masked_content.count('***MASKED***') + \
                                    masked_content.count('***MASKED***')

            output = output_path or file_path
            with open(output, 'w', encoding='utf-8') as f:
                f.write(masked_content)

            result['success'] = True

        except Exception as e:
            result['error'] = str(e)

        return result

    def should_exclude(self, file_path: str) -> bool:
        """判断是否应排除文件（公开方法）"""
        filename = Path(file_path).name
        return self._should_exclude_file(filename, file_path) or \
               self._is_sensitive_file(filename, file_path)

    def get_safe_content(self, file_path: str) -> str:
        """获取脱敏后的文件内容

        Args:
            file_path: 文件路径

        Returns:
            脱敏后的内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return self.mask_content(content)
        except Exception:
            return ""


def scan_project(project_dir: str, config: Dict[str, Any] = None) -> ScanResult:
    """扫描项目敏感信息的便捷函数"""
    scanner = SensitiveScanner(config)
    return scanner.scan(project_dir)


def main():
    """命令行接口"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: sensitive_scanner.py <project_dir> [--json] [--mask]")
        print("\nOptions:")
        print("  --json    Output as JSON")
        print("  --mask    Show masked content instead of original")
        sys.exit(1)

    project_dir = sys.argv[1]
    output_json = '--json' in sys.argv
    show_masked = '--mask' in sys.argv

    scanner = SensitiveScanner()
    result = scanner.scan(project_dir)

    if output_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"\n=== 敏感信息扫描结果 ===")
        print(f"项目目录: {result.project_dir}")
        print(f"扫描文件: {result.scanned_files}")
        print(f"扫描耗时: {result.scan_time}")

        if result.sensitive_files:
            print(f"\n发现敏感文件 ({len(result.sensitive_files)}):")
            for f in result.sensitive_files[:10]:
                print(f"  - {f}")
            if len(result.sensitive_files) > 10:
                print(f"  ... 还有 {len(result.sensitive_files) - 10} 个")

        if result.matches:
            print(f"\n发现敏感内容 ({len(result.matches)}):")
            for m in result.matches[:10]:
                content = m.masked if show_masked else f"{m.sensitive_type.value}=***"
                print(f"  - {m.file_path}:{m.line_number} [{m.severity}] {content}")
            if len(result.matches) > 10:
                print(f"  ... 还有 {len(result.matches) - 10} 处")

        if not result.has_sensitive:
            print("\n未发现敏感信息")


if __name__ == '__main__':
    main()