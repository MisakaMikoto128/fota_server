# FOTA 固件升级服务器

FOTA（Firmware Over-The-Air）固件升级服务器是一个基于Flask的Web应用，用于管理物联网设备的固件升级。该系统支持AIR780E等设备的固件版本控制、设备管理和升级日志记录等功能。

## 功能特点

- **设备管理**：添加、编辑、删除和授权管理设备
- **固件管理**：上传、下载、启用/禁用和删除固件
- **升级规则**：配置从特定版本升级到特定版本的规则
- **日志记录**：记录设备的更新历史，支持查询和导出
- **用户认证**：基本的用户登录和权限控制
- **响应式界面**：适配桌面和移动设备的Web界面

## 系统要求

- Python 3.6+
- Flask 2.0.1+
- SQLite 3

## 安装步骤

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/fota-server.git
cd fota-server
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 运行应用：

```bash
python app.py
```

4. 在浏览器中访问：

```
http://localhost:5000
```

## 目录结构

```
fota_server/
├── app.py              # 主应用文件
├── models.py           # 数据库模型
├── forms.py            # 表单定义
├── requirements.txt    # 依赖列表
├── static/             # 静态资源
│   ├── css/            # CSS样式
│   └── js/             # JavaScript脚本
├── templates/          # HTML模板
└── update_packages/    # 固件存储目录
```

## API接口

### 检查更新

```
GET /update/check?version={current_version}&imei={device_imei}
```

参数：
- `version`：设备当前版本号（格式：xxx.yyy.zzz）
- `imei`：设备IMEI号（用于授权验证）

返回示例：
```json
{
  "code": 0,
  "data": {
    "update_available": true,
    "new_version": "001.000.002",
    "download_url": "/update/download/firmware.bin"
  },
  "message": "发现新版本"
}
```

### 下载固件

```
GET /update/download/{filename}
```

参数：
- `filename`：固件文件名

返回：
- 固件文件的二进制内容

### libfota2升级接口

```
GET /upgrade?imei={device_imei}&version={current_version}&project_key={project_key}&firmware_name={firmware_name}
```

参数：
- `imei`：设备IMEI号
- `version`：设备当前版本号
- `project_key`：项目标识（可选）
- `firmware_name`：固件名称（可选）

返回：
- 固件文件的二进制内容

## 使用说明

### 管理员登录

- 默认用户名：admin
- 默认密码：admin123

### 固件管理

1. 上传新固件：点击"上传新固件"按钮，填写版本号和选择固件文件
2. 管理固件：可以下载、查看详情、启用/禁用或删除固件

### 设备管理

1. 添加设备：点击"添加设备"按钮，填写IMEI和其他信息
2. 批量导入：通过CSV文件批量导入设备
3. 管理设备：可以编辑、授权/禁用或删除设备

### 升级规则

1. 添加规则：点击"添加规则"按钮，设置从哪个版本升级到哪个版本，并选择对应的固件
2. 管理规则：可以启用/禁用或删除规则

### 日志记录

1. 查看日志：可以查看所有设备的更新历史
2. 筛选日志：可以按设备、版本、状态和日期筛选日志
3. 导出日志：可以导出日志为CSV文件

## 客户端集成

客户端设备需要实现以下功能：

1. 定期调用检查更新API，获取是否有可用更新
2. 如果有可用更新，下载新固件
3. 安装新固件并重启设备

对于使用libfota2库的设备，可以直接使用升级接口。

## 安全注意事项

1. 生产环境中应修改默认管理员密码
2. 建议启用HTTPS以保护数据传输安全
3. 根据需要配置设备授权，防止未授权设备升级

## 许可证

[MIT License](LICENSE)

## 联系方式

如有问题或建议，请联系：your-email@example.com
