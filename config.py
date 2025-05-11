import os
import secrets

class Config:
    """基本配置类"""
    # 使用随机生成的密钥，提高安全性
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 限制上传文件大小为50MB
    WTF_CSRF_ENABLED = True  # 启用CSRF保护

    # 固件存储目录
    UPDATE_DIR = os.path.join(os.path.dirname(__file__), 'update_packages')

    # 安全设置
    ENABLE_HTTPS = False  # 默认不启用HTTPS
    HTTPS_CERT_PATH = None  # HTTPS证书路径
    HTTPS_KEY_PATH = None   # HTTPS密钥路径

    # 请求限制
    RATE_LIMIT_ENABLED = True  # 启用请求限制
    RATE_LIMIT_PER_MINUTE = 60  # 每分钟最大请求数

    # 密码安全策略
    PASSWORD_MIN_LENGTH = 8  # 密码最小长度
    PASSWORD_REQUIRE_SPECIAL = False  # 是否要求特殊字符

    # 固件验证
    FIRMWARE_VERIFY_ENABLED = False  # 是否启用固件验证
    FIRMWARE_VERIFY_KEY = None  # 固件验证密钥

    # 国际化设置
    LANGUAGES = ['zh', 'en', 'ja']
    DEFAULT_LANGUAGE = 'zh'

    @staticmethod
    def init_app(app):
        """初始化应用"""
        # 确保升级包目录存在
        if not os.path.exists(Config.UPDATE_DIR):
            os.makedirs(Config.UPDATE_DIR)


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///fota.db'
    WTF_CSRF_ENABLED = False  # 开发环境禁用CSRF保护，简化开发


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False  # 测试环境禁用CSRF保护


class ProductionConfig(Config):
    """生产环境配置"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///fota.db'
    WTF_CSRF_ENABLED = True  # 生产环境强制启用CSRF保护

    # 生产环境安全设置
    RATE_LIMIT_ENABLED = True  # 启用请求限制
    RATE_LIMIT_PER_MINUTE = 30  # 生产环境限制更严格
    PASSWORD_REQUIRE_SPECIAL = True  # 生产环境要求密码包含特殊字符

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # 生产环境特定的配置
        import logging
        from logging.handlers import RotatingFileHandler

        # 创建日志目录
        if not os.path.exists('logs'):
            os.mkdir('logs')

        # 配置文件日志
        file_handler = RotatingFileHandler('logs/fota.log', maxBytes=10*1024*1024, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('FOTA服务器启动')

        # 如果启用HTTPS，配置SSL上下文
        if cls.ENABLE_HTTPS and cls.HTTPS_CERT_PATH and cls.HTTPS_KEY_PATH:
            app.logger.info('启用HTTPS')
            try:
                import ssl
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ctx.load_cert_chain(cls.HTTPS_CERT_PATH, cls.HTTPS_KEY_PATH)
                app.config['SSL_CONTEXT'] = ctx
            except Exception as e:
                app.logger.error(f'HTTPS配置失败: {str(e)}')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
