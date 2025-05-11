from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from flask_babel import gettext as _
from datetime import datetime
import csv
import io

from models import db, Device, Project, UpdateLog
from forms import DeviceForm, ImportDevicesForm

# 创建蓝图
devices_bp = Blueprint('devices', __name__)

@devices_bp.route('/devices')
@login_required
def device_list():
    """设备列表"""
    # 筛选条件
    imei_filter = request.args.get('imei', '')
    version_filter = request.args.get('version', '')
    status_filter = request.args.get('status', '')
    project_id = request.args.get('project_id', type=int)
    
    # 构建查询
    if current_user.is_administrator():
        # 管理员可以查看所有设备
        if project_id:
            # 如果指定了项目，只查看该项目的设备
            query = Device.query.filter_by(project_id=project_id)
        else:
            query = Device.query
    else:
        # 普通用户只能查看自己项目的设备
        user_projects = current_user.projects.all()
        project_ids = [p.id for p in user_projects]
        
        if project_id and project_id in project_ids:
            # 如果指定了项目且用户有权限，只查看该项目的设备
            query = Device.query.filter_by(project_id=project_id)
        else:
            # 否则查看用户所有项目的设备
            query = Device.query.filter(Device.project_id.in_(project_ids))
    
    # 应用筛选条件
    if imei_filter:
        query = query.filter(Device.imei.like(f'%{imei_filter}%'))
    if version_filter:
        query = query.filter(Device.current_version.like(f'%{version_filter}%'))
    if status_filter:
        is_authorized = (status_filter == 'authorized')
        query = query.filter(Device.is_authorized == is_authorized)
    
    # 分页
    page = request.args.get('page', 1, type=int)
    pagination = query.paginate(page=page, per_page=10)
    devices = pagination.items
    
    # 获取用户可访问的项目列表
    if current_user.is_administrator():
        projects = Project.query.all()
    else:
        projects = current_user.projects.all()
    
    # 表单
    device_form = DeviceForm()
    device_form.project_id.choices = [(p.id, p.name) for p in projects]
    
    import_form = ImportDevicesForm()
    import_form.project_id.choices = [(p.id, p.name) for p in projects]
    
    return render_template('devices/device_list.html',
                          devices=devices,
                          pagination=pagination,
                          device_form=device_form,
                          import_form=import_form,
                          projects=projects,
                          current_project_id=project_id)


@devices_bp.route('/devices/add', methods=['POST'])
@login_required
def add_device():
    """添加设备"""
    form = DeviceForm()
    
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
            flash(_('您没有权限向此项目添加设备'), 'danger')
            return redirect(url_for('devices.device_list'))
        
        # 检查IMEI是否已存在
        if Device.query.filter_by(imei=form.imei.data).first():
            flash(_('IMEI为 {} 的设备已存在').format(form.imei.data), 'danger')
            return redirect(url_for('devices.device_list'))
        
        # 创建设备记录
        device = Device(
            imei=form.imei.data,
            name=form.name.data,
            current_version=form.current_version.data,
            is_authorized=form.is_authorized.data,
            project_id=project_id
        )
        db.session.add(device)
        db.session.commit()
        
        flash(_('设备 {} 添加成功').format(form.imei.data), 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('devices.device_list'))


@devices_bp.route('/devices/<int:device_id>')
@login_required
def device_detail(device_id):
    """设备详情"""
    device = Device.query.get_or_404(device_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not device.project or device.project not in current_user.projects.all()):
        abort(403)
    
    # 获取设备的更新日志
    update_logs = UpdateLog.query.filter_by(device_id=device_id).order_by(UpdateLog.update_time.desc()).all()
    
    # 编辑表单
    form = DeviceForm()
    
    # 获取用户可访问的项目列表
    if current_user.is_administrator():
        projects = Project.query.all()
    else:
        projects = current_user.projects.all()
    
    form.project_id.choices = [(p.id, p.name) for p in projects]
    
    if request.method == 'GET':
        form.imei.data = device.imei
        form.name.data = device.name
        form.current_version.data = device.current_version
        form.is_authorized.data = device.is_authorized
        if device.project_id:
            form.project_id.data = device.project_id
    
    return render_template('devices/device_detail.html', 
                          device=device, 
                          update_logs=update_logs, 
                          form=form)


