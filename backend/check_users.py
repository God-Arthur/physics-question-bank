#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('physics.db')
c = conn.cursor()

print('=== Users in database ===')
c.execute('SELECT id, username, role, password_hash FROM users')
for row in c.fetchall():
    print(f'ID: {row[0]}, Username: {row[1]}, Role: {row[2]}, Password Hash: {row[3][:20]}...')

conn.close()