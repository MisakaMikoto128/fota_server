from flask import Flask, request, jsonify, send_from_directory, Response
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 升级包存储目录（确保该目录存在）
UPDATE_DIR = os.path.join(os.path.dirname(__file__), 'update_packages')
if not os.path.exists(UPDATE_DIR):
    os.makedirs(UPDATE_DIR)

# 版本信息数据库 - 适配新的版本格式 (xxx.yyy.zzz)
VERSIONS = {
    # 格式: "当前版本": {"new_version": "新版本", "file": "升级文件名"}
    "001.000.000": {"new_version": "001.000.001", "file": "fotademo_1113.001.001_LuatOS-SoC_EC618.bin"},
}

@app.route('/update/check', methods=['GET'])
def check_update():
    """检查是否有可用的固件更新（旧接口，保留兼容）"""
    current_version = request.args.get('version')
    imei = request.args.get('imei')  # 获取设备IMEI（用于授权验证）

    logger.info(f"检查更新请求: 版本={current_version}, IMEI={imei}")

    # 模拟设备授权验证
    authorized = True  # 假设所有设备都已授权

    if not authorized:
        return jsonify({"code": -1, "message": "设备未授权"}), 403

    if current_version not in VERSIONS:
        return jsonify({
            "code": 0,
            "data": {"update_available": False},
            "message": "当前已是最新版本"
        })

    update_info = VERSIONS[current_version]
    update_url = f"/update/download/{update_info['file']}"

    return jsonify({
        "code": 0,
        "data": {
            "update_available": True,
            "new_version": update_info['new_version'],
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

    # 检查是否有可用更新
    if client_version in VERSIONS:
        update_info = VERSIONS[client_version]
        update_file = os.path.join(UPDATE_DIR, update_info['file'])

        if os.path.exists(update_file):
            logger.info(f"找到更新: {update_file}")
            # 直接返回文件内容
            with open(update_file, 'rb') as f:
                return Response(f.read(), mimetype='application/octet-stream')
        else:
            logger.error(f"更新文件不存在: {update_file}")

    # 没有更新或文件不存在，返回404
    logger.info("没有可用更新")
    return Response("No update available", status=404)

@app.route('/update/download/<path:filename>')
def download_firmware(filename):
    """提供固件下载服务（旧接口，保留兼容）"""
    logger.info(f"下载请求: {filename}")
    return send_from_directory(UPDATE_DIR, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)