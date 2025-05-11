from flask_babel import Babel

babel = Babel()

def init_app(app):
    """初始化Babel国际化支持"""
    babel.init_app(app)
    
    @babel.localeselector
    def get_locale():
        """获取当前语言"""
        from flask import request, session
        # 优先使用会话中的语言设置
        if 'language' in session:
            return session['language']
        # 其次使用请求头中的语言设置
        return request.accept_languages.best_match(app.config['LANGUAGES']) or app.config['DEFAULT_LANGUAGE']
