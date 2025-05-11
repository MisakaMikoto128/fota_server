from flask import Flask, request, session, g, render_template
from flask_login import LoginManager, current_user
import os
import logging
from datetime import datetime

from models import db, User, Role
from config import config
import babel_support as babel_module
from auth import auth_bp
from pages import pages_bp
from projects import projects_bp
from devices import devices_bp
from firmware import firmware_bp
from rules import rules_bp
from logs import logs_bp
from api import api_bp

def create_app(config_name='default'):
    """创建Flask应用"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # 初始化数据库
    db.init_app(app)

    # 初始化登录管理器
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.login_message_category = 'warning'

    # 初始化国际化支持
    babel_module.init_app(app)

    # 配置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(devices_bp)
    app.register_blueprint(firmware_bp)
    app.register_blueprint(rules_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(api_bp)

    # 用户加载函数
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 创建数据库表
    @app.before_first_request
    def create_tables():
        db.create_all()
        # 初始化角色
        if not Role.query.first():
            Role.insert_roles()
            logger.info("已初始化角色")

        # 检查是否需要创建管理员账户
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')  # 默认密码，生产环境应修改
            db.session.add(admin)
            db.session.commit()
            logger.info("已创建默认管理员账户")

    # 上下文处理器，为所有模板提供通用变量
    @app.context_processor
    def inject_common_variables():
        return {
            'now': datetime.now(),
            'current_user': current_user
        }

    # 请求前处理
    @app.before_request
    def before_request():
        g.user = current_user
        # 设置用户语言
        if current_user.is_authenticated:
            if 'language' not in session:
                session['language'] = request.accept_languages.best_match(app.config['LANGUAGES']) or app.config['DEFAULT_LANGUAGE']

    # 错误处理
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    return app


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    app.run(host='0.0.0.0', port=5000, debug=True)
