#!/usr/bin/env python3
"""
安全模块
提供敏感信息保护、审计日志等安全功能
"""

from .sensitive_scanner import (
    SensitiveScanner,
    SensitiveType,
    SensitiveMatch,
    ScanResult,
    scan_project,
)
from .security_config import (
    SecurityConfig,
    SecurityConfigManager,
    SensitiveConfig,
    AuditConfig,
    DataRetentionConfig,
    get_security_config,
    DEFAULT_SECURITY_CONFIG,
)
from .audit_logger import (
    AuditLogger,
    LogEntry,
    LogLevel,
    OperationType,
    get_audit_logger,
)

__all__ = [
    # Scanner
    'SensitiveScanner',
    'SensitiveType',
    'SensitiveMatch',
    'ScanResult',
    'scan_project',

    # Config
    'SecurityConfig',
    'SecurityConfigManager',
    'SensitiveConfig',
    'AuditConfig',
    'DataRetentionConfig',
    'get_security_config',
    'DEFAULT_SECURITY_CONFIG',

    # Audit
    'AuditLogger',
    'LogEntry',
    'LogLevel',
    'OperationType',
    'get_audit_logger',
]