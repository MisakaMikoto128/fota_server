from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from flask_babel import gettext as _
from datetime import datetime, timedelta

from models import db, Device, Firmware, UpdateLog, Project, Role, User

# 创建蓝图
pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def index():
    """首页"""
    return render_template('index.html')


@pages_bp.route('/dashboard')
@login_required
def dashboard():
    """仪表盘页面"""
    # 获取用户可访问的项目
    if current_user.is_administrator():
        projects = Project.query.all()
    else:
        projects = current_user.projects.all()

    project_ids = [p.id for p in projects]

    # 统计数据
    stats = {
        'project_count': len(projects),
        'device_count': Device.query.filter(Device.project_id.in_(project_ids) if project_ids else False).count(),
        'firmware_count': Firmware.query.filter(Firmware.project_id.in_(project_ids) if project_ids else False).count(),
        'today_updates': UpdateLog.query.filter(
            UpdateLog.update_time >= datetime.now().replace(hour=0, minute=0, second=0),
            UpdateLog.project_id.in_(project_ids) if project_ids else False
        ).count(),
        'pending_updates': UpdateLog.query.filter(
            UpdateLog.status == 'pending',
            UpdateLog.project_id.in_(project_ids) if project_ids else False
        ).count()
    }

    # 最近更新记录
    recent_updates = UpdateLog.query.filter(
        UpdateLog.project_id.in_(project_ids) if project_ids else False
    ).order_by(UpdateLog.update_time.desc()).limit(5).all()

    # 版本分布
    version_distribution = {}
    for device in Device.query.filter(Device.project_id.in_(project_ids) if project_ids else False).all():
        if device.current_version:
            if device.current_version in version_distribution:
                version_distribution[device.current_version] += 1
            else:
                version_distribution[device.current_version] = 1

    # 项目活动
    project_activities = []
    for project in projects:
        # 获取项目的设备数量
        device_count = Device.query.filter_by(project_id=project.id).count()

        # 获取项目的固件数量
        firmware_count = Firmware.query.filter_by(project_id=project.id).count()

        # 获取项目的更新规则数量
        rule_count = project.update_rules.count()

        # 获取项目的最近更新
        last_update = UpdateLog.query.filter_by(project_id=project.id).order_by(UpdateLog.update_time.desc()).first()

        project_activities.append({
            'project': project,
            'device_count': device_count,
            'firmware_count': firmware_count,
            'rule_count': rule_count,
            'last_update': last_update
        })

    return render_template('dashboard.html',
                          stats=stats,
                          recent_updates=recent_updates,
                          version_distribution=version_distribution,
                          project_activities=project_activities)


@pages_bp.route('/users')
@login_required
def user_list():
    """用户列表（仅管理员可见）"""
    if not current_user.is_administrator():
        abort(403)

    users = User.query.all()
    roles = Role.query.all()

    return render_template('users/user_list.html', users=users, roles=roles)


@pages_bp.route('/users/set_role/<int:user_id>/<int:role_id>')
@login_required
def set_user_role(user_id, role_id):
    """设置用户角色（仅管理员可见）"""
    if not current_user.is_administrator():
        abort(403)

    user = User.query.get_or_404(user_id)
    role = Role.query.get_or_404(role_id)

    # 不能修改自己的角色
    if user.id == current_user.id:
        flash(_('不能修改自己的角色'), 'danger')
        return redirect(url_for('pages.user_list'))

    user.role_id = role.id
    db.session.commit()

    flash(_('用户 {} 的角色已更新为 {}').format(user.username, role.name), 'success')
    return redirect(url_for('pages.user_list'))


@pages_bp.route('/users/delete/<int:user_id>')
@login_required
def delete_user(user_id):
    """删除用户（仅管理员可见）"""
    if not current_user.is_administrator():
        abort(403)

    user = User.query.get_or_404(user_id)

    # 不能删除自己
    if user.id == current_user.id:
        flash(_('不能删除自己'), 'danger')
        return redirect(url_for('pages.user_list'))

    db.session.delete(user)
    db.session.commit()

    flash(_('用户 {} 已删除').format(user.username), 'success')
    return redirect(url_for('pages.user_list'))
