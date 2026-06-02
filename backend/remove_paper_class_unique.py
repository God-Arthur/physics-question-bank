#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'app', 'physics.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # 1. 创建一个没有唯一约束的临时表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_publishes_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            published_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            published_by INTEGER,
            FOREIGN KEY (paper_id) REFERENCES papers (id),
            FOREIGN KEY (class_id) REFERENCES classes (id),
            FOREIGN KEY (published_by) REFERENCES users (id)
        )
    ''')
    
    # 2. 复制数据到新表
    cursor.execute('''
        INSERT INTO paper_publishes_new (id, paper_id, class_id, published_at, published_by)
        SELECT id, paper_id, class_id, published_at, published_by FROM paper_publishes
    ''')
    
    # 3. 删除旧表
    cursor.execute('DROP TABLE paper_publishes')
    
    # 4. 重命名新表
    cursor.execute('ALTER TABLE paper_publishes_new RENAME TO paper_publishes')
    
    conn.commit()
    print("Unique constraint removed from paper_publishes table!")
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
