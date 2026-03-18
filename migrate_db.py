
import sqlite3
import os

db_path = "scholar_agent.db"
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Check if column already exists
        cursor.execute("PRAGMA table_info(projects)")
        columns = [col[1] for col in cursor.fetchall()]
        if "user_metrics" not in columns:
            print("Adding 'user_metrics' column to 'projects' table...")
            cursor.execute("ALTER TABLE projects ADD COLUMN user_metrics TEXT DEFAULT ''")
            conn.commit()
            print("Column added successfully.")
        else:
            print("'user_metrics' column already exists.")
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")
else:
    print(f"Database {db_path} not found.")
