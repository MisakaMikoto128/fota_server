from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__)

# 升级包存储目录（确保该目录存在）
UPDATE_DIR = os.path.join(os.path.dirname(__file__), 'update_packages')
if not os.path.exists(UPDATE_DIR):
    os.makedirs(UPDATE_DIR)

# 模拟版本信息数据库
VERSIONS = {
    "current_version": "1.0.0",
    "available_updates": {
        "1.0.0": {"new_version": "1.0.0", "file": "main.lua"},
    }
}

@app.route('/update/check', methods=['GET'])
def check_update():
    """检查是否有可用的固件更新"""
    current_version = request.args.get('version')
    imei = request.args.get('imei')  # 获取设备IMEI（用于授权验证）

    # 模拟设备授权验证（实际应用中应对接你的设备管理系统）
    authorized = True  # 假设所有设备都已授权

    if not authorized:
        return jsonify({"code": -1, "message": "设备未授权"}), 403

    if current_version not in VERSIONS['available_updates']:
        return jsonify({
            "code": 0,
            "data": {"update_available": False},
            "message": "当前已是最新版本"
        })

    update_info = VERSIONS['available_updates'][current_version]
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

@app.route('/upgrade')
def download_firmware():
    """提供固件下载服务"""
    return send_from_directory(UPDATE_DIR, "fotademo_1113.001.001_LuatOS-SoC_EC618.bin", as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)