@devices_bp.route('/devices/edit/<int:device_id>', methods=['POST'])
@login_required
def edit_device(device_id):
    """编辑设备"""
    device = Device.query.get_or_404(device_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not device.project or device.project not in current_user.projects.all()):
        abort(403)
    
    form = DeviceForm()
    
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
            flash(_('您没有权限将设备移动到此项目'), 'danger')
            return redirect(url_for('devices.device_detail', device_id=device_id))
        
        # 更新设备信息
        device.name = form.name.data
        device.is_authorized = form.is_authorized.data
        device.project_id = project_id
        
        if form.current_version.data:
            device.current_version = form.current_version.data
            
        db.session.commit()
        flash(_('设备 {} 更新成功').format(device.imei), 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    # 检查是从设备详情页还是设备列表页提交的
    referrer = request.referrer
    if referrer and 'devices/' + str(device_id) in referrer:
        return redirect(url_for('devices.device_detail', device_id=device_id))
    else:
        return redirect(url_for('devices.device_list'))


@devices_bp.route('/devices/toggle/<int:device_id>')
@login_required
def toggle_device_auth(device_id):
    """启用/禁用设备授权"""
    device = Device.query.get_or_404(device_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not device.project or device.project not in current_user.projects.all()):
        abort(403)
    
    device.is_authorized = not device.is_authorized
    db.session.commit()
    
    status = _("授权") if device.is_authorized else _("禁用")
    flash(_('设备 {} 已{}').format(device.imei, status), 'success')
    
    # 检查是从设备详情页还是设备列表页提交的
    referrer = request.referrer
    if referrer and 'devices/' + str(device_id) in referrer:
        return redirect(url_for('devices.device_detail', device_id=device_id))
    else:
        return redirect(url_for('devices.device_list'))


@devices_bp.route('/devices/delete/<int:device_id>')
@login_required
def delete_device(device_id):
    """删除设备"""
    device = Device.query.get_or_404(device_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not device.project or device.project not in current_user.projects.all()):
        abort(403)
    
    db.session.delete(device)
    db.session.commit()
    
    flash(_('设备 {} 已删除').format(device.imei), 'success')
    return redirect(url_for('devices.device_list'))


@devices_bp.route('/devices/import', methods=['POST'])
@login_required
def import_devices():
    """批量导入设备"""
    form = ImportDevicesForm()
    
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
            flash(_('您没有权限向此项目导入设备'), 'danger')
            return redirect(url_for('devices.device_list'))
        
        csv_file = form.import_file.data
        skip_header = form.skip_header.data
        
        # 读取CSV文件
        stream = io.StringIO(csv_file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.reader(stream)
        
        # 跳过标题行
        if skip_header:
            next(csv_reader)
        
        # 导入设备
        count = 0
        for row in csv_reader:
            if len(row) >= 1:
                imei = row[0].strip()
                name = row[1].strip() if len(row) > 1 else ""
                version = row[2].strip() if len(row) > 2 else ""
                is_authorized = True
                if len(row) > 3:
                    is_authorized = row[3].strip().lower() in ['true', '1', 'yes', 'y']
                
                # 检查IMEI是否已存在
                if not Device.query.filter_by(imei=imei).first():
                    device = Device(
                        imei=imei,
                        name=name,
                        current_version=version,
                        is_authorized=is_authorized,
                        project_id=project_id
                    )
                    db.session.add(device)
                    count += 1
        
        db.session.commit()
        flash(_('成功导入 {} 个设备').format(count), 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('devices.device_list'))


@devices_bp.route('/devices/start_upgrade/<int:device_id>')
@login_required
def start_upgrade(device_id):
    """启动设备升级"""
    device = Device.query.get_or_404(device_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not device.project or device.project not in current_user.projects.all()):
        abort(403)
    
    # 这里只是打印日志，实际功能后期实现
    print(f"启动设备 {device.imei} 的升级")
    
    flash(_('已向设备 {} 发送升级指令').format(device.imei), 'success')
    
    # 检查是从设备详情页还是设备列表页提交的
    referrer = request.referrer
    if referrer and 'devices/' + str(device_id) in referrer:
        return redirect(url_for('devices.device_detail', device_id=device_id))
    else:
        return redirect(url_for('devices.device_list'))
