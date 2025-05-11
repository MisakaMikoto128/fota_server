"""
AJAX API模块，用于处理前端异步请求
"""

from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from flask_babel import gettext as _
import logging

from models import db, Firmware, Device, UpdateRule

# 创建蓝图
api_ajax_bp = Blueprint('api_ajax', __name__)

# 配置日志
logger = logging.getLogger(__name__)

@api_ajax_bp.route('/api/ajax/toggle_firmware', methods=['POST'])
@login_required
def toggle_firmware():
    """启用/禁用固件（AJAX）"""
    firmware_id = request.json.get('firmware_id')
    if not firmware_id:
        return jsonify({'success': False, 'message': _('参数错误')}), 400
    
    firmware = Firmware.query.get_or_404(firmware_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not firmware.project or firmware.project not in current_user.projects.all()):
        return jsonify({'success': False, 'message': _('权限不足')}), 403
    
    # 切换状态
    firmware.is_active = not firmware.is_active
    db.session.commit()
    
    status = _("启用") if firmware.is_active else _("禁用")
    return jsonify({
        'success': True, 
        'message': _('固件 {} 已{}').format(firmware.version, status),
        'is_active': firmware.is_active
    })

@api_ajax_bp.route('/api/ajax/toggle_device_auth', methods=['POST'])
@login_required
def toggle_device_auth():
    """启用/禁用设备授权（AJAX）"""
    device_id = request.json.get('device_id')
    if not device_id:
        return jsonify({'success': False, 'message': _('参数错误')}), 400
    
    device = Device.query.get_or_404(device_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not device.project or device.project not in current_user.projects.all()):
        return jsonify({'success': False, 'message': _('权限不足')}), 403
    
    # 切换状态
    device.is_authorized = not device.is_authorized
    db.session.commit()
    
    status = _("授权") if device.is_authorized else _("禁用")
    return jsonify({
        'success': True, 
        'message': _('设备 {} 已{}').format(device.imei, status),
        'is_authorized': device.is_authorized
    })

@api_ajax_bp.route('/api/ajax/toggle_rule', methods=['POST'])
@login_required
def toggle_rule():
    """启用/禁用升级规则（AJAX）"""
    rule_id = request.json.get('rule_id')
    if not rule_id:
        return jsonify({'success': False, 'message': _('参数错误')}), 400
    
    rule = UpdateRule.query.get_or_404(rule_id)
    
    # 检查权限
    if not current_user.is_administrator() and (not rule.project or rule.project not in current_user.projects.all()):
        return jsonify({'success': False, 'message': _('权限不足')}), 403
    
    # 切换状态
    rule.is_active = not rule.is_active
    db.session.commit()
    
    status = _("启用") if rule.is_active else _("禁用")
    return jsonify({
        'success': True, 
        'message': _('规则已{}').format(status),
        'is_active': rule.is_active
    })
