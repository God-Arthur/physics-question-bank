#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('physics.db')
c = conn.cursor()

print('=== Tables in database ===')
c.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = c.fetchall()
print('Tables:', tables)

conn.close()