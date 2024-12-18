import sqlite3

def view_database():
    """Displays all data from the pets_database.db."""
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()

    # Fetch all table names
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()

    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        c.execute(f"SELECT * FROM {table_name}")
        rows = c.fetchall()

        # Fetch column names
        c.execute(f"PRAGMA table_info({table_name});")
        columns = [col[1] for col in c.fetchall()]
        print(" | ".join(columns))  # Print column headers
        print("-" * 40)

        # Print rows
        for row in rows:
            print(row)

    conn.close()

if __name__ == "__main__":
    view_database()

