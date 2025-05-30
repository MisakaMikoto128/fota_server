from flask import Blueprint, render_template, redirect, url_for, flash, request, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from models import db, User, Role, RepoConfig
from forms import LoginForm, RegistrationForm, UserProfileForm
from avatar_generator import generate_random_avatar

# 创建蓝图
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('pages.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember.data

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            # 更新最后登录时间
            user.last_login = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            flash(_('登录成功！'), 'success')
            return redirect(next_page or url_for('pages.dashboard'))
        else:
            flash(_('登录失败，请检查用户名和密码'), 'danger')

    # 获取注册开关状态
    config = RepoConfig.get_config()
    allow_registration = config.allow_registration

    return render_template('auth/login.html', form=form, allow_registration=allow_registration)


@auth_bp.route('/logout')
@login_required
def logout():
    """用户退出"""
    logout_user()
    flash(_('您已成功退出登录'), 'info')
    return redirect(url_for('pages.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('pages.dashboard'))

    # 检查是否允许用户自行注册
    config = RepoConfig.get_config()
    if not config.allow_registration:
        flash(_('管理员已关闭用户注册功能'), 'warning')
        return redirect(url_for('auth.login'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            name=form.name.data
        )
        user.set_password(form.password.data)

        # 确保角色已初始化
        if not Role.query.first():
            Role.insert_roles()

        # 如果用户选择使用AI生成动漫头像
        if form.use_ai_avatar.data:
            # 确保头像目录存在
            avatar_dir = os.path.join(os.path.dirname(__file__), 'static/avatars')
            if not os.path.exists(avatar_dir):
                os.makedirs(avatar_dir)

            # 生成动漫头像
            avatar_filename = generate_random_avatar(form.username.data, avatar_dir)
            user.avatar = avatar_filename
            flash(_('已为您生成动漫风格头像'), 'info')

        db.session.add(user)
        db.session.commit()

        flash(_('注册成功！现在您可以登录了'), 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """用户资料"""
    form = UserProfileForm()

    if request.method == 'GET':
        form.name.data = current_user.name
        form.email.data = current_user.email

    if form.validate_on_submit():
        # 验证当前密码
        if form.current_password.data and not current_user.check_password(form.current_password.data):
            flash(_('当前密码不正确'), 'danger')
            return render_template('auth/profile.html', form=form)

        # 更新基本信息
        current_user.name = form.name.data
        current_user.email = form.email.data

        # 更新密码（如果提供了新密码）
        if form.new_password.data:
            current_user.set_password(form.new_password.data)

        # 确保头像目录存在
        avatar_dir = os.path.join(os.path.dirname(__file__), 'static/avatars')
        if not os.path.exists(avatar_dir):
            os.makedirs(avatar_dir)

        # 处理头像上传
        if form.avatar.data:
            avatar_file = form.avatar.data
            filename = secure_filename(f"{current_user.username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{avatar_file.filename.rsplit('.', 1)[1].lower()}")
            avatar_path = os.path.join(avatar_dir, filename)
            avatar_file.save(avatar_path)
            # 更新用户头像
            current_user.avatar = filename
            flash(_('头像已更新'), 'success')
        # 生成新的动漫头像
        elif form.generate_anime_avatar.data:
            # 生成动漫头像
            avatar_filename = generate_random_avatar(current_user.username, avatar_dir)
            # 更新用户头像
            current_user.avatar = avatar_filename
            flash(_('已为您生成新的动漫风格头像'), 'success')

        db.session.commit()
        flash(_('个人资料已更新'), 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', form=form)


@auth_bp.route('/language/<lang>')
def set_language(lang):
    """设置语言"""
    # 确保语言代码有效
    from flask import current_app
    if lang in current_app.config['LANGUAGES']:
        session['language'] = lang
        # 添加一个闪现消息，提示用户语言已更改
        if lang == 'zh':
            flash('语言已切换为中文', 'success')
        elif lang == 'en':
            flash('Language switched to English', 'success')
        elif lang == 'ja':
            flash('言語が日本語に切り替わりました', 'success')
    return redirect(request.referrer or url_for('pages.index'))
