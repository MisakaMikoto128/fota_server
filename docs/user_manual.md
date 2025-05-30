# FOTA服务器用户手册

本手册提供了FOTA服务器的详细使用说明，包括安装配置、界面操作和常见问题解答等内容。

## 目录

1. [系统概述](#系统概述)
2. [安装配置](#安装配置)
3. [登录系统](#登录系统)
4. [仪表盘](#仪表盘)
5. [固件管理](#固件管理)
6. [设备管理](#设备管理)
7. [升级规则](#升级规则)
8. [日志记录](#日志记录)
9. [个人资料](#个人资料)
10. [常见问题](#常见问题)

## 系统概述

FOTA（Firmware Over-The-Air）固件升级服务器是一个用于管理物联网设备固件升级的Web应用。通过该系统，您可以：

- 管理设备信息和授权状态
- 上传和管理固件版本
- 配置设备升级规则
- 查看和导出升级日志
- 监控设备升级状态

系统支持AIR780E等设备的固件升级，采用版本号格式为xxx.yyy.zzz（如001.000.001）。

## 安装配置

### 系统要求

- Python 3.6+
- 50MB以上磁盘空间
- 512MB以上内存

### 安装步骤

1. 安装Python和pip（如果尚未安装）
2. 克隆或下载项目代码
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 运行应用：
   ```bash
   python app.py
   ```
5. 在浏览器中访问：http://localhost:5000

### 配置选项

主要配置选项位于`app.py`文件中：

- `SECRET_KEY`：应用密钥，生产环境中应修改为随机字符串
- `SQLALCHEMY_DATABASE_URI`：数据库连接URI，默认使用SQLite
- `MAX_CONTENT_LENGTH`：上传文件大小限制，默认为50MB

## 登录系统

1. 访问系统首页
2. 点击"管理员登录"按钮
3. 输入用户名和密码
   - 默认用户名：admin
   - 默认密码：admin123
4. 点击"登录"按钮

**注意**：首次登录后，建议立即修改默认密码。

## 仪表盘

仪表盘页面显示系统的概览信息，包括：

- 设备总数
- 固件版本数
- 今日更新数
- 待更新设备数
- 最近更新记录
- 设备版本分布图表
- 系统活动记录

通过仪表盘，您可以快速了解系统状态和设备升级情况。

## 固件管理

### 查看固件列表

固件管理页面显示所有已上传的固件版本，包括版本号、文件名、大小、上传时间和状态等信息。

### 上传新固件

1. 点击"上传新固件"按钮
2. 填写版本号（格式：xxx.yyy.zzz）
3. 选择固件文件（.bin格式）
4. 填写版本描述（可选）
5. 点击"上传"按钮

### 管理固件

对于每个固件版本，您可以执行以下操作：

- **下载**：下载固件文件
- **查看详情**：查看固件的详细信息
- **启用/禁用**：控制固件是否可用于设备升级
- **删除**：删除固件版本（同时删除文件）

## 设备管理

### 查看设备列表

设备管理页面显示所有已注册的设备，包括IMEI、名称、当前版本、最后检查时间、最后更新时间和状态等信息。

### 筛选设备

您可以使用以下条件筛选设备：

- IMEI
- 当前版本
- 状态（已授权/未授权）

### 添加设备

1. 点击"添加设备"按钮
2. 填写IMEI（15位数字）
3. 填写设备名称（可选）
4. 填写当前版本（可选）
5. 选择是否授权设备
6. 点击"添加"按钮

### 批量导入设备

1. 点击"批量导入"按钮
2. 选择CSV文件（包含列：IMEI,名称,当前版本,是否授权）
3. 选择是否跳过第一行（标题行）
4. 点击"导入"按钮

### 管理设备

对于每个设备，您可以执行以下操作：

- **查看详情**：查看设备的详细信息和更新历史
- **编辑**：修改设备名称
- **授权/禁用**：控制设备是否可以升级固件
- **删除**：删除设备记录

## 升级规则

### 查看规则列表

升级规则页面显示所有已配置的升级规则，包括起始版本、目标版本、固件、创建时间和状态等信息。

### 添加规则

1. 点击"添加规则"按钮
2. 填写起始版本（设备当前的版本）
3. 填写目标版本（设备将升级到的版本）
4. 选择对应的固件
5. 选择是否启用规则
6. 点击"添加"按钮

### 管理规则

对于每个规则，您可以执行以下操作：

- **启用/禁用**：控制规则是否生效
- **删除**：删除规则

## 日志记录

### 查看日志列表

日志记录页面显示所有设备的更新历史，包括设备IMEI、从版本、到版本、更新时间和状态等信息。

### 筛选日志

您可以使用以下条件筛选日志：

- IMEI
- 版本
- 状态（成功/失败/进行中）
- 日期范围

### 更新日志状态

对于状态为"进行中"的日志，您可以手动更新为：

- **成功**：表示升级已成功完成
- **失败**：表示升级失败

### 导出日志

点击"导出日志"按钮，可以将日志导出为CSV文件。

## 个人资料

### 查看个人资料

个人资料页面显示当前登录用户的信息，包括用户名、角色、账户创建时间和最后登录时间等。

### 修改密码

1. 输入当前密码
2. 输入新密码
3. 确认新密码
4. 点击"更新密码"按钮

## 常见问题

### 设备无法检查更新

可能的原因：
- 设备未授权
- 没有适用的升级规则
- 设备当前版本没有对应的升级路径

解决方法：
1. 检查设备是否已授权
2. 确认是否已添加适用的升级规则
3. 验证设备当前版本是否正确

### 设备下载固件失败

可能的原因：
- 固件文件不存在
- 固件已被禁用
- 网络连接问题

解决方法：
1. 检查固件文件是否存在
2. 确认固件状态是否为启用
3. 检查网络连接

### 无法上传固件

可能的原因：
- 文件格式不正确
- 文件大小超过限制
- 版本号格式不正确
- 版本号已存在

解决方法：
1. 确保文件为.bin格式
2. 检查文件大小是否超过50MB
3. 确保版本号格式为xxx.yyy.zzz
4. 使用未使用过的版本号

### 设备升级后无法启动

可能的原因：
- 固件不兼容
- 升级过程中断
- 固件损坏

解决方法：
1. 使用兼容的固件版本
2. 确保升级过程不会中断
3. 验证固件的完整性

### 系统性能问题

如果系统运行缓慢，可以尝试：
1. 清理旧的日志记录
2. 删除不再使用的固件
3. 优化数据库（`VACUUM`命令）
4. 增加服务器资源
