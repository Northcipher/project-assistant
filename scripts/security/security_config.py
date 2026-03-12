#!/usr/bin/env python3
"""
安全配置管理
管理项目安全策略和配置

特性：
- YAML 配置文件支持
- 默认安全策略
- 自定义规则扩展
- 配置验证
"""

import os
import json
import yaml
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class SensitiveConfig:
    """敏感信息配置"""
    exclude_files: List[str] = field(default_factory=lambda: [
        '.env*', '*.pem', '*.key', 'credentials.json', 'secrets.json'
    ])
    exclude_dirs: List[str] = field(default_factory=lambda: [
        'secrets/', '.secrets/', 'private/', '.ssh/'
    ])
    mask_patterns: List[str] = field(default_factory=lambda: [
        'password', 'api_key', 'secret', 'token', 'private_key'
    ])
    on_sensitive_found: str = 'warn'  # warn | error | ignore


@dataclass
class AuditConfig:
    """审计配置"""
    enabled: bool = True
    log_file: str = '.projmeta/audit.log'
    log_level: str = 'info'  # debug | info | warn | error
    max_log_size_mb: int = 10
    log_rotation_count: int = 5


@dataclass
class DataRetentionConfig:
    """数据保留配置"""
    cache_ttl_days: int = 7
    qa_docs_ttl_days: int = 30
    audit_logs_ttl_days: int = 90


