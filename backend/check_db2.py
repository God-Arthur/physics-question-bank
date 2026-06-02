import sqlite3
conn = sqlite3.connect('app/physics.db')
cursor = conn.cursor()

# 检查表结构
cursor.execute('PRAGMA table_info(questions)')
cols = cursor.fetchall()
print('字段数量:', len(cols))
for col in cols:
    print(col[1])

conn.close()
