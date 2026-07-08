"""
初始化脚本 - 创建默认管理员账号和机构数据
"""
from app import create_app
from app.utils.database import db
from app.models import User, Institute

# 默认机构列表
DEFAULT_INSTITUTES = [
    {'name': '兰阶', 'code': 'LAN'},
    {'name': '思博楷睿', 'code': 'SBO'},
    {'name': '博知汇', 'code': 'BOZ'},
    {'name': '芝麻', 'code': 'ZHM'},
    {'name': '量子', 'code': 'QUA'},
    {'name': '学而思', 'code': 'XES'},
    {'name': '北大', 'code': 'PKU'},
    {'name': '清华', 'code': 'THU'},
    {'name': '培尖', 'code': 'PJI'},
    {'name': '方圆', 'code': 'FYU'},
    {'name': '爱尖子', 'code': 'AJZ'},
    {'name': '问名师', 'code': 'WMS'},
    {'name': '猿辅导', 'code': 'YFD'},
    {'name': '质心', 'code': 'ZHX'},
    {'name': '厦门一中', 'code': 'XYZ'},
    {'name': '个人', 'code': 'IND'},
]

def init_data():
    app = create_app()
    
    with app.app_context():
        # 先创建所有表
        db.create_all()
        
        # 检查是否已有用户
        if User.query.count() == 0:
            # 创建默认管理员
            admin = User(
                username='admin',
                role='admin',
                real_name='管理员'
            )
            admin.set_password('admin1906')
            db.session.add(admin)
            
            print("默认用户创建完成:")
            print("  管理员: admin / admin1906")
        
        # 检查是否已有机构
        if Institute.query.count() == 0:
            for inst in DEFAULT_INSTITUTES:
                institute = Institute(name=inst['name'], code=inst['code'])
                db.session.add(institute)
            print(f"默认机构创建完成: {len(DEFAULT_INSTITUTES)} 个")
        
        db.session.commit()
        print("初始化完成！")


if __name__ == '__main__':
    init_data()
