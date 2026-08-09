import sqlite3

conn = sqlite3.connect("community.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS discussions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT
)
""")

conn.commit()
conn.close()

print("Discussions table created!")