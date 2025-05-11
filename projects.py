from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from flask_babel import gettext as _
from datetime import datetime

from models import db, Project, User, Role
from forms import ProjectForm, UserProjectForm

# 创建蓝图
projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/projects')
@login_required
def project_list():
    """项目列表"""
    # 管理员可以看到所有项目，普通用户只能看到自己的项目
    if current_user.is_administrator():
        projects = Project.query.order_by(Project.created_at.desc()).all()
    else:
        projects = current_user.projects.order_by(Project.created_at.desc()).all()
    
    form = ProjectForm()
    return render_template('projects/project_list.html', projects=projects, form=form)


@projects_bp.route('/projects/add', methods=['POST'])
@login_required
def add_project():
    """添加项目"""
    form = ProjectForm()
    if form.validate_on_submit():
        # 创建项目
        project = Project(
            name=form.name.data,
            description=form.description.data,
            project_key=form.project_key.data,
            created_by_id=current_user.id
        )
        db.session.add(project)
        
        # 将当前用户添加到项目中
        project.users.append(current_user)
        
        db.session.commit()
        flash(_('项目创建成功'), 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('projects.project_list'))


@projects_bp.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    """项目详情"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限
    if not current_user.is_administrator() and project not in current_user.projects:
        abort(403)
    
    # 获取项目成员
    project_users = project.users.all()
    
    # 获取可添加的用户（不在项目中的用户）
    available_users = User.query.filter(~User.projects.contains(project)).all()
    
    # 用户-项目关联表单
    user_project_form = UserProjectForm()
    user_project_form.user_id.choices = [(u.id, u.username) for u in available_users]
    user_project_form.project_id.data = project.id
    
    # 项目编辑表单
    edit_form = ProjectForm()
    if request.method == 'GET':
        edit_form.name.data = project.name
        edit_form.description.data = project.description
        edit_form.project_key.data = project.project_key
    
    return render_template('projects/project_detail.html', 
                          project=project, 
                          project_users=project_users,
                          user_project_form=user_project_form,
                          edit_form=edit_form)


@projects_bp.route('/projects/edit/<int:project_id>', methods=['POST'])
@login_required
def edit_project(project_id):
    """编辑项目"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限
    if not current_user.is_administrator() and project not in current_user.projects:
        abort(403)
    
    form = ProjectForm()
    if form.validate_on_submit():
        project.name = form.name.data
        project.description = form.description.data
        project.project_key = form.project_key.data
        db.session.commit()
        flash(_('项目更新成功'), 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('projects.project_detail', project_id=project.id))


@projects_bp.route('/projects/delete/<int:project_id>')
@login_required
def delete_project(project_id):
    """删除项目"""
    project = Project.query.get_or_404(project_id)
    
    # 检查权限（只有管理员或项目创建者可以删除项目）
    if not current_user.is_administrator() and project.created_by_id != current_user.id:
        abort(403)
    
    db.session.delete(project)
    db.session.commit()
    flash(_('项目已删除'), 'success')
    return redirect(url_for('projects.project_list'))


@projects_bp.route('/projects/add_user', methods=['POST'])
@login_required
def add_user_to_project():
    """添加用户到项目"""
    form = UserProjectForm()
    if form.validate_on_submit():
        project_id = form.project_id.data
        user_id = form.user_id.data
        
        project = Project.query.get_or_404(project_id)
        user = User.query.get_or_404(user_id)
        
        # 检查权限
        if not current_user.is_administrator() and project not in current_user.projects:
            abort(403)
        
        # 添加用户到项目
        if user not in project.users:
            project.users.append(user)
            db.session.commit()
            flash(_('用户已添加到项目'), 'success')
        else:
            flash(_('用户已在项目中'), 'warning')
    
    return redirect(url_for('projects.project_detail', project_id=form.project_id.data))


@projects_bp.route('/projects/remove_user/<int:project_id>/<int:user_id>')
@login_required
def remove_user_from_project(project_id, user_id):
    """从项目中移除用户"""
    project = Project.query.get_or_404(project_id)
    user = User.query.get_or_404(user_id)
    
    # 检查权限
    if not current_user.is_administrator() and project not in current_user.projects:
        abort(403)
    
    # 不能移除项目创建者
    if project.created_by_id == user.id:
        flash(_('不能移除项目创建者'), 'danger')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    # 移除用户
    if user in project.users:
        project.users.remove(user)
        db.session.commit()
        flash(_('用户已从项目中移除'), 'success')
    
    return redirect(url_for('projects.project_detail', project_id=project_id))
