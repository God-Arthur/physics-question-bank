#!/usr/bin/env python3
import sqlite3
import os

# 检查 app 目录下的数据库
db_path = os.path.join(os.path.dirname(__file__), 'app', 'physics.db')
print(f'Checking database at: {db_path}')
print(f'File exists: {os.path.exists(db_path)}')
print(f'File size: {os.path.getsize(db_path) if os.path.exists(db_path) else 0}')

if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print('\n=== Tables ===')
    c.execute('SELECT name FROM sqlite_master WHERE type="table"')
    for t in c.fetchall():
        print(f'  {t[0]}')
    
    print('\n=== Users ===')
    c.execute('SELECT id, username, role FROM users')
    for u in c.fetchall():
        print(f'  ID: {u[0]}, Username: {u[1]}, Role: {u[2]}')
    
    conn.close()
else:
    print('Database is empty or does not exist!')