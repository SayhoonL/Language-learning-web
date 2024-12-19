import sqlite3

def view_database():
    """Displays all tables and their data from the pets_database.db."""
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()

    # Fetch all table names
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()

    if not tables:
        print("No tables found in the database.")
        conn.close()
        return

    for table in tables:
        table_name = table[0]
        print(f"\n=== Table: {table_name} ===")

        # Fetch column names
        c.execute(f"PRAGMA table_info({table_name});")
        columns = [col[1] for col in c.fetchall()]
        if columns:
            print(" | ".join(columns))  # Print column headers
            print("-" * 40)
        else:
            print("No columns found.")

        # Fetch rows
        c.execute(f"SELECT * FROM {table_name}")
        rows = c.fetchall()

        if rows:
            for row in rows:
                print(row)
        else:
            print("No data found in this table.")

    conn.close()

if __name__ == "__main__":
    view_database()
