import sqlite3
import os
import hashlib

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'physics.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看密码哈希格式
cursor.execute("SELECT id, username, password_hash FROM users WHERE username LIKE '1026%'")
rows = cursor.fetchall()
print(f"Found {len(rows)} accounts:")
for row in rows:
    print(f"  id={row[0]}, username={row[1]}, hash={row[2][:30]}...")

# 查看管理员账号的密码哈希格式作为参考
cursor.execute("SELECT username, password_hash FROM users WHERE role='admin' LIMIT 1")
admin = cursor.fetchone()
if admin:
    print(f"\nAdmin reference: {admin[0]}, hash={admin[1][:50]}...")

conn.close()
