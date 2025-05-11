from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from flask_babel import gettext as _
from datetime import datetime, timedelta, timezone
import os
import subprocess
import logging
import tempfile
import shutil

from models import db, Device, Firmware, UpdateLog, Project, Role, User, RepoConfig
from forms import RepoConfigForm

# 创建蓝图
pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/')
def index():
    """首页"""
    return render_template('index.html')


@pages_bp.route('/about')
def about():
    """关于页面"""
    return render_template('about.html')


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


@pages_bp.route('/admin/update_system')
@login_required
def update_system_page():
    """系统更新页面（仅管理员可见）"""
    if not current_user.is_administrator():
        abort(403)

    # 获取仓库配置
    repo_config = RepoConfig.get_config()

    return render_template('admin/update_system.html', repo_config=repo_config)


@pages_bp.route('/admin/save_repo_config', methods=['POST'])
@login_required
def save_repo_config():
    """保存仓库配置（仅管理员可见）"""
    if not current_user.is_administrator():
        abort(403)

    # 获取仓库配置
    repo_config = RepoConfig.get_config()

    # 更新配置
    repo_config.repo_type = request.form.get('repo_type', 'github')
    repo_config.repo_url = request.form.get('repo_url', '')
    repo_config.repo_branch = request.form.get('repo_branch', 'main')

    db.session.commit()

    flash(_('仓库配置已保存'), 'success')
    return redirect(url_for('pages.update_system_page'))


@pages_bp.route('/admin/check_update', methods=['POST'])
@login_required
def check_update():
    """检查系统更新（仅管理员可见）"""
    if not current_user.is_administrator():
        return jsonify({'status': 'error', 'message': _('权限不足')}), 403

    # 获取仓库配置
    repo_config = RepoConfig.get_config()

    if not repo_config.repo_url:
        return jsonify({
            'status': 'error',
            'message': _('未配置仓库URL'),
            'log': _('请先配置仓库URL')
        })

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    log_output = []

    try:
        # 检查是否已经克隆过仓库
        current_dir = os.getcwd()
        git_dir = os.path.join(current_dir, '.git')

        if os.path.exists(git_dir):
            # 已有Git仓库，执行Git操作
            def run_git_cmd(cmd, error_msg=None, default_value=None):
                """执行Git命令并处理可能的错误"""
                try:
                    result = subprocess.check_output(
                        cmd, stderr=subprocess.STDOUT, universal_newlines=True, shell=True
                    ).strip()
                    return result
                except subprocess.CalledProcessError:
                    if error_msg:
                        log_output.append(error_msg)
                    return default_value

            # 获取仓库信息
            current_commit = run_git_cmd(['git', 'rev-parse', 'HEAD'],
                                        "无法获取当前提交，可能不是有效的Git仓库", "未知")
            log_output.append(f"当前提交: {current_commit}")

            remote_url = run_git_cmd(['git', 'config', '--get', 'remote.origin.url'],
                                    "无法获取远程仓库URL", "未知")
            log_output.append(f"远程仓库: {remote_url}")

            current_branch = run_git_cmd(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                        "无法获取当前分支", "未知")
            log_output.append(f"当前分支: {current_branch}")

            # 获取远程更新
            fetch_output = run_git_cmd(['git', 'fetch', 'origin', repo_config.repo_branch],
                                      "获取远程更新失败", "获取远程更新失败")
            log_output.append(fetch_output)

            # 检查是否有更新
            diff_output = run_git_cmd(['git', 'diff', f'HEAD..origin/{repo_config.repo_branch}', '--name-only'],
                                     "检查更新失败")
            if diff_output is None:
                return jsonify({
                    'status': 'error',
                    'message': _('检查更新失败'),
                    'log': '\n'.join(log_output)
                })

            if diff_output.strip():
                # 有更新
                log_output.append(_("发现以下文件有更新:"))
                log_output.append(diff_output)

                # 获取最新提交信息
                latest_commit = run_git_cmd(
                    ['git', 'rev-parse', f'origin/{repo_config.repo_branch}'],
                    "获取最新提交信息失败", "未知"
                )

                # 获取提交日志
                log_message = run_git_cmd(
                    ['git', 'log', '--oneline', f'HEAD..origin/{repo_config.repo_branch}'],
                    "获取提交日志失败", "无法获取提交日志"
                )
                log_output.append(_("提交历史:"))
                log_output.append(log_message)

                # 更新配置
                repo_config.last_check_time = datetime.now(timezone.utc)
                repo_config.last_commit = latest_commit
                db.session.commit()

                return jsonify({
                    'status': 'needupdate',
                    'message': _('发现新版本'),
                    'latest_commit': latest_commit[:7],
                    'log': '\n'.join(log_output)
                })
            else:
                # 没有更新
                log_output.append(_("系统已是最新版本"))

                # 更新检查时间
                repo_config.last_check_time = datetime.now(timezone.utc)
                db.session.commit()

                return jsonify({
                    'status': 'uptodate',
                    'message': _('系统已是最新版本'),
                    'log': '\n'.join(log_output)
                })
        else:
            # 没有Git仓库，需要克隆
            log_output.append(_("未检测到Git仓库，需要克隆"))

            # 克隆仓库到临时目录
            clone_output = subprocess.check_output(
                ['git', 'clone', '-b', repo_config.repo_branch, repo_config.repo_url, temp_dir],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            log_output.append(clone_output)

            # 获取最新提交信息
            os.chdir(temp_dir)
            latest_commit = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            ).strip()

            # 更新配置
            repo_config.last_check_time = datetime.now(timezone.utc)
            repo_config.last_commit = latest_commit
            db.session.commit()

            return jsonify({
                'status': 'needupdate',
                'message': _('需要初始化仓库'),
                'latest_commit': latest_commit[:7],
                'log': '\n'.join(log_output)
            })

    except subprocess.CalledProcessError as e:
        log_output.append(f"错误: {e.output}")
        return jsonify({
            'status': 'error',
            'message': _('检查更新失败'),
            'log': '\n'.join(log_output)
        })

    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@pages_bp.route('/admin/update_system', methods=['POST'])
