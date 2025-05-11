from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp, Optional
from flask_babel import lazy_gettext as _l
import re
from models import User, Project

class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField(_l('用户名'), validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField(_l('密码'), validators=[DataRequired()])
    remember = BooleanField(_l('记住我'))
    submit = SubmitField(_l('登录'))


class RegistrationForm(FlaskForm):
    """注册表单"""
    username = StringField(_l('用户名'), validators=[
        DataRequired(),
        Length(min=3, max=20)
    ])
    email = StringField(_l('电子邮箱'), validators=[
        DataRequired(),
        Email(message=_l('请输入有效的电子邮箱地址'))
    ])
    password = PasswordField(_l('密码'), validators=[
        DataRequired(),
        Length(min=6, message=_l('密码长度至少为6个字符'))
    ])
    password2 = PasswordField(_l('确认密码'), validators=[
        DataRequired(),
        EqualTo('password', message=_l('两次输入的密码不匹配'))
    ])
    name = StringField(_l('姓名'), validators=[Optional(), Length(max=64)])
    use_ai_avatar = BooleanField(_l('使用AI生成动漫头像'), default=True)
    submit = SubmitField(_l('注册'))

    def validate_username(self, field):
        """验证用户名是否已存在"""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError(_l('该用户名已被使用'))

    def validate_email(self, field):
        """验证邮箱是否已存在"""
        if User.query.filter_by(email=field.data).first():
            raise ValidationError(_l('该邮箱已被注册'))


class UserProfileForm(FlaskForm):
    """用户资料表单"""
    name = StringField(_l('姓名'), validators=[Optional(), Length(max=64)])
    email = StringField(_l('电子邮箱'), validators=[
        DataRequired(),
        Email(message=_l('请输入有效的电子邮箱地址'))
    ])
    avatar = FileField(_l('头像'), validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg'], _l('只允许上传jpg、png或jpeg格式的图片'))
    ])
    generate_anime_avatar = BooleanField(_l('生成新的动漫头像'), default=False)
    current_password = PasswordField(_l('当前密码'))
    new_password = PasswordField(_l('新密码'), validators=[
        Optional(),
        Length(min=6, message=_l('密码长度至少为6个字符'))
    ])
    confirm_password = PasswordField(_l('确认新密码'), validators=[
        Optional(),
        EqualTo('new_password', message=_l('两次输入的密码不匹配'))
    ])
    submit = SubmitField(_l('保存修改'))

class FirmwareUploadForm(FlaskForm):
    """固件上传表单"""
    version = StringField(_l('版本号'), validators=[
        DataRequired(),
        Regexp(r'^\d{3}\.\d{3}\.\d{3}$', message=_l('版本号格式必须为xxx.yyy.zzz'))
    ])
    firmware_file = FileField(_l('固件文件'), validators=[
        FileRequired(),
        FileAllowed(['bin'], _l('只允许上传.bin文件'))
    ])
    description = TextAreaField(_l('版本描述'))
    project_id = SelectField(_l('所属项目'), coerce=int, validators=[DataRequired()])
    submit = SubmitField(_l('上传'))

class DeviceForm(FlaskForm):
    """设备表单"""
    imei = StringField(_l('IMEI'), validators=[
        DataRequired(),
        Regexp(r'^\d{15}$', message=_l('IMEI必须为15位数字'))
    ])
    name = StringField(_l('设备名称'))
    current_version = StringField(_l('当前版本'), validators=[
        Regexp(r'^\d{3}\.\d{3}\.\d{3}$', message=_l('版本号格式必须为xxx.yyy.zzz'), flags=re.IGNORECASE)
    ])
    is_authorized = BooleanField(_l('授权设备'), default=True)
    project_id = SelectField(_l('所属项目'), coerce=int, validators=[DataRequired()])
    submit = SubmitField(_l('保存'))

class UpdateRuleForm(FlaskForm):
    """更新规则表单"""
    from_version = StringField(_l('起始版本'), validators=[
        DataRequired(),
        Regexp(r'^\d{3}\.\d{3}\.\d{3}$', message=_l('版本号格式必须为xxx.yyy.zzz'))
    ])
    to_version = StringField(_l('目标版本'), validators=[
        DataRequired(),
        Regexp(r'^\d{3}\.\d{3}\.\d{3}$', message=_l('版本号格式必须为xxx.yyy.zzz'))
    ])
    firmware_id = SelectField(_l('固件'), coerce=int, validators=[DataRequired()])
    project_id = SelectField(_l('所属项目'), coerce=int, validators=[DataRequired()])
    is_active = BooleanField(_l('启用规则'), default=True)
    submit = SubmitField(_l('保存'))

class ImportDevicesForm(FlaskForm):
    """设备批量导入表单"""
    import_file = FileField(_l('CSV文件'), validators=[
        FileRequired(),
        FileAllowed(['csv'], _l('只允许上传.csv文件'))
    ])
    skip_header = BooleanField(_l('跳过第一行'), default=True)
    project_id = SelectField(_l('所属项目'), coerce=int, validators=[DataRequired()])
    submit = SubmitField(_l('导入'))


class ProjectForm(FlaskForm):
    """项目表单"""
    name = StringField(_l('项目名称'), validators=[
        DataRequired(),
        Length(min=2, max=100)
    ])
    description = TextAreaField(_l('项目描述'))
    project_key = StringField(_l('项目密钥'), validators=[Length(min=16, max=64)])
    submit = SubmitField(_l('保存'))

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        # 如果是新建项目，自动生成项目密钥
        if not self.project_key.data:
            self.project_key.data = Project.generate_project_key()


class UserProjectForm(FlaskForm):
    """用户项目关联表单"""
    user_id = SelectField(_l('用户'), coerce=int, validators=[DataRequired()])
    project_id = HiddenField(_l('项目ID'), validators=[DataRequired()])
    submit = SubmitField(_l('添加用户到项目'))


class LanguageForm(FlaskForm):
    """语言选择表单"""
    language = SelectField(_l('语言'), choices=[
        ('zh', _l('中文')),
        ('en', _l('英文')),
        ('ja', _l('日文'))
    ])
    submit = SubmitField(_l('切换'))