@dataclass
class SecurityConfig:
    """安全配置"""
    sensitive: SensitiveConfig = field(default_factory=SensitiveConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    data_retention: DataRetentionConfig = field(default_factory=DataRetentionConfig)


# 默认配置
DEFAULT_SECURITY_CONFIG = SecurityConfig()

# 默认 YAML 配置模板
DEFAULT_CONFIG_YAML = """# project-assistant 安全配置
# 配置敏感信息保护、审计日志、数据保留等

sensitive:
  # 排除的敏感文件（glob 模式）
  exclude_files:
    - '.env*'
    - '*.pem'
    - '*.key'
    - '*.p12'
    - 'credentials.json'
    - 'secrets.json'
    - 'secrets.yaml'
    - 'service-account.json'
    - 'id_rsa'
    - 'id_ed25519'

  # 排除的敏感目录
  exclude_dirs:
    - 'secrets/'
    - '.secrets/'
    - 'private/'
    - 'credentials/'
    - '.ssh/'
    - '.gnupg/'

  # 需要脱敏的模式关键词
  mask_patterns:
    - password
    - passwd
    - api_key
    - apikey
    - secret
    - secret_key
    - token
    - access_token
    - auth_token
    - private_key
    - client_secret
    - credentials

  # 发现敏感信息时的行为
  # warn: 警告并继续
  # error: 报错并停止
  # ignore: 忽略继续
  on_sensitive_found: warn

audit:
  # 是否启用审计日志
  enabled: true

  # 日志文件路径（相对于项目根目录）
  log_file: .projmeta/audit.log

  # 日志级别
  # debug: 详细调试信息
  # info: 一般信息
  # warn: 警告信息
  # error: 错误信息
  log_level: info

  # 日志文件最大大小（MB）
  max_log_size_mb: 10

  # 日志轮转保留数量
  log_rotation_count: 5

data_retention:
  # 缓存保留天数
  cache_ttl_days: 7

  # 问答文档保留天数
  qa_docs_ttl_days: 30

  # 审计日志保留天数
  audit_logs_ttl_days: 90
"""


class SecurityConfigManager:
    """安全配置管理器"""

    CONFIG_FILE_NAME = 'security-config.yaml'

    def __init__(self, project_dir: str = None, config_path: str = None):
        """初始化配置管理器

        Args:
            project_dir: 项目目录
            config_path: 配置文件路径（可选）
        """
        self.project_dir = Path(project_dir) if project_dir else None
        self._config_path = config_path
        self._config: Optional[SecurityConfig] = None

    @property
    def config_path(self) -> Optional[Path]:
        """配置文件路径"""
        if self._config_path:
            return Path(self._config_path)

        if self.project_dir:
            # 查找配置文件
            candidates = [
                self.project_dir / self.CONFIG_FILE_NAME,
                self.project_dir / '.projmeta' / self.CONFIG_FILE_NAME,
            ]
            for path in candidates:
                if path.exists():
                    return path

        return None

    def load(self) -> SecurityConfig:
        """加载配置"""
        if self._config is not None:
            return self._config

        config_path = self.config_path

        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                self._config = self._parse_config(data)
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")
                self._config = DEFAULT_SECURITY_CONFIG
        else:
            self._config = DEFAULT_SECURITY_CONFIG

        return self._config

    def _parse_config(self, data: Dict[str, Any]) -> SecurityConfig:
        """解析配置数据"""
        sensitive_data = data.get('sensitive', {})
        audit_data = data.get('audit', {})
        retention_data = data.get('data_retention', {})

        return SecurityConfig(
            sensitive=SensitiveConfig(
                exclude_files=sensitive_data.get('exclude_files',
                                                  DEFAULT_SECURITY_CONFIG.sensitive.exclude_files),
                exclude_dirs=sensitive_data.get('exclude_dirs',
                                                 DEFAULT_SECURITY_CONFIG.sensitive.exclude_dirs),
                mask_patterns=sensitive_data.get('mask_patterns',
                                                  DEFAULT_SECURITY_CONFIG.sensitive.mask_patterns),
                on_sensitive_found=sensitive_data.get('on_sensitive_found', 'warn'),
            ),
            audit=AuditConfig(
                enabled=audit_data.get('enabled', True),
                log_file=audit_data.get('log_file', '.projmeta/audit.log'),
                log_level=audit_data.get('log_level', 'info'),
                max_log_size_mb=audit_data.get('max_log_size_mb', 10),
                log_rotation_count=audit_data.get('log_rotation_count', 5),
            ),
            data_retention=DataRetentionConfig(
                cache_ttl_days=retention_data.get('cache_ttl_days', 7),
                qa_docs_ttl_days=retention_data.get('qa_docs_ttl_days', 30),
                audit_logs_ttl_days=retention_data.get('audit_logs_ttl_days', 90),
            ),
        )

    def save(self, config: SecurityConfig = None, path: str = None) -> None:
        """保存配置"""
        config = config or self._config or DEFAULT_SECURITY_CONFIG
        save_path = Path(path) if path else (
            self.project_dir / self.CONFIG_FILE_NAME if self.project_dir
            else Path(self.CONFIG_FILE_NAME)
        )

        save_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'sensitive': {
                'exclude_files': config.sensitive.exclude_files,
                'exclude_dirs': config.sensitive.exclude_dirs,
                'mask_patterns': config.sensitive.mask_patterns,
                'on_sensitive_found': config.sensitive.on_sensitive_found,
            },
            'audit': {
                'enabled': config.audit.enabled,
                'log_file': config.audit.log_file,
                'log_level': config.audit.log_level,
                'max_log_size_mb': config.audit.max_log_size_mb,
                'log_rotation_count': config.audit.log_rotation_count,
            },
            'data_retention': {
                'cache_ttl_days': config.data_retention.cache_ttl_days,
                'qa_docs_ttl_days': config.data_retention.qa_docs_ttl_days,
                'audit_logs_ttl_days': config.data_retention.audit_logs_ttl_days,
            },
        }

        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def create_default_config(self, project_dir: str = None) -> Path:
        """创建默认配置文件"""
        target_dir = Path(project_dir) if project_dir else self.project_dir
        if not target_dir:
            target_dir = Path.cwd()

        config_path = target_dir / self.CONFIG_FILE_NAME

        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_CONFIG_YAML)

        return config_path

    def get_scanner_config(self) -> Dict[str, Any]:
        """获取扫描器配置"""
        config = self.load()
        return {
            'exclude_files': config.sensitive.exclude_files,
            'exclude_dirs': config.sensitive.exclude_dirs,
            'mask_patterns': config.sensitive.mask_patterns,
            'on_sensitive_found': config.sensitive.on_sensitive_found,
        }

    def get_audit_config(self) -> AuditConfig:
        """获取审计配置"""
        config = self.load()
        return config.audit

    def validate(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        config = self.load()

        # 验证 on_sensitive_found
        if config.sensitive.on_sensitive_found not in ('warn', 'error', 'ignore'):
            errors.append(f"Invalid on_sensitive_found: {config.sensitive.on_sensitive_found}")

        # 验证 log_level
        if config.audit.log_level not in ('debug', 'info', 'warn', 'error'):
            errors.append(f"Invalid log_level: {config.audit.log_level}")

        # 验证数值
        if config.audit.max_log_size_mb <= 0:
            errors.append("max_log_size_mb must be positive")

        if config.data_retention.cache_ttl_days <= 0:
            errors.append("cache_ttl_days must be positive")

        return errors


def get_security_config(project_dir: str = None) -> SecurityConfig:
    """获取安全配置的便捷函数"""
    manager = SecurityConfigManager(project_dir)
    return manager.load()


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: security_config.py <command> [args]")
        print("\nCommands:")
        print("  show [project_dir]        Show current config")
        print("  create [project_dir]      Create default config file")
        print("  validate [project_dir]    Validate config")
        sys.exit(1)

    command = sys.argv[1]
    project_dir = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()

    manager = SecurityConfigManager(project_dir)

    if command == 'show':
        config = manager.load()
        print(yaml.dump({
            'sensitive': {
                'exclude_files': config.sensitive.exclude_files,
                'exclude_dirs': config.sensitive.exclude_dirs,
                'mask_patterns': config.sensitive.mask_patterns,
                'on_sensitive_found': config.sensitive.on_sensitive_found,
            },
            'audit': {
                'enabled': config.audit.enabled,
                'log_file': config.audit.log_file,
                'log_level': config.audit.log_level,
            },
            'data_retention': {
                'cache_ttl_days': config.data_retention.cache_ttl_days,
                'qa_docs_ttl_days': config.data_retention.qa_docs_ttl_days,
            },
        }, default_flow_style=False))

    elif command == 'create':
        path = manager.create_default_config()
        print(f"Created: {path}")

    elif command == 'validate':
        errors = manager.validate()
        if errors:
            print("Validation errors:")
            for e in errors:
                print(f"  - {e}")
        else:
            print("Config is valid")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()