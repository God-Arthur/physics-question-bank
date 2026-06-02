#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'app', 'physics.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    print("=== Fixing Database ===")

    # 1. Add 'year' column to questions table if missing
    cursor.execute('PRAGMA table_info(questions)')
    columns = [row[1] for row in cursor.fetchall()]
    if 'year' not in columns:
        cursor.execute('ALTER TABLE questions ADD COLUMN year INTEGER')
        print("Added 'year' column to questions table")
    else:
        print("'year' column already exists in questions table")

    # 2. Add 'source_institute' column to questions table if missing
    if 'source_institute' not in columns:
        cursor.execute('ALTER TABLE questions ADD COLUMN source_institute VARCHAR(3)')
        print("Added 'source_institute' column to questions table")
    else:
        print("'source_institute' column already exists in questions table")

    # 3. Add 'author' column to questions table if missing
    if 'author' not in columns:
        cursor.execute('ALTER TABLE questions ADD COLUMN author VARCHAR(50)')
        print("Added 'author' column to questions table")
    else:
        print("'author' column already exists in questions table")

    # 4. Remove unique constraint from paper_publishes (if exists)
    print("\nChecking paper_publishes table...")
    cursor.execute('PRAGMA table_info(paper_publishes)')
    pp_columns = [row[1] for row in cursor.fetchall()]

    cursor.execute('PRAGMA index_list(paper_publishes)')
    indexes = cursor.fetchall()
    unique_index_name = None
    for idx in indexes:
        if idx[2] == 1:  # unique index
            unique_index_name = idx[1]
            break

    if unique_index_name:
        print(f"Found unique index: {unique_index_name}")
        # Recreate table without unique constraint
        cursor.execute('''
            CREATE TABLE paper_publishes_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER NOT NULL,
                class_id INTEGER NOT NULL,
                published_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                published_by INTEGER,
                FOREIGN KEY (paper_id) REFERENCES papers (id),
                FOREIGN KEY (class_id) REFERENCES classes (id),
                FOREIGN KEY (published_by) REFERENCES users (id)
            )
        ''')
        cursor.execute('''
            INSERT INTO paper_publishes_new (id, paper_id, class_id, published_at, published_by)
            SELECT id, paper_id, class_id, published_at, published_by FROM paper_publishes
        ''')
        cursor.execute('DROP TABLE paper_publishes')
        cursor.execute('ALTER TABLE paper_publishes_new RENAME TO paper_publishes')
        print("Removed unique constraint from paper_publishes table")
    else:
        print("No unique constraint on paper_publishes table")

    # 5. Add publish_id column to class_exams table
    print("\nChecking class_exams table...")
    cursor.execute('PRAGMA table_info(class_exams)')
    ce_columns = [row[1] for row in cursor.fetchall()]
    if 'publish_id' not in ce_columns:
        cursor.execute('ALTER TABLE class_exams ADD COLUMN publish_id INTEGER')
        print("Added 'publish_id' column to class_exams table")
    else:
        print("'publish_id' column already exists in class_exams table")

    conn.commit()
    print("\n=== Database Fix Complete ===")

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
    import traceback
    traceback.print_exc()
finally:
    conn.close()
