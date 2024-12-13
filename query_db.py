import sqlite3

def view_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()

    for user in users:
        print(f"ID: {user[0]}, Username: {user[1]}, Points: {user[3]}")

if __name__ == "__main__":
    view_users()
