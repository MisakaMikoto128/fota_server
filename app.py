from flask import Flask, request, jsonify, send_from_directory, Response, render_template, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import logging
import csv
import io
from models import db, User, Device, Firmware, UpdateRule, UpdateLog
from forms import LoginForm, FirmwareUploadForm, DeviceForm, UpdateRuleForm, ImportDevicesForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # 生产环境中应使用安全的随机密钥
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fota.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 限制上传文件大小为50MB
app.config['WTF_CSRF_ENABLED'] = False  # 暂时禁用CSRF保护，简化开发

# 初始化数据库
db.init_app(app)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录以访问此页面'
login_manager.login_message_category = 'warning'

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 升级包存储目录（确保该目录存在）
UPDATE_DIR = os.path.join(os.path.dirname(__file__), 'update_packages')
if not os.path.exists(UPDATE_DIR):
    os.makedirs(UPDATE_DIR)

# 用户加载函数
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 版本信息数据库 - 适配新的版本格式 (xxx.yyy.zzz)
# 这个字典将在数据库初始化后被替换
VERSIONS = {
    # 格式: "当前版本": {"new_version": "新版本", "file": "升级文件名"}
    "001.000.000": {"new_version": "001.000.001", "file": "fotademo_1113.001.001_LuatOS-SoC_EC618.bin"},
}

# 创建数据库表
@app.before_first_request
def create_tables():
    db.create_all()
    # 检查是否需要创建管理员账户
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin123')  # 默认密码，生产环境应修改
        db.session.add(admin)
        db.session.commit()
        logger.info("已创建默认管理员账户")

# 上下文处理器，为所有模板提供通用变量
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/update/check', methods=['GET'])
def check_update():
    """检查是否有可用的固件更新（旧接口，保留兼容）"""
    current_version = request.args.get('version')
    imei = request.args.get('imei')  # 获取设备IMEI（用于授权验证）

    logger.info(f"检查更新请求: 版本={current_version}, IMEI={imei}")

    # 查找设备并验证授权
    device = None
    if imei:
        device = Device.query.filter_by(imei=imei).first()
        if device:
            # 更新设备的当前版本和检查时间
            if current_version and device.current_version != current_version:
                device.current_version = current_version
            device.last_check_time = datetime.now()
            db.session.commit()

    # 设备授权验证
    authorized = True
    if device and not device.is_authorized:
        authorized = False

    if not authorized:
        return jsonify({"code": -1, "message": "设备未授权"}), 403

    # 查找适用的更新规则
    update_rule = UpdateRule.query.filter_by(
        from_version=current_version,
        is_active=True
    ).first()

    if not update_rule:
        return jsonify({
            "code": 0,
            "data": {"update_available": False},
            "message": "当前已是最新版本"
        })

    # 获取固件信息
    firmware = Firmware.query.get(update_rule.firmware_id)
    if not firmware or not firmware.is_active:
        return jsonify({
            "code": 0,
            "data": {"update_available": False},
            "message": "当前已是最新版本"
        })

    update_url = f"/update/download/{firmware.filename}"

    return jsonify({
        "code": 0,
        "data": {
            "update_available": True,
            "new_version": update_rule.to_version,
            "download_url": update_url
        },
        "message": "发现新版本"
    })

