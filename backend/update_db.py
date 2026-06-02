#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, '/home/redaunt/physics/backend')

from app import create_app
from app.utils.database import db

app = create_app()

with app.app_context():
    print("正在更新数据库...")
    db.create_all()
    print("数据库更新完成！")
