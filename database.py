import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Users table for registration and login
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
""")

# Bookings table for facility bookings
cursor.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("Database created successfully!")