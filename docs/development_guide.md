# FOTA服务器开发指南

本文档提供了FOTA服务器的开发指南，包括架构设计、数据模型、API接口和前端开发等内容。

## 架构设计

FOTA服务器采用了经典的MVC（Model-View-Controller）架构：

- **Model**：数据库模型，定义在`models.py`中
- **View**：HTML模板，存放在`templates/`目录下
- **Controller**：路由和业务逻辑，定义在`app.py`中

### 技术栈

- **后端**：Flask、SQLAlchemy、Flask-Login
- **前端**：Bootstrap 5、jQuery、Chart.js
- **数据库**：SQLite（可扩展到其他数据库）

## 数据模型

### User（用户）

用户模型，用于管理员登录和权限控制。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| username | String | 用户名 |
| password_hash | String | 密码哈希 |
| is_admin | Boolean | 是否为管理员 |
| last_login | DateTime | 最后登录时间 |
| created_at | DateTime | 创建时间 |

### Device（设备）

设备模型，记录连接到系统的设备信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| imei | String | 设备IMEI号 |
| name | String | 设备名称 |
| current_version | String | 当前版本 |
| last_check_time | DateTime | 最后检查更新时间 |
| last_update_time | DateTime | 最后更新时间 |
| is_authorized | Boolean | 是否授权 |
| created_at | DateTime | 创建时间 |

### Firmware（固件）

固件模型，记录可用的固件版本。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| version | String | 版本号 |
| filename | String | 文件名 |
| description | Text | 版本描述 |
| filesize | Integer | 文件大小（字节） |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |

### UpdateRule（更新规则）

更新规则，定义从哪个版本可以更新到哪个版本。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| from_version | String | 起始版本 |
| to_version | String | 目标版本 |
| firmware_id | Integer | 固件ID（外键） |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |

### UpdateLog（更新日志）

更新日志，记录设备的更新历史。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| device_id | Integer | 设备ID（外键） |
| from_version | String | 起始版本 |
| to_version | String | 目标版本 |
| update_time | DateTime | 更新时间 |
| status | String | 状态（'success', 'failed', 'pending'） |

## API接口

### 检查更新

```
GET /update/check
```

参数：
- `version`：设备当前版本号（格式：xxx.yyy.zzz）
- `imei`：设备IMEI号（用于授权验证）

返回：
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
GET /upgrade
```

参数：
- `imei`：设备IMEI号
- `version`：设备当前版本号
- `project_key`：项目标识（可选）
- `firmware_name`：固件名称（可选）

返回：
- 固件文件的二进制内容

## 前端开发

### 模板结构

- `layout.html`：基础布局模板
- `index.html`：首页
- `login.html`：登录页面
- `dashboard.html`：仪表盘
- `firmware_list.html`：固件管理
- `device_list.html`：设备管理
- `device_detail.html`：设备详情
- `update_rules.html`：升级规则
- `logs.html`：日志记录
- `profile.html`：个人资料

### 静态资源

- `static/css/style.css`：自定义样式
- `static/js/main.js`：自定义脚本

### 第三方库

- Bootstrap 5：响应式UI框架
- Chart.js：图表库
- Bootstrap Icons：图标库

## 开发指南

### 添加新功能

1. 在`models.py`中添加新的数据模型（如果需要）
2. 在`forms.py`中添加新的表单类（如果需要）
3. 在`app.py`中添加新的路由和处理函数
4. 在`templates/`目录下添加新的HTML模板
5. 更新`static/`目录下的CSS和JavaScript文件（如果需要）

### 修改现有功能

1. 找到相关的路由和处理函数
2. 修改处理逻辑
3. 更新相应的HTML模板

### 数据库迁移

如果修改了数据模型，需要进行数据库迁移：

1. 安装Flask-Migrate：`pip install Flask-Migrate`
2. 初始化迁移：`flask db init`
3. 创建迁移脚本：`flask db migrate -m "描述"`
4. 应用迁移：`flask db upgrade`

## 测试

### 单元测试

可以使用Python的`unittest`或`pytest`框架进行单元测试。

示例：

```python
import unittest
from app import app, db

class TestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_check_update(self):
        response = self.app.get('/update/check?version=001.000.000&imei=123456789012345')
        self.assertEqual(response.status_code, 200)
        # 更多断言...

if __name__ == '__main__':
    unittest.main()
```

### API测试

可以使用Postman或curl进行API测试。

示例（curl）：

```bash
curl -X GET "http://localhost:5000/update/check?version=001.000.000&imei=123456789012345"
```

## 部署

### 开发环境

```bash
python app.py
```

### 生产环境

建议使用Gunicorn和Nginx进行部署：

1. 安装Gunicorn：`pip install gunicorn`
2. 启动应用：`gunicorn -w 4 -b 127.0.0.1:8000 app:app`
3. 配置Nginx作为反向代理

Nginx配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /path/to/your/app/static;
    }
}
```

## 贡献指南

1. Fork仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -am 'Add some feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交Pull Request
