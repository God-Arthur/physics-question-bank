import sqlite3
conn = sqlite3.connect('app/physics.db')
cursor = conn.cursor()
cursor.execute('SELECT id, content, answer FROM questions LIMIT 3')
for row in cursor.fetchall():
    print(f'ID: {row[0]}')
    print(f'content: {repr(row[1][:100] if row[1] else None)}')
    print(f'answer: {repr(row[2][:100] if row[2] else None)}')
    print('---')
conn.close()
