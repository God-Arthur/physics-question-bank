#!/usr/bin/env python3
import sqlite3
import os
from werkzeug.security import check_password_hash, generate_password_hash

db_path = os.path.join(os.path.dirname(__file__), 'app', 'physics.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('SELECT id, username, password_hash FROM users WHERE username="admin"')
row = c.fetchone()
if row:
    print(f'Admin user found: ID={row[0]}, Username={row[1]}')
    print(f'Password hash: {row[2]}')
    
    # 测试密码验证
    result = check_password_hash(row[2], 'admin1906')
    print(f'Password check result: {result}')
    
    # 如果验证失败，重新设置密码
    if not result:
        print('\nPassword hash is invalid. Resetting...')
        new_hash = generate_password_hash('admin1906')
        c.execute('UPDATE users SET password_hash=? WHERE username="admin"', (new_hash,))
        conn.commit()
        print(f'New hash: {new_hash}')
        
        # 再次验证
        result2 = check_password_hash(new_hash, 'admin1906')
        print(f'New password check result: {result2}')

conn.close()