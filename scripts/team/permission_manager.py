#!/usr/bin/env python3
"""
权限管理器
细粒度访问控制

特性:
- 角色定义
- 权限检查
- 资源访问控制
"""

import os
import json
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class Permission(Enum):
    """权限类型"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    MANAGE = "manage"
    ADMIN = "admin"


@dataclass
class Role:
    """角色定义"""
    name: str
    permissions: Set[str]
    description: str = ""

    def has_permission(self, permission: str) -> bool:
        """检查是否有权限"""
        return permission in self.permissions or Permission.ADMIN.value in self.permissions


# 预定义角色
DEFAULT_ROLES = {
    'admin': Role(
        name='admin',
        permissions={'read', 'write', 'delete', 'share', 'manage', 'admin'},
        description='Full administrative access'
    ),
    'member': Role(
        name='member',
        permissions={'read', 'write', 'share'},
        description='Team member with read/write access'
    ),
    'viewer': Role(
        name='viewer',
        permissions={'read'},
        description='Read-only access'
    ),
    'contributor': Role(
        name='contributor',
        permissions={'read', 'write'},
        description='Can read and write but not share'
    ),
}


@dataclass
class Resource:
    """资源定义"""
    type: str  # qa, project, team, file, etc.
    id: str
    owner_id: str = ""
    team_id: str = ""
    visibility: str = "team"  # public, team, private
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'id': self.id,
            'owner_id': self.owner_id,
            'team_id': self.team_id,
            'visibility': self.visibility,
            'created_at': self.created_at,
        }


@dataclass
class AccessControlEntry:
    """访问控制条目"""
    resource_type: str
    resource_id: str
    user_id: str
    role: str
    granted_by: str
    granted_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'user_id': self.user_id,
            'role': self.role,
            'granted_by': self.granted_by,
            'granted_at': self.granted_at,
        }


class PermissionManager:
    """权限管理器

    权限检查流程:
    1. 检查用户是否是资源所有者
    2. 检查用户是否在资源关联的团队中
    3. 检查是否有显式授权
    4. 检查资源的可见性
    """

    def __init__(self, db_path: str = None):
        """初始化权限管理器

        Args:
            db_path: 数据库路径
        """
        self.db_path = Path(db_path) if db_path else None
        self._roles: Dict[str, Role] = dict(DEFAULT_ROLES)
        self._acl: List[AccessControlEntry] = []
        self._resources: Dict[str, Resource] = {}

        if self.db_path:
            self._load_acl()

    def define_role(self, name: str, permissions: List[str], description: str = "") -> Role:
        """定义新角色

        Args:
            name: 角色名称
            permissions: 权限列表
            description: 描述

        Returns:
            创建的角色
        """
        role = Role(
            name=name,
            permissions=set(permissions),
            description=description
        )
        self._roles[name] = role
        return role

    def get_role(self, name: str) -> Optional[Role]:
        """获取角色定义"""
        return self._roles.get(name)

    def list_roles(self) -> List[Role]:
        """列出所有角色"""
        return list(self._roles.values())

    def grant_role(self, user_id: str, resource_type: str, resource_id: str,
                   role_name: str, granted_by: str) -> bool:
        """授予角色

        Args:
            user_id: 用户 ID
            resource_type: 资源类型
            resource_id: 资源 ID
            role_name: 角色名称
            granted_by: 授权者 ID

        Returns:
            是否成功
        """
        if role_name not in self._roles:
            return False

        # 移除旧的角色
        self._acl = [ace for ace in self._acl
                     if not (ace.user_id == user_id and
                             ace.resource_type == resource_type and
                             ace.resource_id == resource_id)]

        # 添加新的角色
        ace = AccessControlEntry(
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            role=role_name,
            granted_by=granted_by,
            granted_at=datetime.now().isoformat()
        )
        self._acl.append(ace)

        if self.db_path:
            self._save_acl()

        return True

    def revoke_role(self, user_id: str, resource_type: str, resource_id: str) -> bool:
        """撤销角色"""
        original_count = len(self._acl)
        self._acl = [ace for ace in self._acl
                     if not (ace.user_id == user_id and
                             ace.resource_type == resource_type and
                             ace.resource_id == resource_id)]

        if len(self._acl) < original_count:
            if self.db_path:
                self._save_acl()
            return True
        return False

    def check_permission(self, user_id: str, resource_type: str, resource_id: str,
                         action: str, team_memberships: List[str] = None) -> bool:
        """检查权限

        Args:
            user_id: 用户 ID
            resource_type: 资源类型
            resource_id: 资源 ID
            action: 操作 (read, write, delete, share, manage)
            team_memberships: 用户所属团队 ID 列表

        Returns:
            是否有权限
        """
        # 1. 检查是否是资源所有者
        resource = self._resources.get(f"{resource_type}:{resource_id}")
        if resource and resource.owner_id == user_id:
            return True

        # 2. 检查显式授权
        for ace in self._acl:
            if (ace.user_id == user_id and
                ace.resource_type == resource_type and
                ace.resource_id == resource_id):
                role = self._roles.get(ace.role)
                if role and role.has_permission(action):
                    return True

        # 3. 检查团队权限
        if resource and team_memberships:
            if resource.team_id in team_memberships:
                # 团队成员默认有读取权限
                if action == Permission.READ.value:
                    return True
                # 检查团队角色
                for ace in self._acl:
                    if (ace.resource_type == 'team' and
                        ace.resource_id == resource.team_id and
                        ace.user_id == user_id):
                        role = self._roles.get(ace.role)
                        if role and role.has_permission(action):
                            return True

        # 4. 检查资源可见性
        if resource:
            if resource.visibility == 'public':
                return action == Permission.READ.value

        return False

    def get_user_role(self, user_id: str, resource_type: str,
                      resource_id: str) -> Optional[str]:
        """获取用户在资源上的角色"""
        for ace in self._acl:
            if (ace.user_id == user_id and
                ace.resource_type == resource_type and
                ace.resource_id == resource_id):
                return ace.role
        return None

    def get_accessible_resources(self, user_id: str, resource_type: str = None,
                                  action: str = None) -> List[Resource]:
        """获取用户可访问的资源列表

        Args:
            user_id: 用户 ID
            resource_type: 资源类型（可选）
            action: 操作类型（可选，默认读取）

        Returns:
            可访问的资源列表
        """
        resources = []

        for key, resource in self._resources.items():
            if resource_type and resource.type != resource_type:
                continue

            if self.check_permission(user_id, resource.type, resource.id, action or 'read'):
                resources.append(resource)

        return resources

    def register_resource(self, resource_type: str, resource_id: str,
                          owner_id: str = "", team_id: str = "",
                          visibility: str = "team") -> Resource:
        """注册资源

        Args:
            resource_type: 资源类型
            resource_id: 资源 ID
            owner_id: 所有者 ID
            team_id: 所属团队 ID
            visibility: 可见性

        Returns:
            创建的资源
        """
        resource = Resource(
            type=resource_type,
            id=resource_id,
            owner_id=owner_id,
            team_id=team_id,
            visibility=visibility,
            created_at=datetime.now().isoformat()
        )
        self._resources[f"{resource_type}:{resource_id}"] = resource

        if self.db_path:
            self._save_resources()

        return resource

    def unregister_resource(self, resource_type: str, resource_id: str) -> bool:
        """注销资源"""
        key = f"{resource_type}:{resource_id}"
        if key in self._resources:
            del self._resources[key]
            # 清理相关 ACL
            self._acl = [ace for ace in self._acl
                         if not (ace.resource_type == resource_type and
                                 ace.resource_id == resource_id)]
            return True
        return False

    def get_resource(self, resource_type: str, resource_id: str) -> Optional[Resource]:
        """获取资源"""
        return self._resources.get(f"{resource_type}:{resource_id}")

    def set_resource_visibility(self, resource_type: str, resource_id: str,
                                 visibility: str) -> bool:
        """设置资源可见性"""
        resource = self._resources.get(f"{resource_type}:{resource_id}")
        if resource:
            resource.visibility = visibility
            if self.db_path:
                self._save_resources()
            return True
        return False

    def _load_acl(self):
        """加载 ACL"""
        if not self.db_path:
            return

        acl_file = self.db_path.parent / 'acl.json'
        if acl_file.exists():
            try:
                with open(acl_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._acl = [AccessControlEntry(**ace) for ace in data.get('acl', [])]
                self._resources = {
                    k: Resource(**v) for k, v in data.get('resources', {}).items()
                }
            except Exception:
                pass

    def _save_acl(self):
        """保存 ACL"""
        if not self.db_path:
            return

        acl_file = self.db_path.parent / 'acl.json'
        acl_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'acl': [ace.to_dict() for ace in self._acl],
            'resources': {k: v.to_dict() for k, v in self._resources.items()},
        }

        with open(acl_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_resources(self):
        """保存资源"""
        self._save_acl()

    def get_permission_matrix(self) -> Dict[str, List[str]]:
        """获取权限矩阵"""
        return {
            role_name: list(role.permissions)
            for role_name, role in self._roles.items()
        }

    def export_acl(self) -> Dict[str, Any]:
        """导出 ACL 配置"""
        return {
            'roles': {name: {'permissions': list(r.permissions), 'description': r.description}
                      for name, r in self._roles.items()},
            'acl': [ace.to_dict() for ace in self._acl],
            'resources': {k: v.to_dict() for k, v in self._resources.items()},
        }

    def import_acl(self, data: Dict[str, Any]):
        """导入 ACL 配置"""
        # 导入角色
        for name, role_data in data.get('roles', {}).items():
            self._roles[name] = Role(
                name=name,
                permissions=set(role_data.get('permissions', [])),
                description=role_data.get('description', '')
            )

        # 导入 ACL
        for ace_data in data.get('acl', []):
            self._acl.append(AccessControlEntry(**ace_data))

        # 导入资源
        for key, res_data in data.get('resources', {}).items():
            self._resources[key] = Resource(**res_data)


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: permission_manager.py <command> [args]")
        print("\nCommands:")
        print("  roles                          List all roles")
        print("  check <user> <type> <id> <action>  Check permission")
        print("  grant <user> <type> <id> <role>    Grant role")
        print("  export                         Export ACL config")
        sys.exit(1)

    pm = PermissionManager()
    command = sys.argv[1]

    if command == 'roles':
        for role in pm.list_roles():
            print(f"- {role.name}: {', '.join(role.permissions)}")

    elif command == 'check':
        if len(sys.argv) < 6:
            print("Usage: permission_manager.py check <user> <type> <id> <action>")
            sys.exit(1)
        user_id = sys.argv[2]
        resource_type = sys.argv[3]
        resource_id = sys.argv[4]
        action = sys.argv[5]

        result = pm.check_permission(user_id, resource_type, resource_id, action)
        print(f"Permission: {'granted' if result else 'denied'}")

    elif command == 'grant':
        if len(sys.argv) < 6:
            print("Usage: permission_manager.py grant <user> <type> <id> <role>")
            sys.exit(1)
        user_id = sys.argv[2]
        resource_type = sys.argv[3]
        resource_id = sys.argv[4]
        role = sys.argv[5]

        success = pm.grant_role(user_id, resource_type, resource_id, role, "system")
        print(f"Grant: {'success' if success else 'failed'}")

    elif command == 'export':
        config = pm.export_acl()
        print(json.dumps(config, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()