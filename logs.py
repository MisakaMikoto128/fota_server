from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, abort
from flask_login import login_required, current_user
from flask_babel import gettext as _
from datetime import datetime, timedelta
import csv
import io

from models import db, UpdateLog, Device, Project

# 创建蓝图
logs_bp = Blueprint('logs', __name__)

@logs_bp.route('/logs')
@login_required
def logs():
    """日志列表"""
    # 筛选条件
    imei_filter = request.args.get('imei', '')
    version_filter = request.args.get('version', '')
    status_filter = request.args.get('status', '')
    project_id = request.args.get('project_id', type=int)
    
    # 日期范围
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    # 构建查询
    if current_user.is_administrator():
        # 管理员可以查看所有日志
        if project_id:
            # 如果指定了项目，只查看该项目的日志
            query = UpdateLog.query.filter_by(project_id=project_id)
        else:
            query = UpdateLog.query
    else:
        # 普通用户只能查看自己项目的日志
        user_projects = current_user.projects.all()
        project_ids = [p.id for p in user_projects]
        
        if project_id and project_id in project_ids:
            # 如果指定了项目且用户有权限，只查看该项目的日志
            query = UpdateLog.query.filter_by(project_id=project_id)
        else:
            # 否则查看用户所有项目的日志
            query = UpdateLog.query.filter(UpdateLog.project_id.in_(project_ids))
    
    # 应用筛选条件
    if imei_filter:
        # 通过IMEI筛选设备
        device_ids = [d.id for d in Device.query.filter(Device.imei.like(f'%{imei_filter}%')).all()]
        query = query.filter(UpdateLog.device_id.in_(device_ids))
    
    if version_filter:
        # 通过版本号筛选
        query = query.filter((UpdateLog.from_version.like(f'%{version_filter}%')) | 
                            (UpdateLog.to_version.like(f'%{version_filter}%')))
    
    if status_filter:
        # 通过状态筛选
        query = query.filter(UpdateLog.status == status_filter)
    
    # 应用日期范围
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(UpdateLog.update_time >= start_date)
        except ValueError:
            flash(_('开始日期格式无效'), 'warning')
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            # 将结束日期设为当天的最后一秒
            end_date = end_date + timedelta(days=1, seconds=-1)
            query = query.filter(UpdateLog.update_time <= end_date)
        except ValueError:
            flash(_('结束日期格式无效'), 'warning')
    
    # 排序
    logs = query.order_by(UpdateLog.update_time.desc()).all()
    
    # 获取用户可访问的项目列表
    if current_user.is_administrator():
        projects = Project.query.all()
    else:
        projects = current_user.projects.all()
    
    return render_template('logs/logs.html', 
                          logs=logs, 
                          projects=projects,
                          current_project_id=project_id,
                          imei_filter=imei_filter,
                          version_filter=version_filter,
                          status_filter=status_filter,
                          start_date=start_date_str,
                          end_date=end_date_str)


@logs_bp.route('/logs/update_status/<int:log_id>/<status>')
@login_required
def update_log_status(log_id, status):
    """更新日志状态"""
    if status not in ['success', 'failed', 'pending']:
        flash(_('无效的状态'), 'danger')
        return redirect(url_for('logs.logs'))
    
    log = UpdateLog.query.get_or_404(log_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not log.project or log.project not in current_user.projects.all()):
        abort(403)
    
    log.status = status
    
    # 如果状态为成功，更新设备的最后更新时间和当前版本
    if status == 'success' and log.device:
        log.device.last_update_time = datetime.now()
        log.device.current_version = log.to_version
    
    db.session.commit()
    
    flash(_('日志状态已更新'), 'success')
    return redirect(url_for('logs.logs'))


@logs_bp.route('/logs/export')
@login_required
def export_logs():
    """导出日志为CSV文件"""
    # 筛选条件（与日志列表相同）
    imei_filter = request.args.get('imei', '')
    version_filter = request.args.get('version', '')
    status_filter = request.args.get('status', '')
    project_id = request.args.get('project_id', type=int)
    
    # 日期范围
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    # 构建查询
    if current_user.is_administrator():
        # 管理员可以查看所有日志
        if project_id:
            # 如果指定了项目，只查看该项目的日志
            query = UpdateLog.query.filter_by(project_id=project_id)
        else:
            query = UpdateLog.query
    else:
        # 普通用户只能查看自己项目的日志
        user_projects = current_user.projects.all()
        project_ids = [p.id for p in user_projects]
        
        if project_id and project_id in project_ids:
            # 如果指定了项目且用户有权限，只查看该项目的日志
            query = UpdateLog.query.filter_by(project_id=project_id)
        else:
            # 否则查看用户所有项目的日志
            query = UpdateLog.query.filter(UpdateLog.project_id.in_(project_ids))
    
    # 应用筛选条件
    if imei_filter:
        # 通过IMEI筛选设备
        device_ids = [d.id for d in Device.query.filter(Device.imei.like(f'%{imei_filter}%')).all()]
        query = query.filter(UpdateLog.device_id.in_(device_ids))
    
    if version_filter:
        # 通过版本号筛选
        query = query.filter((UpdateLog.from_version.like(f'%{version_filter}%')) | 
                            (UpdateLog.to_version.like(f'%{version_filter}%')))
    
    if status_filter:
        # 通过状态筛选
        query = query.filter(UpdateLog.status == status_filter)
    
    # 应用日期范围
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query = query.filter(UpdateLog.update_time >= start_date)
        except ValueError:
            pass
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            # 将结束日期设为当天的最后一秒
            end_date = end_date + timedelta(days=1, seconds=-1)
            query = query.filter(UpdateLog.update_time <= end_date)
        except ValueError:
            pass
    
    # 获取日志
    logs = query.order_by(UpdateLog.update_time.desc()).all()
    
    # 创建CSV内容
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入标题行
    writer.writerow([
        _('项目'), 
        _('设备IMEI'), 
        _('从版本'), 
        _('到版本'), 
        _('更新时间'), 
        _('状态')
    ])
    
    # 写入数据行
    for log in logs:
        writer.writerow([
            log.project.name if log.project else '',
            log.device.imei if log.device else '',
            log.from_version,
            log.to_version,
            log.update_time.strftime('%Y-%m-%d %H:%M:%S'),
            log.status
        ])
    
    # 设置响应
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=fota_logs_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv'}
    )
