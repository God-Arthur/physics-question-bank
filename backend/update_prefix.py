import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'physics.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看所有 1024 开头的账号
cursor.execute("SELECT id, username, password_hash FROM users WHERE username LIKE '1024%'")
rows = cursor.fetchall()
print(f"Found {len(rows)} accounts with 1024 prefix:")
for row in rows:
    print(f"  id={row[0]}, username={row[1]}")

# 更新用户名 1024 -> 1026
cursor.execute("UPDATE users SET username = REPLACE(username, '1024', '1026') WHERE username LIKE '1024%'")
print(f"\nUpdated {cursor.rowcount} usernames from 1024 to 1026")

# 更新密码哈希中包含的 1024（bcrypt 哈希中可能包含 1024 子串，但不应替换）
# 密码哈希是加密的，不需要修改，只需要修改明文密码相关的记录

conn.commit()

# 验证
cursor.execute("SELECT id, username FROM users WHERE username LIKE '1026%'")
rows = cursor.fetchall()
print(f"\nNow {len(rows)} accounts with 1026 prefix:")
for row in rows:
    print(f"  id={row[0]}, username={row[1]}")

# 检查是否还有 1024 的
cursor.execute("SELECT COUNT(*) FROM users WHERE username LIKE '1024%'")
remaining = cursor.fetchone()[0]
print(f"\nRemaining 1024 accounts: {remaining}")

conn.close()
print("\nDone!")
