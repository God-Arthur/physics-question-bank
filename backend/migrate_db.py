#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'app', 'physics.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute("PRAGMA table_info(questions)")
    columns = [row[1] for row in cursor.fetchall()]

    new_columns = [
        ('score_data_updated', 'BOOLEAN DEFAULT 0'),
        ('total_attempts', 'INTEGER DEFAULT 0'),
        ('total_score_rate', 'FLOAT DEFAULT 0'),
        ('fit_param_a', 'FLOAT'),
        ('fit_param_b', 'FLOAT'),
        ('fit_param_c', 'FLOAT'),
        ('fit_param_d', 'FLOAT'),
        ('last_fitted_at', 'DATETIME')
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE questions ADD COLUMN {col_name} {col_type}")
            print(f"{col_name} added")

    conn.commit()
    print("Done!")
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
#!/usr/bin/env python3
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), 'app', 'physics.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute("PRAGMA table_info(questions)")
    columns = [row[1] for row in cursor.fetchall()]

    new_columns = [
        ('score_data_updated', 'BOOLEAN DEFAULT 0'),
        ('total_attempts', 'INTEGER DEFAULT 0'),
        ('total_score_rate', 'FLOAT DEFAULT 0'),
        ('fit_param_a', 'FLOAT'),
        ('fit_param_b', 'FLOAT'),
        ('fit_param_c', 'FLOAT'),
        ('fit_param_d', 'FLOAT'),
        ('last_fitted_at', 'DATETIME')
    ]

    for col_name, col_type in new_columns:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE questions ADD COLUMN {col_name} {col_type}")
            print(f"{col_name} added")

    conn.commit()
    print("Done!")
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
