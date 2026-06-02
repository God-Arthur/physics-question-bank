#!/usr/bin/env python3
import os
import sqlite3

# Get DB path correctly
database_py_dir = os.path.join(os.path.dirname(__file__), 'app', 'utils')
db_path = os.path.join(os.path.dirname(database_py_dir), 'physics.db')
print(f"Database path: {db_path}\n")

# Connect to DB
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:")
for (table_name,) in tables:
    print(f"\n=== Table: {table_name} ===")
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]}: {col[2]}")

conn.close()
