import sqlite3
import sys

try:
    conn = sqlite3.connect('physics.db')
    cursor = conn.cursor()
    
    print('Tables:')
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = [row[0] for row in cursor.fetchall()]
    print(tables)
    
    print('\nQuestions schema:')
    cursor.execute('PRAGMA table_info(questions)')
    print([row for row in cursor.fetchall()])
    
    print('\nPaper Publishes schema:')
    cursor.execute('PRAGMA table_info(paper_publishes)')
    print([row for row in cursor.fetchall()])
    
    print('\nClass Exams schema:')
    cursor.execute('PRAGMA table_info(class_exams)')
    print([row for row in cursor.fetchall()])
    
    conn.close()
    print('\nSuccess!')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
