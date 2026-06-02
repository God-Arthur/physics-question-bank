#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'app', 'physics.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS paper_publishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            published_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            published_by INTEGER,
            FOREIGN KEY (paper_id) REFERENCES papers (id),
            FOREIGN KEY (class_id) REFERENCES classes (id),
            FOREIGN KEY (published_by) REFERENCES users (id),
            UNIQUE(paper_id, class_id)
        )
    ''')
    print("paper_publishes table created")

    conn.commit()
    print("Done!")
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
