from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """用户模型，用于管理员登录"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login接口
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<User {self.username}>'

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

    def __repr__(self):
        return f'<Device {self.imei}>'

class Firmware(db.Model):
    """固件模型，记录可用的固件版本"""
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    filesize = db.Column(db.Integer)  # 文件大小（字节）
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Firmware {self.version}>'

class UpdateRule(db.Model):
    """更新规则，定义从哪个版本可以更新到哪个版本"""
    id = db.Column(db.Integer, primary_key=True)
    from_version = db.Column(db.String(20), nullable=False)
    to_version = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 外键关联
    firmware_id = db.Column(db.Integer, db.ForeignKey('firmware.id'))
    firmware = db.relationship('Firmware', backref=db.backref('update_rules', lazy=True))

    def __repr__(self):
        return f'<UpdateRule {self.from_version} -> {self.to_version}>'

class UpdateLog(db.Model):
    """更新日志，记录设备的更新历史"""
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    device = db.relationship('Device', backref=db.backref('update_logs', lazy=True))

    from_version = db.Column(db.String(20))
    to_version = db.Column(db.String(20))
    update_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20))  # 'success', 'failed', 'pending'

    def __repr__(self):
        return f'<UpdateLog {self.device.imei} {self.from_version} -> {self.to_version}>'