@app.route('/upgrade', methods=['GET'])
def upgrade():
    """libfota2 升级接口"""
    # 获取请求参数
    imei = request.args.get('imei', '')
    project_key = request.args.get('project_key', '')
    firmware_name = request.args.get('firmware_name', '')
    version = request.args.get('version', '')

    logger.info(f"升级请求: IMEI={imei}, 项目={project_key}, 固件={firmware_name}, 版本={version}")

    # 从版本字符串中提取客户端版本号
    # 格式: BSP版本.x.z，我们只关心x.y.z部分
    client_version = None
    try:
        parts = version.split('.')
        if len(parts) >= 3:
            # 取最后三位作为版本号
            client_version = f"{parts[-3]}.{parts[-2]}.{parts[-1]}"
        else:
            # 如果格式不对，尝试直接匹配
            client_version = version
    except Exception as e:
        logger.error(f"解析版本号出错: {e}")
        return Response("版本号格式错误", status=400)

    logger.info(f"解析后的客户端版本: {client_version}")

    # 查找设备并更新信息
    device = None
    if imei:
        device = Device.query.filter_by(imei=imei).first()
        if not device:
            # 自动创建新设备
            device = Device(imei=imei, current_version=client_version)
            db.session.add(device)
            db.session.commit()
            logger.info(f"自动创建新设备: IMEI={imei}, 版本={client_version}")
        elif device.current_version != client_version:
            # 更新设备版本
            device.current_version = client_version
            db.session.commit()

    # 设备授权验证
    if device and not device.is_authorized:
        logger.warning(f"设备未授权: IMEI={imei}")
        return Response("设备未授权", status=403)

    # 查找适用的更新规则
    update_rule = UpdateRule.query.filter_by(
        from_version=client_version,
        is_active=True
    ).first()

    if not update_rule:
        logger.info(f"没有找到适用的更新规则: 版本={client_version}")
        return Response("No update available", status=404)

    # 获取固件信息
    firmware = Firmware.query.get(update_rule.firmware_id)
    if not firmware or not firmware.is_active:
        logger.warning(f"固件不存在或未启用: ID={update_rule.firmware_id}")
        return Response("No update available", status=404)

    update_file = os.path.join(UPDATE_DIR, firmware.filename)
    if not os.path.exists(update_file):
        logger.error(f"更新文件不存在: {update_file}")
        return Response("Update file not found", status=404)

    # 记录更新日志
    if device:
        update_log = UpdateLog(
            device_id=device.id,
            from_version=client_version,
            to_version=update_rule.to_version,
            status='pending'
        )
        db.session.add(update_log)
        db.session.commit()

    logger.info(f"提供更新: 设备={imei}, 从={client_version}, 到={update_rule.to_version}, 文件={firmware.filename}")

    # 返回固件文件
    with open(update_file, 'rb') as f:
        return Response(f.read(), mimetype='application/octet-stream')

@app.route('/update/download/<path:filename>')
def download_firmware(filename):
    """提供固件下载服务（旧接口，保留兼容）"""
    logger.info(f"下载请求: {filename}")
    return send_from_directory(UPDATE_DIR, filename, as_attachment=True)

