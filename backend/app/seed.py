"""默认管理员和机构数据。启动时缺什么补什么，不覆盖已有账号。"""
from sqlalchemy.exc import IntegrityError

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


def ensure_seed_data():
    from app.models import Institute, User
    from app.utils.database import db

    if User.query.filter_by(username='admin').first() is None:
        admin = User(
            username='admin',
            role='admin',
            real_name='管理员',
            password_changed=False,
        )
        admin.set_password('admin1906')
        db.session.add(admin)

    if Institute.query.count() == 0:
        for inst in DEFAULT_INSTITUTES:
            db.session.add(Institute(name=inst['name'], code=inst['code']))

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
