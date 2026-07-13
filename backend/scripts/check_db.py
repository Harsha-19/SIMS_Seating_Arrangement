from pathlib import Path
import sqlite3

database_path = Path(__file__).resolve().parents[1] / "db.sqlite3"

with sqlite3.connect(database_path) as connection:
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(api_student)")
    columns = cursor.fetchall()

for column in columns:
    print(column)
