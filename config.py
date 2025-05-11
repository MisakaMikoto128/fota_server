import os

class Config:
    """基本配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 限制上传文件大小为50MB
    WTF_CSRF_ENABLED = True  # 启用CSRF保护
    
    # 固件存储目录
    UPDATE_DIR = os.path.join(os.path.dirname(__file__), 'update_packages')
    
    # 安全设置
    ENABLE_HTTPS = False  # 默认不启用HTTPS
    
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


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
