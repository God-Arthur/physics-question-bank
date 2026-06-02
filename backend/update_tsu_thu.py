#!/usr/bin/env python3
"""更新数据库中的TSU为THU"""
from app import create_app
from app.utils.database import db
from app.models import Institute, Question

app = create_app()
with app.app_context():
    # 更新机构表
    institute_count = Institute.query.filter_by(code='TSU').update({'code': 'THU'})
    print(f'更新机构表: {institute_count} 条记录')

    # 更新题目表
    question_count = Question.query.filter_by(source_institute='TSU').update({'source_institute': 'THU'})
    print(f'更新题目表: {question_count} 条记录')

    db.session.commit()
    print('数据库更新完成!')
