from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp
import re

class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('密码', validators=[DataRequired()])
    remember = BooleanField('记住我')

class FirmwareUploadForm(FlaskForm):
    """固件上传表单"""
    version = StringField('版本号', validators=[
        DataRequired(),
        Regexp(r'^\d{3}\.\d{3}\.\d{3}$', message='版本号格式必须为xxx.yyy.zzz')
    ])
    firmware_file = FileField('固件文件', validators=[
        FileRequired(),
        FileAllowed(['bin'], '只允许上传.bin文件')
    ])
    description = TextAreaField('版本描述')

class DeviceForm(FlaskForm):
    """设备表单"""
    imei = StringField('IMEI', validators=[
        DataRequired(),
        Regexp(r'^\d{15}$', message='IMEI必须为15位数字')
    ])
    name = StringField('设备名称')
    current_version = StringField('当前版本', validators=[
        Regexp(r'^\d{3}\.\d{3}\.\d{3}$', message='版本号格式必须为xxx.yyy.zzz', flags=re.IGNORECASE)
    ])
    is_authorized = BooleanField('授权设备', default=True)

class UpdateRuleForm(FlaskForm):
    """更新规则表单"""
    from_version = StringField('起始版本', validators=[
        DataRequired(),
        Regexp(r'^\d{3}\.\d{3}\.\d{3}$', message='版本号格式必须为xxx.yyy.zzz')
    ])
    to_version = StringField('目标版本', validators=[
        DataRequired(),
        Regexp(r'^\d{3}\.\d{3}\.\d{3}$', message='版本号格式必须为xxx.yyy.zzz')
    ])
    is_active = BooleanField('启用规则', default=True)

class ImportDevicesForm(FlaskForm):
    """设备批量导入表单"""
    import_file = FileField('CSV文件', validators=[
        FileRequired(),
        FileAllowed(['csv'], '只允许上传.csv文件')
    ])
    skip_header = BooleanField('跳过第一行', default=True)