# 前端路由
@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('登录成功！', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('登录失败，请检查用户名和密码', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """退出登录"""
    logout_user()
    flash('您已成功退出登录', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """仪表盘页面"""
    # 统计数据
    stats = {
        'device_count': Device.query.count(),
        'firmware_count': Firmware.query.count(),
        'today_updates': UpdateLog.query.filter(
            UpdateLog.update_time >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count(),
        'pending_updates': 0  # 待实现
    }

    # 最近更新记录
    recent_updates = UpdateLog.query.order_by(UpdateLog.update_time.desc()).limit(5).all()

    # 版本分布
    version_distribution = {}
    for device in Device.query.all():
        if device.current_version:
            if device.current_version in version_distribution:
                version_distribution[device.current_version] += 1
            else:
                version_distribution[device.current_version] = 1

    # 系统活动
    system_activities = []  # 待实现

    return render_template('dashboard.html',
                          stats=stats,
                          recent_updates=recent_updates,
                          version_distribution=version_distribution,
                          system_activities=system_activities)

@app.route('/firmware')
@login_required
def firmware_list():
    """固件管理页面"""
    firmwares = Firmware.query.order_by(Firmware.created_at.desc()).all()
    upload_form = FirmwareUploadForm()
    return render_template('firmware_list.html', firmwares=firmwares, upload_form=upload_form)

@app.route('/firmware/upload', methods=['POST'])
@login_required
def firmware_upload():
    """上传新固件"""
    form = FirmwareUploadForm()
    if form.validate_on_submit():
        # 检查版本是否已存在
        if Firmware.query.filter_by(version=form.version.data).first():
            flash(f'版本 {form.version.data} 已存在', 'danger')
            return redirect(url_for('firmware_list'))

        # 保存文件
        firmware_file = form.firmware_file.data
        filename = secure_filename(firmware_file.filename)
        file_path = os.path.join(UPDATE_DIR, filename)
        firmware_file.save(file_path)

        # 创建固件记录
        firmware = Firmware(
            version=form.version.data,
            filename=filename,
            description=form.description.data,
            filesize=os.path.getsize(file_path),
            is_active=True
        )
        db.session.add(firmware)
        db.session.commit()

        flash(f'固件 {form.version.data} 上传成功', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')

    return redirect(url_for('firmware_list'))

@app.route('/firmware/download/<int:firmware_id>')
@login_required
def download_firmware_admin(firmware_id):
    """管理员下载固件"""
    firmware = Firmware.query.get_or_404(firmware_id)
    return send_from_directory(UPDATE_DIR, firmware.filename, as_attachment=True)

@app.route('/firmware/toggle/<int:firmware_id>')
@login_required
def toggle_firmware(firmware_id):
    """启用/禁用固件"""
    firmware = Firmware.query.get_or_404(firmware_id)
    firmware.is_active = not firmware.is_active
    db.session.commit()

    status = "启用" if firmware.is_active else "禁用"
    flash(f'固件 {firmware.version} 已{status}', 'success')
    return redirect(url_for('firmware_list'))

@app.route('/firmware/delete/<int:firmware_id>')
@login_required
def delete_firmware(firmware_id):
    """删除固件"""
    firmware = Firmware.query.get_or_404(firmware_id)

    # 删除文件
    file_path = os.path.join(UPDATE_DIR, firmware.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # 删除数据库记录
    db.session.delete(firmware)
    db.session.commit()

    flash(f'固件 {firmware.version} 已删除', 'success')
    return redirect(url_for('firmware_list'))

@app.route('/devices')
@login_required
def device_list():
    """设备管理页面"""
    # 筛选条件
    imei_filter = request.args.get('imei', '')
    version_filter = request.args.get('version', '')
    status_filter = request.args.get('status', '')

    # 构建查询
    query = Device.query
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

    # 表单
    device_form = DeviceForm()
    import_form = ImportDevicesForm()

    return render_template('device_list.html',
                          devices=devices,
                          pagination=pagination,
                          device_form=device_form,
                          import_form=import_form)

@app.route('/devices/add', methods=['POST'])
@login_required
def add_device():
    """添加设备"""
    form = DeviceForm()
    if form.validate_on_submit():
        # 检查IMEI是否已存在
        if Device.query.filter_by(imei=form.imei.data).first():
            flash(f'IMEI为 {form.imei.data} 的设备已存在', 'danger')
            return redirect(url_for('device_list'))

        # 创建设备记录
        device = Device(
            imei=form.imei.data,
            name=form.name.data,
            current_version=form.current_version.data,
            is_authorized=form.is_authorized.data
        )
        db.session.add(device)
        db.session.commit()

        flash(f'设备 {form.imei.data} 添加成功', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')

    return redirect(url_for('device_list'))

@app.route('/devices/<int:device_id>')
@login_required
def device_detail(device_id):
    """设备详情页面"""
    device = Device.query.get_or_404(device_id)
    update_logs = UpdateLog.query.filter_by(device_id=device_id).order_by(UpdateLog.update_time.desc()).all()
    form = DeviceForm()
    return render_template('device_detail.html', device=device, update_logs=update_logs, form=form)

@app.route('/devices/edit/<int:device_id>', methods=['POST'])
@login_required
def edit_device(device_id):
    """编辑设备"""
    device = Device.query.get_or_404(device_id)
    form = DeviceForm()

    if form.validate_on_submit():
        device.name = form.name.data
        if form.current_version.data:
            device.current_version = form.current_version.data
        db.session.commit()
        flash(f'设备 {device.imei} 更新成功', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')

    # 检查是从设备详情页还是设备列表页提交的
    referrer = request.referrer
    if referrer and 'devices/' + str(device_id) in referrer:
        return redirect(url_for('device_detail', device_id=device_id))
    else:
        return redirect(url_for('device_list'))

@app.route('/devices/toggle/<int:device_id>')
@login_required
def toggle_device_auth(device_id):
    """启用/禁用设备授权"""
    device = Device.query.get_or_404(device_id)
    device.is_authorized = not device.is_authorized
    db.session.commit()

    status = "授权" if device.is_authorized else "禁用"
    flash(f'设备 {device.imei} 已{status}', 'success')
    return redirect(url_for('device_list'))

@app.route('/devices/delete/<int:device_id>')
@login_required
def delete_device(device_id):
    """删除设备"""
    device = Device.query.get_or_404(device_id)
    db.session.delete(device)
    db.session.commit()

    flash(f'设备 {device.imei} 已删除', 'success')
    return redirect(url_for('device_list'))

@app.route('/devices/import', methods=['POST'])
@login_required
def import_devices():
    """批量导入设备"""
    form = ImportDevicesForm()
    if form.validate_on_submit():
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
                        is_authorized=is_authorized
                    )
                    db.session.add(device)
                    count += 1

        db.session.commit()
        flash(f'成功导入 {count} 个设备', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')

    return redirect(url_for('device_list'))

@app.route('/update_rules')
@login_required
def update_rules():
    """升级规则管理页面"""
    rules = UpdateRule.query.all()
    form = UpdateRuleForm()
    firmwares = Firmware.query.filter_by(is_active=True).all()
    return render_template('update_rules.html', rules=rules, form=form, firmwares=firmwares)

@app.route('/update_rules/add', methods=['POST'])
@login_required
def add_rule():
    """添加升级规则"""
    if request.method == 'POST':
        from_version = request.form.get('from_version')
        to_version = request.form.get('to_version')
        firmware_id = request.form.get('firmware_id')
        is_active = 'is_active' in request.form

        # 验证输入
        if not from_version or not to_version or not firmware_id:
            flash('所有必填字段都必须填写', 'danger')
            return redirect(url_for('update_rules'))

        # 检查规则是否已存在
        existing_rule = UpdateRule.query.filter_by(
            from_version=from_version,
            to_version=to_version
        ).first()

        if existing_rule:
            flash(f'从 {from_version} 到 {to_version} 的规则已存在', 'danger')
            return redirect(url_for('update_rules'))

        # 创建规则
        rule = UpdateRule(
            from_version=from_version,
            to_version=to_version,
            firmware_id=firmware_id,
            is_active=is_active
        )
        db.session.add(rule)
        db.session.commit()

        flash('升级规则添加成功', 'success')

    return redirect(url_for('update_rules'))

@app.route('/update_rules/toggle/<int:rule_id>')
@login_required
def toggle_rule(rule_id):
    """启用/禁用升级规则"""
    rule = UpdateRule.query.get_or_404(rule_id)
    rule.is_active = not rule.is_active
    db.session.commit()

    status = "启用" if rule.is_active else "禁用"
    flash(f'规则已{status}', 'success')
    return redirect(url_for('update_rules'))

@app.route('/update_rules/delete/<int:rule_id>')
@login_required
def delete_rule(rule_id):
    """删除升级规则"""
    rule = UpdateRule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()

    flash(f'规则已删除', 'success')
    return redirect(url_for('update_rules'))

@app.route('/logs')
@login_required
def logs():
    """日志记录页面"""
    # 筛选条件
    imei_filter = request.args.get('imei', '')
    version_filter = request.args.get('version', '')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    # 构建查询
    query = UpdateLog.query

    # 应用筛选条件
    if imei_filter:
        query = query.join(Device).filter(Device.imei.like(f'%{imei_filter}%'))

    if version_filter:
        query = query.filter(
            (UpdateLog.from_version.like(f'%{version_filter}%')) |
            (UpdateLog.to_version.like(f'%{version_filter}%'))
        )

    if status_filter:
        query = query.filter(UpdateLog.status == status_filter)

    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(UpdateLog.update_time >= date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj + timedelta(days=1)  # 包含结束日期
            query = query.filter(UpdateLog.update_time < date_to_obj)
        except ValueError:
            pass

    # 排序和分页
    query = query.order_by(UpdateLog.update_time.desc())
    page = request.args.get('page', 1, type=int)
    pagination = query.paginate(page=page, per_page=20)
    logs = pagination.items

    return render_template('logs.html', logs=logs, pagination=pagination)

@app.route('/logs/update_status/<int:log_id>/<status>')
@login_required
def update_log_status(log_id, status):
    """更新日志状态"""
    if status not in ['success', 'failed', 'pending']:
        flash('无效的状态', 'danger')
        return redirect(url_for('logs'))

    log = UpdateLog.query.get_or_404(log_id)
    log.status = status

    # 如果状态为成功，更新设备的最后更新时间和当前版本
    if status == 'success':
        device = log.device
        if device:
            device.last_update_time = datetime.now()
            device.current_version = log.to_version

    db.session.commit()

    flash('日志状态已更新', 'success')
    return redirect(url_for('logs'))

@app.route('/logs/export')
@login_required
def export_logs():
    """导出日志为CSV文件"""
    # 获取所有日志
    logs = UpdateLog.query.order_by(UpdateLog.update_time.desc()).all()

    # 创建CSV内容
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入标题行
    writer.writerow(['设备IMEI', '从版本', '到版本', '更新时间', '状态'])

    # 写入数据行
    for log in logs:
        writer.writerow([
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

@app.route('/profile')
@login_required
def profile():
    """个人资料页面"""
    return render_template('profile.html', timedelta=timedelta)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    # 验证表单数据
    if not current_password or not new_password or not confirm_password:
        flash('所有字段都是必填的', 'danger')
        return redirect(url_for('profile'))

    if new_password != confirm_password:
        flash('新密码和确认密码不匹配', 'danger')
        return redirect(url_for('profile'))

    # 验证当前密码
    if not current_user.check_password(current_password):
        flash('当前密码不正确', 'danger')
        return redirect(url_for('profile'))

    # 更新密码
    current_user.set_password(new_password)
    db.session.commit()

    flash('密码已成功更新', 'success')
    return redirect(url_for('profile'))

# 启动应用
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)