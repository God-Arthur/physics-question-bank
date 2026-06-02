#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/redaunt/physics/backend')

from app import create_app
from app.utils.database import db

app = create_app()

with app.app_context():
    try:
        # 尝试查询 papers 表
        from app.models import Paper
        papers = Paper.query.all()
        print(f"Papers table OK, count: {len(papers)}")
        
        # 检查是否有 review_status 列
        if hasattr(Paper, 'review_status'):
            print("review_status column exists")
        else:
            print("ERROR: review_status column missing")
            
        # 检查是否有 needs_review 列
        if hasattr(Paper, 'needs_review'):
            print("needs_review column exists")
        else:
            print("ERROR: needs_review column missing")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
