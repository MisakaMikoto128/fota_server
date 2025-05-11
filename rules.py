from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from flask_babel import gettext as _
from datetime import datetime

from models import db, UpdateRule, Firmware, Project
from forms import UpdateRuleForm

# 创建蓝图
rules_bp = Blueprint('rules', __name__)

@rules_bp.route('/update_rules')
@login_required
def update_rules():
    """升级规则列表"""
    # 筛选条件
    version_filter = request.args.get('version', '')
    project_id = request.args.get('project_id', type=int)
    
    # 构建查询
    if current_user.is_administrator():
        # 管理员可以查看所有规则
        if project_id:
            # 如果指定了项目，只查看该项目的规则
            query = UpdateRule.query.filter_by(project_id=project_id)
        else:
            query = UpdateRule.query
    else:
        # 普通用户只能查看自己项目的规则
        user_projects = current_user.projects.all()
        project_ids = [p.id for p in user_projects]
        
        if project_id and project_id in project_ids:
            # 如果指定了项目且用户有权限，只查看该项目的规则
            query = UpdateRule.query.filter_by(project_id=project_id)
        else:
            # 否则查看用户所有项目的规则
            query = UpdateRule.query.filter(UpdateRule.project_id.in_(project_ids))
    
    # 应用筛选条件
    if version_filter:
        query = query.filter((UpdateRule.from_version.like(f'%{version_filter}%')) | 
                            (UpdateRule.to_version.like(f'%{version_filter}%')))
    
    # 获取规则列表
    rules = query.all()
    
    # 获取用户可访问的项目列表
    if current_user.is_administrator():
        projects = Project.query.all()
    else:
        projects = current_user.projects.all()
    
    # 表单
    form = UpdateRuleForm()
    form.project_id.choices = [(p.id, p.name) for p in projects]
    
    # 默认选择第一个项目
    if projects and not form.project_id.data:
        form.project_id.data = projects[0].id
        
    # 获取选定项目的固件列表
    selected_project_id = form.project_id.data
    firmwares = Firmware.query.filter_by(project_id=selected_project_id, is_active=True).all()
    form.firmware_id.choices = [(f.id, f.version) for f in firmwares]
    
    return render_template('rules/update_rules.html', 
                          rules=rules, 
                          form=form, 
                          firmwares=firmwares,
                          projects=projects,
                          current_project_id=project_id)


@rules_bp.route('/update_rules/add', methods=['POST'])
@login_required
def add_rule():
    """添加升级规则"""
    form = UpdateRuleForm()
    
    # 获取用户可访问的项目列表
    if current_user.is_administrator():
        projects = Project.query.all()
    else:
        projects = current_user.projects.all()
    
    form.project_id.choices = [(p.id, p.name) for p in projects]
    
    # 获取所有固件
    all_firmwares = Firmware.query.filter_by(is_active=True).all()
    form.firmware_id.choices = [(f.id, f.version) for f in all_firmwares]
    
    if form.validate_on_submit():
        # 检查项目权限
        project_id = form.project_id.data
        project = Project.query.get_or_404(project_id)
        
        if not current_user.is_administrator() and project not in current_user.projects:
            flash(_('您没有权限向此项目添加规则'), 'danger')
            return redirect(url_for('rules.update_rules'))
        
        # 检查固件是否属于该项目
        firmware_id = form.firmware_id.data
        firmware = Firmware.query.get_or_404(firmware_id)
        
        if firmware.project_id != project_id:
            flash(_('所选固件不属于该项目'), 'danger')
            return redirect(url_for('rules.update_rules'))
        
        # 检查规则是否已存在
        existing_rule = UpdateRule.query.filter_by(
            from_version=form.from_version.data,
            to_version=form.to_version.data,
            project_id=project_id
        ).first()
        
        if existing_rule:
            flash(_('从 {} 到 {} 的规则在项目中已存在').format(form.from_version.data, form.to_version.data), 'danger')
            return redirect(url_for('rules.update_rules'))
        
        # 创建规则
        rule = UpdateRule(
            from_version=form.from_version.data,
            to_version=form.to_version.data,
            firmware_id=firmware_id,
            is_active=form.is_active.data,
            project_id=project_id,
            created_by_id=current_user.id
        )
        db.session.add(rule)
        db.session.commit()
        
        flash(_('升级规则添加成功'), 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('rules.update_rules'))


@rules_bp.route('/update_rules/toggle/<int:rule_id>')
@login_required
def toggle_rule(rule_id):
    """启用/禁用升级规则"""
    rule = UpdateRule.query.get_or_404(rule_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not rule.project or rule.project not in current_user.projects.all()):
        abort(403)
    
    rule.is_active = not rule.is_active
    db.session.commit()
    
    status = _("启用") if rule.is_active else _("禁用")
    flash(_('规则已{}').format(status), 'success')
    return redirect(url_for('rules.update_rules'))


@rules_bp.route('/update_rules/delete/<int:rule_id>')
@login_required
def delete_rule(rule_id):
    """删除升级规则"""
    rule = UpdateRule.query.get_or_404(rule_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not rule.project or rule.project not in current_user.projects.all()):
        abort(403)
    
    db.session.delete(rule)
    db.session.commit()
    
    flash(_('规则已删除'), 'success')
    return redirect(url_for('rules.update_rules'))


@rules_bp.route('/update_rules/get_firmwares/<int:project_id>')
@login_required
def get_project_firmwares(project_id):
    """获取项目的固件列表（AJAX）"""
    # 检查项目权限
    project = Project.query.get_or_404(project_id)
    
    if not current_user.is_administrator() and project not in current_user.projects:
        return jsonify({'error': _('您没有权限访问此项目')}), 403
    
    # 获取项目的固件列表
    firmwares = Firmware.query.filter_by(project_id=project_id, is_active=True).all()
    firmware_list = [{'id': f.id, 'version': f.version} for f in firmwares]
    
    return jsonify({'firmwares': firmware_list})
