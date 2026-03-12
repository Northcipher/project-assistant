#!/usr/bin/env python3
"""
Webhook 服务器
事件驱动集成

特性:
- GitHub Webhook 支持
- GitLab Webhook 支持
- Jira Webhook 支持
- 事件处理和路由
"""

import os
import json
import hmac
import hashlib
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading


class WebhookSource(Enum):
    """Webhook 来源"""
    GITHUB = "github"
    GITLAB = "gitlab"
    JIRA = "jira"
    AZURE_DEVOPS = "azure_devops"
    CUSTOM = "custom"


@dataclass
class WebhookEvent:
    """Webhook 事件"""
    source: WebhookSource
    event_type: str
    payload: Dict[str, Any]
    headers: Dict[str, str] = field(default_factory=dict)
    timestamp: str = ""
    signature: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class WebhookHandler(BaseHTTPRequestHandler):
    """Webhook HTTP 处理器"""

    server = None  # 将被 WebhookServer 设置

    def log_message(self, format, *args):
        """自定义日志"""
        if self.server and hasattr(self.server, 'logger'):
            self.server.logger(f"[Webhook] {format % args}")
        else:
            print(f"[Webhook] {format % args}")

    def do_GET(self):
        """处理 GET 请求（健康检查）"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """处理 POST 请求"""
        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''

        # 解析 JSON
        try:
            payload = json.loads(body.decode('utf-8'))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        # 获取事件类型和来源
        source = self._detect_source()
        event_type = self._get_event_type(source)

        # 验证签名
        signature = self.headers.get('X-Hub-Signature-256', '')
        if not self._verify_signature(source, body, signature):
            self.send_response(401)
            self.end_headers()
            return

        # 创建事件
        event = WebhookEvent(
            source=source,
            event_type=event_type,
            payload=payload,
            headers=dict(self.headers),
            signature=signature,
        )

        # 分发事件
        if self.server and hasattr(self.server, 'handle_event'):
            response = self.server.handle_event(event)
        else:
            response = {'status': 'processed'}

        # 返回响应
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def _detect_source(self) -> WebhookSource:
        """检测 Webhook 来源"""
        user_agent = self.headers.get('User-Agent', '')

        if 'GitHub-Hookshot' in user_agent:
            return WebhookSource.GITHUB
        elif 'GitLab' in user_agent:
            return WebhookSource.GITLAB
        elif 'Atlassian' in user_agent or 'Jira' in user_agent:
            return WebhookSource.JIRA
        elif 'AzureDevOps' in user_agent:
            return WebhookSource.AZURE_DEVOPS
        else:
            return WebhookSource.CUSTOM

    def _get_event_type(self, source: WebhookSource) -> str:
        """获取事件类型"""
        if source == WebhookSource.GITHUB:
            return self.headers.get('X-GitHub-Event', 'unknown')
        elif source == WebhookSource.GITLAB:
            return self.headers.get('X-Gitlab-Event', 'unknown').replace(' ', '_').lower()
        elif source == WebhookSource.JIRA:
            return self.headers.get('X-Atlassian-Webhook-Event', 'unknown')
        else:
            return 'unknown'

    def _verify_signature(self, source: WebhookSource, body: bytes,
                          signature: str) -> bool:
        """验证签名"""
        if not self.server or not hasattr(self.server, 'secrets'):
            return True  # 未配置密钥时跳过验证

        secret = self.server.secrets.get(source.value)
        if not secret:
            return True

        if source == WebhookSource.GITHUB:
            expected = 'sha256=' + hmac.new(
                secret.encode(), body, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)

        elif source == WebhookSource.GITLAB:
            token = self.headers.get('X-Gitlab-Token', '')
            return hmac.compare_digest(token, secret)

        return True


class WebhookServer:
    """Webhook 服务器

    支持的事件:
    - GitHub: push, pull_request, issues, release
    - GitLab: push, merge_request, issues, pipeline
    - Jira: issue_created, issue_updated
    """

    ENDPOINTS = {
        '/webhook/github': WebhookSource.GITHUB,
        '/webhook/gitlab': WebhookSource.GITLAB,
        '/webhook/jira': WebhookSource.JIRA,
        '/webhook/azure': WebhookSource.AZURE_DEVOPS,
        '/webhook': WebhookSource.CUSTOM,
    }

    def __init__(self, project_dir: str, host: str = '0.0.0.0',
                 port: int = 8080, secrets: Dict[str, str] = None):
        """初始化

        Args:
            project_dir: 项目目录
            host: 监听地址
            port: 监听端口
            secrets: 各平台的 secret/token
        """
        self.project_dir = Path(project_dir).resolve()
        self.host = host
        self.port = port
        self.secrets = secrets or {}

        # 事件处理器
        self._handlers: Dict[str, List[Callable]] = {}

        # 集成模块
        self._ci_cd = None
        self._issue_tracker = None
        self._code_review = None

        # HTTP 服务器
        self._server = None
        self._thread = None

    def start(self, background: bool = True):
        """启动服务器

        Args:
            background: 是否后台运行
        """
        # 初始化集成模块
        try:
            from integration.ci_cd import CICDIntegration
            self._ci_cd = CICDIntegration(str(self.project_dir))
        except ImportError:
            pass

        try:
            from integration.issue_tracker import IssueTrackerIntegration
            self._issue_tracker = IssueTrackerIntegration(str(self.project_dir))
        except ImportError:
            pass

        try:
            from integration.code_review import CodeReviewAssistant
            self._code_review = CodeReviewAssistant(str(self.project_dir))
        except ImportError:
            pass

        # 创建 HTTP 服务器
        self._server = HTTPServer((self.host, self.port), WebhookHandler)
        self._server.secrets = self.secrets
        self._server.handle_event = self.handle_event
        self._server.logger = self._log

        self._log(f"Webhook server starting on {self.host}:{self.port}")

        if background:
            self._thread = threading.Thread(target=self._server.serve_forever)
            self._thread.daemon = True
            self._thread.start()
        else:
            self._server.serve_forever()

    def stop(self):
        """停止服务器"""
        if self._server:
            self._server.shutdown()
            self._log("Webhook server stopped")

    def register_handler(self, event_type: str, handler: Callable):
        """注册事件处理器

        Args:
            event_type: 事件类型 (如 "github:pull_request")
            handler: 处理函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def handle_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """处理事件"""
        self._log(f"Received {event.source.value}:{event.event_type} event")

        # 构建事件键
        event_key = f"{event.source.value}:{event.event_type}"

        # 调用注册的处理器
        results = []
        for handler in self._handlers.get(event_key, []):
            try:
                result = handler(event)
                results.append(result)
            except Exception as e:
                self._log(f"Handler error: {e}")

        # 调用默认处理器
        default_result = self._default_handler(event)
        if default_result:
            results.append(default_result)

        return {'status': 'processed', 'results': len(results)}

    def _default_handler(self, event: WebhookEvent) -> Optional[Dict]:
        """默认事件处理器"""
        if event.source == WebhookSource.GITHUB:
            return self._handle_github(event)
        elif event.source == WebhookSource.GITLAB:
            return self._handle_gitlab(event)
        elif event.source == WebhookSource.JIRA:
            return self._handle_jira(event)
        return None

    def _handle_github(self, event: WebhookEvent) -> Optional[Dict]:
        """处理 GitHub 事件"""
        if event.event_type == 'pull_request':
            return self._handle_github_pr(event)
        elif event.event_type == 'push':
            return self._handle_github_push(event)
        elif event.event_type == 'issues':
            return self._handle_github_issues(event)
        return None

    def _handle_github_pr(self, event: WebhookEvent) -> Optional[Dict]:
        """处理 GitHub PR 事件"""
        action = event.payload.get('action')
        pr = event.payload.get('pull_request', {})

        if action in ('opened', 'synchronize'):
            if self._ci_cd:
                from integration.ci_cd import PRInfo, PRAction
                pr_info = PRInfo(
                    number=pr.get('number'),
                    title=pr.get('title'),
                    author=pr.get('user', {}).get('login'),
                    source_branch=pr.get('head', {}).get('ref'),
                    target_branch=pr.get('base', {}).get('ref'),
                    action=PRAction.OPENED if action == 'opened' else PRAction.SYNCHRONIZE,
                    files=[f.get('filename') for f in pr.get('files', [])],
                    additions=pr.get('additions', 0),
                    deletions=pr.get('deletions', 0),
                    url=pr.get('html_url'),
                )
                report = self._ci_cd.on_pr_created(pr_info)
                return {'action': 'pr_analyzed', 'score': report.overall_score}

        elif action == 'closed' and pr.get('merged'):
            if self._ci_cd:
                from integration.ci_cd import MergeInfo
                merge_info = MergeInfo(
                    commit_sha=pr.get('merge_commit_sha'),
                    author=pr.get('merged_by', {}).get('login'),
                    message=pr.get('title'),
                    merged_at=datetime.now().isoformat(),
                    pr_number=pr.get('number'),
                    files=[f.get('filename') for f in pr.get('files', [])],
                )
                result = self._ci_cd.on_merge(merge_info)
                return {'action': 'merge_processed', 'files_updated': result.get('files_processed')}

        return None

    def _handle_github_push(self, event: WebhookEvent) -> Optional[Dict]:
        """处理 GitHub push 事件"""
        # 更新索引
        commits = event.payload.get('commits', [])
        files = []
        for commit in commits:
            files.extend(commit.get('added', []))
            files.extend(commit.get('modified', []))
            files.extend(commit.get('removed', []))

        if files:
            return {'action': 'push_processed', 'files': len(files)}
        return None

    def _handle_github_issues(self, event: WebhookEvent) -> Optional[Dict]:
        """处理 GitHub Issues 事件"""
        action = event.payload.get('action')
        issue = event.payload.get('issue', {})

        if action == 'closed':
            # 检查关联问答
            if self._issue_tracker:
                issue_url = issue.get('html_url')
                qa_ids = self._issue_tracker.get_issue_qa(issue_url)
                return {'action': 'issue_closed', 'related_qa': qa_ids}

        return None

    def _handle_gitlab(self, event: WebhookEvent) -> Optional[Dict]:
        """处理 GitLab 事件"""
        event_type = event.event_type

        if event_type == 'merge_request':
            return self._handle_gitlab_mr(event)
        elif event_type == 'push':
            return self._handle_gitlab_push(event)

        return None

    def _handle_gitlab_mr(self, event: WebhookEvent) -> Optional[Dict]:
        """处理 GitLab MR 事件"""
        # 类似 GitHub PR 处理
        return None

    def _handle_gitlab_push(self, event: WebhookEvent) -> Optional[Dict]:
        """处理 GitLab push 事件"""
        return None

    def _handle_jira(self, event: WebhookEvent) -> Optional[Dict]:
        """处理 Jira 事件"""
        # Jira webhook 处理
        return None

    def _log(self, message: str):
        """日志"""
        print(f"[{datetime.now().isoformat()}] {message}")

    def get_routes(self) -> Dict[str, str]:
        """获取路由列表"""
        return {
            '/health': 'Health check endpoint',
            '/webhook/github': 'GitHub webhook endpoint',
            '/webhook/gitlab': 'GitLab webhook endpoint',
            '/webhook/jira': 'Jira webhook endpoint',
            '/webhook': 'Generic webhook endpoint',
        }


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: webhook_server.py <project_dir> [--port PORT]")
        print("\nOptions:")
        print("  --port PORT    Listen port (default: 8080)")
        print("  --foreground   Run in foreground")
        sys.exit(1)

    project_dir = sys.argv[1]
    port = 8080
    foreground = False

    for i, arg in enumerate(sys.argv):
        if arg == '--port' and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])
        elif arg == '--foreground':
            foreground = True

    server = WebhookServer(project_dir, port=port)

    print(f"Starting webhook server on port {port}")
    print("Endpoints:")
    for path, desc in server.get_routes().items():
        print(f"  {path}: {desc}")

    server.start(background=not foreground)

    if foreground:
        try:
            while True:
                pass
        except KeyboardInterrupt:
            server.stop()


if __name__ == '__main__':
    main()