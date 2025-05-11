from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_from_directory
from flask_login import login_required, current_user
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from models import db, Firmware, Project
from forms import FirmwareUploadForm
from config import Config

# 创建蓝图
firmware_bp = Blueprint('firmware', __name__)

@firmware_bp.route('/firmware')
@login_required
def firmware_list():
    """固件列表"""
    # 筛选条件
    version_filter = request.args.get('version', '')
    project_id = request.args.get('project_id', type=int)
    
    # 构建查询
    if current_user.is_administrator():
        # 管理员可以查看所有固件
        if project_id:
            # 如果指定了项目，只查看该项目的固件
            query = Firmware.query.filter_by(project_id=project_id)
        else:
            query = Firmware.query
    else:
        # 普通用户只能查看自己项目的固件
        user_projects = current_user.projects.all()
        project_ids = [p.id for p in user_projects]
        
        if project_id and project_id in project_ids:
            # 如果指定了项目且用户有权限，只查看该项目的固件
            query = Firmware.query.filter_by(project_id=project_id)
        else:
            # 否则查看用户所有项目的固件
            query = Firmware.query.filter(Firmware.project_id.in_(project_ids))
    
    # 应用筛选条件
    if version_filter:
        query = query.filter(Firmware.version.like(f'%{version_filter}%'))
    
    # 排序
    firmwares = query.order_by(Firmware.created_at.desc()).all()
    
    # 获取用户可访问的项目列表
    if current_user.is_administrator():
        projects = Project.query.all()
    else:
        projects = current_user.projects.all()
    
    # 上传表单
    upload_form = FirmwareUploadForm()
    upload_form.project_id.choices = [(p.id, p.name) for p in projects]
    
    return render_template('firmware/firmware_list.html', 
                          firmwares=firmwares, 
                          upload_form=upload_form,
                          projects=projects,
                          current_project_id=project_id)


@firmware_bp.route('/firmware/upload', methods=['POST'])
@login_required
def firmware_upload():
    """上传新固件"""
    form = FirmwareUploadForm()
    
    # 获取用户可访问的项目列表
    if current_user.is_administrator():
        projects = Project.query.all()
    else:
        projects = current_user.projects.all()
    
    form.project_id.choices = [(p.id, p.name) for p in projects]
    
    if form.validate_on_submit():
        # 检查项目权限
        project_id = form.project_id.data
        project = Project.query.get_or_404(project_id)
        
        if not current_user.is_administrator() and project not in current_user.projects:
            flash(_('您没有权限向此项目上传固件'), 'danger')
            return redirect(url_for('firmware.firmware_list'))
        
        # 检查版本是否已存在
        if Firmware.query.filter_by(version=form.version.data, project_id=project_id).first():
            flash(_('版本 {} 在项目中已存在').format(form.version.data), 'danger')
            return redirect(url_for('firmware.firmware_list'))
        
        # 保存文件
        firmware_file = form.firmware_file.data
        filename = secure_filename(f"{project.name}_{form.version.data}_{firmware_file.filename}")
        file_path = os.path.join(Config.UPDATE_DIR, filename)
        firmware_file.save(file_path)
        
        # 创建固件记录
        firmware = Firmware(
            version=form.version.data,
            filename=filename,
            description=form.description.data,
            filesize=os.path.getsize(file_path),
            is_active=True,
            project_id=project_id,
            uploaded_by_id=current_user.id
        )
        db.session.add(firmware)
        db.session.commit()
        
        flash(_('固件 {} 上传成功').format(form.version.data), 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('firmware.firmware_list'))


@firmware_bp.route('/firmware/download/<int:firmware_id>')
@login_required
def download_firmware(firmware_id):
    """下载固件"""
    firmware = Firmware.query.get_or_404(firmware_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not firmware.project or firmware.project not in current_user.projects.all()):
        abort(403)
    
    return send_from_directory(Config.UPDATE_DIR, firmware.filename, as_attachment=True)


@firmware_bp.route('/firmware/toggle/<int:firmware_id>')
@login_required
def toggle_firmware(firmware_id):
    """启用/禁用固件"""
    firmware = Firmware.query.get_or_404(firmware_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not firmware.project or firmware.project not in current_user.projects.all()):
        abort(403)
    
    firmware.is_active = not firmware.is_active
    db.session.commit()
    
    status = _("启用") if firmware.is_active else _("禁用")
    flash(_('固件 {} 已{}').format(firmware.version, status), 'success')
    return redirect(url_for('firmware.firmware_list'))


@firmware_bp.route('/firmware/delete/<int:firmware_id>')
@login_required
def delete_firmware(firmware_id):
    """删除固件"""
    firmware = Firmware.query.get_or_404(firmware_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not firmware.project or firmware.project not in current_user.projects.all()):
        abort(403)
    
    # 删除文件
    file_path = os.path.join(Config.UPDATE_DIR, firmware.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # 删除数据库记录
    db.session.delete(firmware)
    db.session.commit()
    
    flash(_('固件 {} 已删除').format(firmware.version), 'success')
    return redirect(url_for('firmware.firmware_list'))
