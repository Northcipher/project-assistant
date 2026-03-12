#!/usr/bin/env python3
"""
团队数据库
SQLite 数据库管理团队用户、权限、问答分享

特性:
- 用户管理
- 权限存储
- 问答分享记录
- 投票记录
"""

import os
import json
import sqlite3
import uuid
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from contextlib import contextmanager


@dataclass
class User:
    """用户"""
    id: str
    name: str
    email: str = ""
    role: str = "member"
    created_at: str = ""
    last_login: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at,
            'last_login': self.last_login,
        }


@dataclass
class Team:
    """团队"""
    id: str
    name: str
    description: str = ""
    owner_id: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'owner_id': self.owner_id,
            'created_at': self.created_at,
        }


class TeamDatabase:
    """团队数据库

    表结构:
    - users: 用户表
    - teams: 团队表
    - team_members: 团队成员关联表
    - qa_shares: 问答分享表
    - qa_votes: 问答投票表
    - audit_log: 审计日志表
    """

    SCHEMA = """
    -- 用户表
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        password_hash TEXT,
        role TEXT DEFAULT 'member',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    );

    -- 团队表
    CREATE TABLE IF NOT EXISTS teams (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        owner_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(id)
    );

    -- 团队成员关联表
    CREATE TABLE IF NOT EXISTS team_members (
        team_id TEXT,
        user_id TEXT,
        role TEXT DEFAULT 'member',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (team_id, user_id),
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- 问答分享表
    CREATE TABLE IF NOT EXISTS qa_shares (
        qa_id TEXT,
        team_id TEXT,
        shared_by TEXT,
        shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (qa_id, team_id),
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (shared_by) REFERENCES users(id)
    );

    -- 问答投票表
    CREATE TABLE IF NOT EXISTS qa_votes (
        qa_id TEXT,
        user_id TEXT,
        vote INTEGER CHECK (vote IN (1, -1)),
        voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (qa_id, user_id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- 审计日志表
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action TEXT NOT NULL,
        resource_type TEXT,
        resource_id TEXT,
        details TEXT,
        ip_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- 索引
    CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);
    CREATE INDEX IF NOT EXISTS idx_teams_name ON teams(name);
    CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
    CREATE INDEX IF NOT EXISTS idx_qa_shares_team ON qa_shares(team_id);
    CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
    CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
    """

    def __init__(self, db_path: str = None):
        """初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            # 默认路径
            self.db_path = Path.home() / '.projmeta' / 'team.db'

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库"""
        with self._get_connection() as conn:
            conn.executescript(self.SCHEMA)

    # 用户管理
    def create_user(self, name: str, email: str = None, password: str = None,
                    role: str = 'member') -> User:
        """创建用户"""
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        password_hash = self._hash_password(password) if password else None

        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO users (id, name, email, password_hash, role)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, name, email, password_hash, role)
            )

        return User(id=user_id, name=name, email=email or "", role=role,
                    created_at=datetime.now().isoformat())

    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()

            if row:
                return User(
                    id=row['id'],
                    name=row['name'],
                    email=row['email'] or "",
                    role=row['role'],
                    created_at=row['created_at'],
                    last_login=row['last_login'] or "",
                )
        return None

    def get_user_by_name(self, name: str) -> Optional[User]:
        """根据名称获取用户"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE name = ?", (name,)
            ).fetchone()

            if row:
                return User(
                    id=row['id'],
                    name=row['name'],
                    email=row['email'] or "",
                    role=row['role'],
                    created_at=row['created_at'],
                    last_login=row['last_login'] or "",
                )
        return None

    def update_user(self, user_id: str, **kwargs) -> bool:
        """更新用户"""
        allowed_fields = {'name', 'email', 'role'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        set_clause = ', '.join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]

        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE users SET {set_clause} WHERE id = ?",
                values
            )

        return True

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM team_members WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return True

    def list_users(self, limit: int = 100) -> List[User]:
        """列出用户"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM users ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()

            return [User(
                id=row['id'],
                name=row['name'],
                email=row['email'] or "",
                role=row['role'],
                created_at=row['created_at'],
                last_login=row['last_login'] or "",
            ) for row in rows]

    # 团队管理
    def create_team(self, name: str, description: str = None,
                    owner_id: str = None) -> Team:
        """创建团队"""
        team_id = f"team_{uuid.uuid4().hex[:8]}"

        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO teams (id, name, description, owner_id)
                   VALUES (?, ?, ?, ?)""",
                (team_id, name, description, owner_id)
            )

            # 添加所有者到团队成员
            if owner_id:
                conn.execute(
                    """INSERT INTO team_members (team_id, user_id, role)
                       VALUES (?, ?, 'admin')""",
                    (team_id, owner_id)
                )

        return Team(
            id=team_id,
            name=name,
            description=description or "",
            owner_id=owner_id or "",
            created_at=datetime.now().isoformat()
        )

    def get_team(self, team_id: str) -> Optional[Team]:
        """获取团队"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM teams WHERE id = ?", (team_id,)
            ).fetchone()

            if row:
                return Team(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'] or "",
                    owner_id=row['owner_id'] or "",
                    created_at=row['created_at'],
                )
        return None

    def get_team_by_name(self, name: str) -> Optional[Team]:
        """根据名称获取团队"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM teams WHERE name = ?", (name,)
            ).fetchone()

            if row:
                return Team(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'] or "",
                    owner_id=row['owner_id'] or "",
                    created_at=row['created_at'],
                )
        return None

    def add_team_member(self, team_id: str, user_id: str, role: str = 'member') -> bool:
        """添加团队成员"""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO team_members (team_id, user_id, role)
                   VALUES (?, ?, ?)""",
                (team_id, user_id, role)
            )
        return True

    def remove_team_member(self, team_id: str, user_id: str) -> bool:
        """移除团队成员"""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM team_members WHERE team_id = ? AND user_id = ?",
                (team_id, user_id)
            )
        return True

    def get_team_members(self, team_id: str) -> List[Dict]:
        """获取团队成员"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT u.*, tm.role as team_role, tm.joined_at
                   FROM users u
                   JOIN team_members tm ON u.id = tm.user_id
                   WHERE tm.team_id = ?""",
                (team_id,)
            ).fetchall()

            return [dict(row) for row in rows]

    def get_user_teams(self, user_id: str) -> List[Team]:
        """获取用户所属团队"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT t.*
                   FROM teams t
                   JOIN team_members tm ON t.id = tm.team_id
                   WHERE tm.user_id = ?""",
                (user_id,)
            ).fetchall()

            return [Team(
                id=row['id'],
                name=row['name'],
                description=row['description'] or "",
                owner_id=row['owner_id'] or "",
                created_at=row['created_at'],
            ) for row in rows]

    # 问答分享
    def share_qa(self, qa_id: str, team_id: str, shared_by: str) -> bool:
        """分享问答到团队"""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO qa_shares (qa_id, team_id, shared_by)
                   VALUES (?, ?, ?)""",
                (qa_id, team_id, shared_by)
            )
        return True

    def unshare_qa(self, qa_id: str, team_id: str) -> bool:
        """取消分享"""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM qa_shares WHERE qa_id = ? AND team_id = ?",
                (qa_id, team_id)
            )
        return True

    def get_team_qa(self, team_id: str) -> List[str]:
        """获取团队分享的问答 ID 列表"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT qa_id FROM qa_shares WHERE team_id = ?",
                (team_id,)
            ).fetchall()
            return [row['qa_id'] for row in rows]

    def get_qa_teams(self, qa_id: str) -> List[str]:
        """获取问答分享到的团队列表"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT team_id FROM qa_shares WHERE qa_id = ?",
                (qa_id,)
            ).fetchall()
            return [row['team_id'] for row in rows]

    # 投票
    def vote_qa(self, qa_id: str, user_id: str, vote: int) -> bool:
        """为问答投票"""
        if vote not in (1, -1):
            return False

        with self._get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO qa_votes (qa_id, user_id, vote)
                   VALUES (?, ?, ?)""",
                (qa_id, user_id, vote)
            )
        return True

    def get_qa_votes(self, qa_id: str) -> int:
        """获取问答总投票数"""
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT SUM(vote) as total FROM qa_votes WHERE qa_id = ?",
                (qa_id,)
            ).fetchone()
            return result['total'] or 0

    def get_user_vote(self, qa_id: str, user_id: str) -> Optional[int]:
        """获取用户对问答的投票"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT vote FROM qa_votes WHERE qa_id = ? AND user_id = ?",
                (qa_id, user_id)
            ).fetchone()
            return row['vote'] if row else None

    # 审计日志
    def log_action(self, user_id: str, action: str, resource_type: str = None,
                   resource_id: str = None, details: Dict = None,
                   ip_address: str = None) -> bool:
        """记录审计日志"""
        with self._get_connection() as conn:
            conn.execute(
                """INSERT INTO audit_log
                   (user_id, action, resource_type, resource_id, details, ip_address)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, action, resource_type, resource_id,
                 json.dumps(details) if details else None, ip_address)
            )
        return True

    def get_audit_log(self, user_id: str = None, action: str = None,
                      start_time: str = None, end_time: str = None,
                      limit: int = 100) -> List[Dict]:
        """获取审计日志"""
        conditions = []
        params = []

        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(
                f"""SELECT * FROM audit_log
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT ?""",
                params
            ).fetchall()

            return [dict(row) for row in rows]

    # 辅助方法
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, user_id: str, password: str) -> bool:
        """验证密码"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()

            if row and row['password_hash']:
                return row['password_hash'] == self._hash_password(password)
        return False


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: team_db.py <command> [args]")
        print("\nCommands:")
        print("  create-user <name> [email]     Create a user")
        print("  create-team <name> [owner]     Create a team")
        print("  list-users                     List all users")
        print("  list-teams                     List all teams")
        print("  add-member <team> <user>       Add member to team")
        print("  share-qa <qa_id> <team>        Share QA to team")
        print("  audit-log                      Show audit log")
        sys.exit(1)

    db = TeamDatabase()
    command = sys.argv[1]

    if command == 'create-user':
        name = sys.argv[2]
        email = sys.argv[3] if len(sys.argv) > 3 else None
        user = db.create_user(name, email)
        print(json.dumps(user.to_dict(), indent=2))

    elif command == 'create-team':
        name = sys.argv[2]
        owner = sys.argv[3] if len(sys.argv) > 3 else None
        team = db.create_team(name, owner_id=owner)
        print(json.dumps(team.to_dict(), indent=2))

    elif command == 'list-users':
        users = db.list_users()
        for user in users:
            print(f"- {user.id}: {user.name} ({user.role})")

    elif command == 'list-teams':
        user_id = sys.argv[2] if len(sys.argv) > 2 else None
        if user_id:
            teams = db.get_user_teams(user_id)
        else:
            # 列出所有团队需要额外方法
            teams = []
        for team in teams:
            print(f"- {team.id}: {team.name}")

    elif command == 'add-member':
        team_name = sys.argv[2]
        user_name = sys.argv[3]
        team = db.get_team_by_name(team_name)
        user = db.get_user_by_name(user_name)
        if team and user:
            db.add_team_member(team.id, user.id)
            print(f"Added {user_name} to {team_name}")
        else:
            print("Team or user not found")

    elif command == 'share-qa':
        qa_id = sys.argv[2]
        team_name = sys.argv[3]
        team = db.get_team_by_name(team_name)
        if team:
            db.share_qa(qa_id, team.id, "system")
            print(f"Shared {qa_id} to {team_name}")
        else:
            print("Team not found")

    elif command == 'audit-log':
        logs = db.get_audit_log()
        for log in logs[:20]:
            print(f"[{log['timestamp']}] {log['action']}: {log['details']}")


if __name__ == '__main__':
    main()