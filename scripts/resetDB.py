import os
import sqlite3

def reset_database():
    db_name = "users.db"  # Name of the database file

    # Step 1: Delete the existing database if it exists
    if os.path.exists(db_name):
        os.remove(db_name)
        print(f"Existing database '{db_name}' has been deleted.")
    else:
        print(f"No database named '{db_name}' found.")

    # Step 2: Recreate the database and its schema
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Create the 'users' table with columns for username, password, and points
    c.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            points INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

    print(f"New database '{db_name}' has been initialized with the 'users' table.")

if __name__ == "__main__":
    reset_database()
