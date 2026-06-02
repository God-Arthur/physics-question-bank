#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'app', 'physics.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=== Questions Table Schema ===")
cursor.execute('PRAGMA table_info(questions)')
for row in cursor.fetchall():
    print(row)

print("\n=== Paper Publishes Table Schema ===")
cursor.execute('PRAGMA table_info(paper_publishes)')
for row in cursor.fetchall():
    print(row)

print("\n=== Class Exams Table Schema ===")
cursor.execute('PRAGMA table_info(class_exams)')
for row in cursor.fetchall():
    print(row)

conn.close()
