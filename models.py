from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import os
from flask_login import UserMixin

db = SQLAlchemy()

class Role(db.Model):
    """用户角色模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)  # 是否为默认角色
    permissions = db.Column(db.Integer, default=0)  # 权限位字段

    # 角色与用户的一对多关系
    users = db.relationship('User', backref='role', lazy='dynamic')

    # 权限常量
    PERMISSION_VIEW = 1      # 查看权限
    PERMISSION_EDIT = 2      # 编辑权限
    PERMISSION_ADMIN = 4     # 管理员权限

    @staticmethod
    def insert_roles():
        """初始化角色"""
        roles = {
            'User': [Role.PERMISSION_VIEW],
            'Operator': [Role.PERMISSION_VIEW, Role.PERMISSION_EDIT],
            'Administrator': [Role.PERMISSION_VIEW, Role.PERMISSION_EDIT, Role.PERMISSION_ADMIN]
        }
        default_role = 'User'

        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()

            # 添加角色权限
            for perm in roles[r]:
                role.add_permission(perm)

            # 设置默认角色
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        """添加权限"""
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        """移除权限"""
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        """重置权限"""
        self.permissions = 0

    def has_permission(self, perm):
        """检查是否有指定权限"""
        return self.permissions & perm == perm

    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(64))  # 真实姓名
    avatar = db.Column(db.String(255), default='default.jpg')  # 头像
    is_admin = db.Column(db.Boolean, default=False)  # 保留兼容性
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 用户与项目的多对多关系
    projects = db.relationship('Project', secondary='user_project',
                              backref=db.backref('users', lazy='dynamic'),
                              lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        # 如果没有指定角色，则使用默认角色
        if self.role is None:
            if self.email == 'admin@example.com' or self.username == 'admin':
                # 管理员用户
                self.role = Role.query.filter_by(name='Administrator').first()
            else:
                # 普通用户
                self.role = Role.query.filter_by(default=True).first()

    def set_password(self, password):
        """设置密码"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def can(self, perm):
        """检查用户是否有指定权限"""
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        """检查用户是否为管理员"""
        return self.can(Role.PERMISSION_ADMIN)

    def __repr__(self):
        return f'<User {self.username}>'

# 用户-项目关联表
user_project = db.Table('user_project',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True)
)


class Project(db.Model):
    """项目模型，用于管理不同的固件项目"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    project_key = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    # 项目与固件的一对多关系
    firmwares = db.relationship('Firmware', backref='project', lazy='dynamic')

    # 项目与设备的一对多关系
    devices = db.relationship('Device', backref='project', lazy='dynamic')

    # 项目与更新规则的一对多关系
    update_rules = db.relationship('UpdateRule', backref='project', lazy='dynamic')

    @staticmethod
    def generate_project_key():
        """生成项目密钥

        生成一个更短且区分大小写的项目密钥
        """
        # 使用 token_urlsafe 生成包含大小写字母和数字的密钥
        # 长度设为 12 个字符，比原来的 32 个字符短很多
        return secrets.token_urlsafe(9)  # 生成约 12 个字符的密钥

    def __repr__(self):
        return f'<Project {self.name}>'


class Device(db.Model):
    """设备模型，记录连接到系统的设备信息"""
    id = db.Column(db.Integer, primary_key=True)
    imei = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    current_version = db.Column(db.String(20))
    last_check_time = db.Column(db.DateTime)
    last_update_time = db.Column(db.DateTime)
    is_authorized = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 设备所属项目
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

    def __repr__(self):
        return f'<Device {self.imei}>'

class Firmware(db.Model):
    """固件模型，记录可用的固件版本"""
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    filesize = db.Column(db.Integer)  # 文件大小（字节）
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 固件所属项目
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

    # 上传者
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])

    # 版本号在项目内唯一
    __table_args__ = (
        db.UniqueConstraint('version', 'project_id', name='uix_firmware_version_project'),
    )

    def __repr__(self):
        return f'<Firmware {self.version}>'

class UpdateRule(db.Model):
    """更新规则，定义从哪个版本可以更新到哪个版本"""
    id = db.Column(db.Integer, primary_key=True)
    from_version = db.Column(db.String(20), nullable=False)
    to_version = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 规则所属项目
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

    # 外键关联
    firmware_id = db.Column(db.Integer, db.ForeignKey('firmware.id'))
    firmware = db.relationship('Firmware', backref=db.backref('update_rules', lazy=True))

    # 创建者
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    # 规则在项目内唯一
    __table_args__ = (
        db.UniqueConstraint('from_version', 'to_version', 'project_id', name='uix_rule_versions_project'),
    )

    def __repr__(self):
        return f'<UpdateRule {self.from_version} -> {self.to_version}>'


class UpdateLog(db.Model):
    """更新日志，记录设备的更新历史"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    device = db.relationship('Device', backref=db.backref('update_logs', lazy=True))

    # 日志所属项目
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship('Project', backref=db.backref('update_logs', lazy=True))

    from_version = db.Column(db.String(20))
    to_version = db.Column(db.String(20))
    update_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))  # 'success', 'failed', 'pending'

    # 固件ID
    firmware_id = db.Column(db.Integer, db.ForeignKey('firmware.id'))
    firmware = db.relationship('Firmware', backref=db.backref('update_logs', lazy=True))

    def __repr__(self):
        return f'<UpdateLog {self.device.imei if self.device else "Unknown"} {self.from_version} -> {self.to_version}>'
