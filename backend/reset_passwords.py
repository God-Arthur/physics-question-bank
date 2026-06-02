import sqlite3
import os
import sys

# 添加 app 路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

from werkzeug.security import generate_password_hash

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'physics.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查询所有 1026 开头的账号
cursor.execute("SELECT id, username FROM users WHERE username LIKE '1026%'")
rows = cursor.fetchall()
print(f"Resetting passwords for {len(rows)} accounts...")

for uid, username in rows:
    new_password = username  # 初始密码等于账号名
    new_hash = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, uid))
    print(f"  {username} -> password: {new_password}")

conn.commit()
conn.close()
print("\nDone! All passwords reset to match username.")
