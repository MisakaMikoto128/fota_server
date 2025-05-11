from flask import Blueprint, request, jsonify, send_from_directory, Response, abort
from flask_babel import gettext as _
from datetime import datetime
import os
import logging

from models import db, Device, Firmware, UpdateRule, UpdateLog, Project
from config import Config

# 创建蓝图
api_bp = Blueprint('api', __name__)

# 配置日志
logger = logging.getLogger(__name__)

@api_bp.route('/update/check', methods=['GET'])
def check_update():
    """检查是否有可用的固件更新（旧接口，保留兼容）"""
    current_version = request.args.get('version')
    imei = request.args.get('imei')  # 获取设备IMEI（用于授权验证）
    project_key = request.args.get('project_key', '')  # 项目密钥（可选）

    logger.info(f"检查更新请求: 版本={current_version}, IMEI={imei}, 项目密钥={project_key}")

    # 查找项目
    project = None
    if project_key:
        project = Project.query.filter_by(project_key=project_key).first()
        if not project:
            logger.warning(f"项目密钥无效: {project_key}")
            return jsonify({"code": -1, "message": _("项目密钥无效")}), 403

    # 查找设备并验证授权
    device = None
    if imei:
        if project:
            # 如果指定了项目，在项目内查找设备
            device = Device.query.filter_by(imei=imei, project_id=project.id).first()
        else:
            # 否则在所有设备中查找
            device = Device.query.filter_by(imei=imei).first()
        
        if device:
            # 更新设备的当前版本和检查时间
            if current_version and device.current_version != current_version:
                device.current_version = current_version
            device.last_check_time = datetime.now()
            db.session.commit()
        elif project:
            # 自动创建新设备并添加到项目中
            device = Device(
                imei=imei, 
                current_version=current_version,
                project_id=project.id,
                last_check_time=datetime.now()
            )
            db.session.add(device)
            db.session.commit()
            logger.info(f"自动创建新设备: IMEI={imei}, 版本={current_version}, 项目={project.name}")

    # 设备授权验证
    authorized = True
    if device and not device.is_authorized:
        authorized = False

    if not authorized:
        logger.warning(f"设备未授权: IMEI={imei}")
        return jsonify({"code": -1, "message": _("设备未授权")}), 403

    # 查找适用的更新规则
    if project:
        # 如果指定了项目，在项目内查找规则
        update_rule = UpdateRule.query.filter_by(
            from_version=current_version,
            is_active=True,
            project_id=project.id
        ).first()
    else:
        # 否则查找所有规则
        update_rule = UpdateRule.query.filter_by(
            from_version=current_version,
            is_active=True
        ).first()

    if not update_rule:
        logger.info(f"没有找到适用的更新规则: 版本={current_version}")
        return jsonify({
            "code": 0,
            "data": {"update_available": False},
            "message": _("当前已是最新版本")
        })

    # 获取固件信息
    firmware = Firmware.query.get(update_rule.firmware_id)
    if not firmware or not firmware.is_active:
        logger.warning(f"固件不存在或未启用: ID={update_rule.firmware_id}")
        return jsonify({
            "code": 0,
            "data": {"update_available": False},
            "message": _("当前已是最新版本")
        })

    update_url = f"/update/download/{firmware.filename}"

    logger.info(f"发现可用更新: 从={current_version}, 到={update_rule.to_version}, 文件={firmware.filename}")
    return jsonify({
        "code": 0,
        "data": {
            "update_available": True,
            "new_version": update_rule.to_version,
            "download_url": update_url
        },
        "message": _("发现新版本")
    })


@api_bp.route('/upgrade', methods=['GET'])
def upgrade():
    """libfota2 升级接口"""
    # 获取请求参数
    imei = request.args.get('imei', '')
    project_key = request.args.get('project_key', '')
    firmware_name = request.args.get('firmware_name', '')
    version = request.args.get('version', '')

    logger.info(f"升级请求: IMEI={imei}, 项目密钥={project_key}, 固件={firmware_name}, 版本={version}")

    # 查找项目
    project = None
    if project_key:
        project = Project.query.filter_by(project_key=project_key).first()
        if not project:
            logger.warning(f"项目密钥无效: {project_key}")
            return Response(_("项目密钥无效"), status=403)

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
        return Response(_("版本号格式错误"), status=400)

    logger.info(f"解析后的客户端版本: {client_version}")

    # 查找设备并更新信息
    device = None
    if imei:
        if project:
            # 如果指定了项目，在项目内查找设备
            device = Device.query.filter_by(imei=imei, project_id=project.id).first()
        else:
            # 否则在所有设备中查找
            device = Device.query.filter_by(imei=imei).first()
        
        if not device:
            # 自动创建新设备
            device = Device(
                imei=imei, 
                current_version=client_version,
                project_id=project.id if project else None
            )
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
        return Response(_("设备未授权"), status=403)

    # 查找适用的更新规则
    if project:
        # 如果指定了项目，在项目内查找规则
        update_rule = UpdateRule.query.filter_by(
            from_version=client_version,
            is_active=True,
            project_id=project.id
        ).first()
    else:
        # 否则查找所有规则
        update_rule = UpdateRule.query.filter_by(
            from_version=client_version,
            is_active=True
        ).first()

    if not update_rule:
        logger.info(f"没有找到适用的更新规则: 版本={client_version}")
        return Response(_("No update available"), status=404)

    # 获取固件信息
    firmware = Firmware.query.get(update_rule.firmware_id)
    if not firmware or not firmware.is_active:
        logger.warning(f"固件不存在或未启用: ID={update_rule.firmware_id}")
        return Response(_("No update available"), status=404)

    update_file = os.path.join(Config.UPDATE_DIR, firmware.filename)
    if not os.path.exists(update_file):
        logger.error(f"更新文件不存在: {update_file}")
        return Response(_("Update file not found"), status=404)

    # 记录更新日志
    if device:
        update_log = UpdateLog(
            device_id=device.id,
            from_version=client_version,
            to_version=update_rule.to_version,
            status='pending',
            project_id=project.id if project else None,
            firmware_id=firmware.id
        )
        db.session.add(update_log)
        db.session.commit()

    logger.info(f"提供更新: 设备={imei}, 从={client_version}, 到={update_rule.to_version}, 文件={firmware.filename}")

    # 返回固件文件
    with open(update_file, 'rb') as f:
        return Response(f.read(), mimetype='application/octet-stream')


@api_bp.route('/update/download/<path:filename>')
def download_firmware(filename):
    """提供固件下载服务（旧接口，保留兼容）"""
    logger.info(f"下载请求: {filename}")
    return send_from_directory(Config.UPDATE_DIR, filename, as_attachment=True)