@login_required
def update_system():
    """更新系统（仅管理员可见）"""
    if not current_user.is_administrator():
        return jsonify({'status': 'error', 'message': _('权限不足')}), 403

    # 获取仓库配置
    repo_config = RepoConfig.get_config()

    if not repo_config.repo_url:
        return jsonify({
            'status': 'error',
            'message': _('未配置仓库URL'),
            'log': _('请先配置仓库URL')
        })

    log_output = []

    try:
        # 检查是否已经克隆过仓库
        # 使用当前工作目录作为项目根目录
        current_dir = os.getcwd()
        git_dir = os.path.join(current_dir, '.git')

        if os.path.exists(git_dir):
            # 已有Git仓库，拉取更新
            log_output.append(_("正在拉取更新..."))

            # 定义辅助函数执行Git命令
            def run_git_cmd(cmd, error_msg=None, default_value=None):
                """执行Git命令并处理可能的错误"""
                try:
                    result = subprocess.check_output(
                        cmd, stderr=subprocess.STDOUT, universal_newlines=True, shell=True
                    ).strip()
                    return result
                except subprocess.CalledProcessError:
                    if error_msg:
                        log_output.append(error_msg)
                    return default_value

            # 拉取更新
            pull_output = run_git_cmd(
                ['git', 'pull', 'origin', repo_config.repo_branch],
                "拉取更新失败"
            )

            if pull_output is None:
                return jsonify({
                    'status': 'error',
                    'message': _('拉取更新失败'),
                    'log': '\n'.join(log_output)
                })

            log_output.append(pull_output)

            # 获取最新提交信息
            latest_commit = run_git_cmd(
                ['git', 'rev-parse', 'HEAD'],
                "获取最新提交信息失败",
                "未知"
            )

            # 更新配置
            repo_config.last_update_time = datetime.now(timezone.utc)
            repo_config.last_commit = latest_commit
            db.session.commit()

            # 重启服务器（这里只返回成功，实际重启需要在前端处理）
            log_output.append(_("更新完成，准备重启服务器..."))

            return jsonify({
                'status': 'success',
                'message': _('系统已更新，即将重启'),
                'log': '\n'.join(log_output)
            })
        else:
            # 没有Git仓库，需要初始化
            log_output.append(_("未检测到Git仓库，需要初始化"))

            # 创建临时目录
            temp_dir = tempfile.mkdtemp()

            try:
                # 克隆仓库到临时目录
                clone_output = subprocess.check_output(
                    ['git', 'clone', '-b', repo_config.repo_branch, repo_config.repo_url, temp_dir],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                log_output.append(clone_output)

                # 复制文件到当前目录
                for item in os.listdir(temp_dir):
                    if item != '.git':  # 不复制.git目录
                        s = os.path.join(temp_dir, item)
                        d = os.path.join(current_dir, item)
                        if os.path.isdir(s):
                            if os.path.exists(d):
                                shutil.rmtree(d)
                            shutil.copytree(s, d)
                        else:
                            shutil.copy2(s, d)

                # 初始化Git仓库
                os.chdir(current_dir)
                init_output = subprocess.check_output(
                    ['git', 'init'],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                log_output.append(init_output)

                # 添加远程仓库
                remote_output = subprocess.check_output(
                    ['git', 'remote', 'add', 'origin', repo_config.repo_url],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                log_output.append(remote_output)

                # 获取最新提交信息
                latest_commit = subprocess.check_output(
                    ['git', 'rev-parse', 'HEAD'],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )

                # 更新配置
                repo_config.last_update_time = datetime.now(timezone.utc)
                repo_config.last_commit = latest_commit.strip()
                db.session.commit()

                # 重启服务器（这里只返回成功，实际重启需要在前端处理）
                log_output.append(_("初始化完成，准备重启服务器..."))

                return jsonify({
                    'status': 'success',
                    'message': _('系统已初始化，即将重启'),
                    'log': '\n'.join(log_output)
                })

            finally:
                # 清理临时目录
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

    except subprocess.CalledProcessError as e:
        log_output.append(f"错误: {e.output}")
        return jsonify({
            'status': 'error',
            'message': _('更新系统失败'),
            'log': '\n'.join(log_output)
        })
