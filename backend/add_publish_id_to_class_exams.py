#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'app', 'physics.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # 检查列是否已经存在
    cursor.execute('PRAGMA table_info(class_exams)')
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'publish_id' not in columns:
        # 添加 publish_id 列
        cursor.execute('ALTER TABLE class_exams ADD COLUMN publish_id INTEGER')
        print("publish_id column added to class_exams table!")
    else:
        print("publish_id column already exists in class_exams table")
    
    conn.commit()
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
