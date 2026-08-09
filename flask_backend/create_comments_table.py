import sqlite3

conn = sqlite3.connect("community.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS comments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discussion_id INTEGER,
    comment TEXT
)
""")

conn.commit()
conn.close()

print("Comments table created!")