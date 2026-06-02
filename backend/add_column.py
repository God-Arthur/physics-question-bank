import sqlite3
conn = sqlite3.connect('physics.db')
cursor = conn.cursor()

# 添加 question_title 字段
try:
    cursor.execute('ALTER TABLE questions ADD COLUMN question_title VARCHAR(200)')
    print('已添加 question_title 字段')
except Exception as e:
    print(f'添加字段失败: {e}')

conn.commit()
conn.close()
