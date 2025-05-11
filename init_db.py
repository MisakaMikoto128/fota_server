"""
初始化数据库脚本
用于创建数据库表和初始化基本数据
"""

import os
import sys
from datetime import datetime
from flask import Flask
from models import db, User, Role, Project
from config import config

def init_database():
    """初始化数据库"""
    # 创建应用
    app = Flask(__name__)
    app.config.from_object(config['development'])
    
    # 初始化数据库
    db.init_app(app)
    
    with app.app_context():
        # 创建所有表
        db.create_all()
        
        # 初始化角色
        if not Role.query.first():
            Role.insert_roles()
            print("已初始化角色")
        
        # 创建管理员账户
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                name='管理员',
                is_admin=True
            )
            admin.set_password('admin123')  # 默认密码，生产环境应修改
            db.session.add(admin)
            db.session.commit()
            print("已创建默认管理员账户")
        
        # 创建默认项目
        if not Project.query.first():
            default_project = Project(
                name='默认项目',
                description='系统自动创建的默认项目',
                project_key=Project.generate_project_key(),
                created_by_id=User.query.filter_by(username='admin').first().id
            )
            db.session.add(default_project)
            
            # 将管理员添加到默认项目
            admin_user = User.query.filter_by(username='admin').first()
            default_project.users.append(admin_user)
            
            db.session.commit()
            print("已创建默认项目")
        
        print("数据库初始化完成")

if __name__ == '__main__':
    # 检查是否存在 --force 参数
    force = False
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        force = True
    
    # 检查数据库文件是否存在
    db_file = 'fota.db'
    if os.path.exists(db_file) and not force:
        print(f"警告: 数据库文件 {db_file} 已存在。")
        response = input("是否继续初始化数据库？这将清除所有现有数据。(y/n): ")
        if response.lower() != 'y':
            print("操作已取消")
            sys.exit(0)
        
        # 删除现有数据库文件
        os.remove(db_file)
        print(f"已删除现有数据库文件 {db_file}")
    
    # 初始化数据库
    init_database()
