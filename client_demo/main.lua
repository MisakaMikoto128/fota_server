-- LuaTools需要PROJECT和VERSION这两个信息
PROJECT = "fotademo"
-- iot限制，只能上传xxx.yyy.zzz格式的三位数的版本号，但实际上现在只用了XXX和ZZZ,中间yyy暂未使用
-- 需要注意的是,因为yyy不生效，所以111.222.333版本和111.444.333版本，对iot平台来说都一样，所以建议中间那一位永远写000
VERSION = "001.000.000"

-- 使用合宙iot平台时需要这个参数
PRODUCT_KEY = "123" -- 到 iot.openluat.com 创建项目,获取正确的项目key(刚刚剪切板里的校验码就填这里)

sys = require "sys"
libfota2 = require "libfota2"

-- 联网函数, 可自行删减
sys.taskInit(function()
    -- 默认都等到联网成功
    sys.waitUntil("IP_READY")
    log.info("4G网络链接成功")
    sys.publish("net_ready")
end)

-- 循环打印版本号, 方便看版本号变化, 非必须
sys.taskInit(function()
    while 1 do
        sys.wait(5000)
        log.info("降功耗,找合宙")
        log.info("fota", "version", VERSION)
    end
end)

-- 升级结果的回调函数
-- 功能:获取fota的回调函数
-- 参数:
-- result:number类型
--   0表示成功
--   1表示连接失败
--   2表示url错误
--   3表示服务器断开
--   4表示接收报文错误
--   5表示使用iot平台VERSION需要使用 xxx.yyy.zzz形式
local function fota_cb(ret)
    log.info("fota", ret)
    if ret == 0 then
        log.info("升级包下载成功,重启模块")
        rtos.reboot()
    elseif ret == 1 then
        log.info("连接失败", "请检查url拼写或服务器配置(是否为内网)")
    elseif ret == 2 then
        log.info("url错误", "检查url拼写")
    elseif ret == 3 then
        log.info("服务器断开", "检查服务器白名单配置")
    elseif ret == 4 then
        log.info("接收报文错误", "检查模块固件或升级包内文件是否正常")
    elseif ret == 5 then
        log.info("版本号书写错误", "iot平台版本号需要使用xxx.yyy.zzz形式")
    else
        log.info("不是上面几种情况 ret为", ret)
    end
end

local ota_opts = {
    url = "http://117.50.188.64:5000/upgrade?",
    imei = "123456789012345", -- 设备imei
    project_key = "fotademo", -- 项目密钥
    firmware_name = "fotademo_custom", -- 暂时未使用
    version = VERSION -- 当前版本号
}

sys.taskInit(function()
    -- 这个判断是提醒要设置PRODUCT_KEY的,实际生产请删除
    if "123" == _G.PRODUCT_KEY and not ota_opts.url then
        while 1 do
            sys.wait(1000)
            log.info("fota", "请修改正确的PRODUCT_KEY")
        end
    end
    -- 等待网络就行后开始检查升级
    sys.waitUntil("net_ready")
    log.info("开始检查升级")
    sys.wait(500)
    libfota2.request(fota_cb, ota_opts)
end)
-- 演示定时自动升级, 每隔4小时自动检查一次
sys.timerLoopStart(libfota2.request, 4 * 3600000, fota_cb, ota_opts)

-- 用户代码已结束---------------------------------------------
-- 结尾总是这一句
sys.run()
-- sys.run()之后后面不要加任何语句!!!!!
