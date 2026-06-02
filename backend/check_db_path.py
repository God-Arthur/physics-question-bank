#!/usr/bin/env python3
import os

# Calculate the path the same way database.py does
script_dir = os.path.abspath(__file__)  # This file
app_utils_dir = os.path.dirname(os.path.join(os.path.dirname(__file__), 'app', 'utils', 'database.py'))  # No, let's do it exactly like database.py
database_py_dir = os.path.join(os.path.dirname(__file__), 'app', 'utils')
db_path = os.path.join(os.path.dirname(database_py_dir), 'physics.db')
print("Calculated DB path:", db_path)
print("Is file?", os.path.isfile(db_path))
print("File size:", os.path.getsize(db_path) if os.path.isfile(db_path) else "N/A")
