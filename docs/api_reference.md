# FOTA服务器 API参考文档

本文档详细描述了FOTA服务器提供的API接口，包括请求参数、返回值和示例。

## API概述

FOTA服务器提供了以下API接口：

1. 检查更新：设备检查是否有可用的固件更新
2. 下载固件：设备下载固件文件
3. libfota2升级接口：兼容libfota2库的升级接口

所有API均使用HTTP协议，支持GET请求方法。

## 通用响应格式

对于JSON响应，采用以下格式：

```json
{
  "code": 0,       // 状态码，0表示成功，非0表示错误
  "data": {},      // 响应数据，对象或数组
  "message": ""    // 状态消息
}
```

## API详情

### 1. 检查更新

#### 请求

```
GET /update/check
```

#### 参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| version | String | 是 | 设备当前版本号，格式：xxx.yyy.zzz |
| imei | String | 是 | 设备IMEI号，用于授权验证 |

#### 响应

成功响应（有可用更新）：

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

成功响应（无可用更新）：

```json
{
  "code": 0,
  "data": {
    "update_available": false
  },
  "message": "当前已是最新版本"
}
```

错误响应（设备未授权）：

```json
{
  "code": -1,
  "message": "设备未授权"
}
```

#### 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 403 | 设备未授权 |

#### 示例

请求：

```
GET /update/check?version=001.000.000&imei=123456789012345
```

响应：

```json
{
  "code": 0,
  "data": {
    "update_available": true,
    "new_version": "001.000.001",
    "download_url": "/update/download/fotademo_1113.001.001_LuatOS-SoC_EC618.bin"
  },
  "message": "发现新版本"
}
```

### 2. 下载固件

#### 请求

```
GET /update/download/{filename}
```

#### 参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| filename | String | 是 | 固件文件名，从检查更新API获取 |

#### 响应

成功响应：
- Content-Type: application/octet-stream
- 固件文件的二进制内容

#### 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 404 | 文件不存在 |

#### 示例

请求：

```
GET /update/download/fotademo_1113.001.001_LuatOS-SoC_EC618.bin
```

响应：
- 二进制文件内容

### 3. libfota2升级接口

#### 请求

```
GET /upgrade
```

#### 参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| imei | String | 是 | 设备IMEI号 |
| version | String | 是 | 设备当前版本号 |
| project_key | String | 否 | 项目标识 |
| firmware_name | String | 否 | 固件名称 |

#### 响应

成功响应：
- Content-Type: application/octet-stream
- 固件文件的二进制内容

#### 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 403 | 设备未授权 |
| 404 | 无可用更新或文件不存在 |

#### 示例

请求：

```
GET /upgrade?imei=123456789012345&version=001.000.000&project_key=demo&firmware_name=air780e
```

响应：
- 二进制文件内容

## 版本号格式

版本号采用`xxx.yyy.zzz`格式，其中：
- xxx：主版本号
- yyy：次版本号（暂未使用）
- zzz：修订版本号

示例：`001.000.001`

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| -1 | 设备未授权 |
| -2 | 参数错误 |
| -3 | 服务器内部错误 |

## 客户端集成指南

### 使用libfota2库

对于使用libfota2库的设备，可以直接使用升级接口：

```lua
-- 示例代码（Lua）
local libfota = require "libfota2"

-- 初始化FOTA
libfota.init("http://your-server.com/upgrade", "your-project-key", "your-firmware-name")

-- 检查更新
libfota.request()

-- 处理更新结果
libfota.on_result(function(result, info)
    if result == 0 then
        -- 更新成功
        log.info("FOTA", "Update success")
    else
        -- 更新失败
        log.error("FOTA", "Update failed", result)
    end
end)
```

### 自定义实现

对于不使用libfota2库的设备，可以按以下步骤实现：

1. 调用检查更新API，获取是否有可用更新
2. 如果有可用更新，下载新固件
3. 安装新固件并重启设备

```python
# 示例代码（Python）
import requests
import os

def check_update(server_url, current_version, imei):
    response = requests.get(f"{server_url}/update/check", params={
        "version": current_version,
        "imei": imei
    })
    
    if response.status_code == 200:
        data = response.json()
        if data["code"] == 0 and data["data"]["update_available"]:
            return data["data"]
    
    return None

def download_firmware(server_url, download_url, save_path):
    response = requests.get(f"{server_url}{download_url}", stream=True)
    
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    
    return False

def update_firmware(server_url, current_version, imei):
    # 检查更新
    update_info = check_update(server_url, current_version, imei)
    
    if update_info:
        # 下载固件
        firmware_path = f"firmware_{update_info['new_version']}.bin"
        if download_firmware(server_url, update_info["download_url"], firmware_path):
            # 安装固件（设备特定实现）
            install_firmware(firmware_path)
            return True
    
    return False
```

## 安全建议

1. 在生产环境中使用HTTPS
2. 实现设备认证机制，防止未授权设备升级
3. 添加固件签名验证，确保固件的完整性和真实性
