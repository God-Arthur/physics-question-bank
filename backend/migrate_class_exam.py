#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'app', 'physics.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # 创建 class_exams 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS class_exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            paper_id INTEGER,
            paper_title VARCHAR(200) NOT NULL,
            paper_total_score INTEGER DEFAULT 0,
            paper_difficulty FLOAT DEFAULT 0,
            exam_date DATE,
            start_time VARCHAR(10),
            end_time VARCHAR(10),
            questions_snapshot TEXT,
            scores_snapshot TEXT,
            finished_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_by INTEGER,
            FOREIGN KEY (class_id) REFERENCES classes (id),
            FOREIGN KEY (paper_id) REFERENCES papers (id),
            FOREIGN KEY (finished_by) REFERENCES users (id)
        )
    ''')
    print("class_exams table created")

    conn.commit()
    print("Done!")
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
