from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Session expires after 30 seconds for testing

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    points INTEGER DEFAULT 0
                )''')
    conn.commit()
    conn.close()

# Helper function to check if user is logged in
def is_logged_in():
    return 'username' in session

@app.before_request
def enforce_session_timeout():
    """Check if the session has expired and log the user out if needed."""
    session.permanent = True  # Use permanent session to respect PERMANENT_SESSION_LIFETIME
    if 'username' in session:
        session.modified = True  # Update session activity timestamp

@app.route('/')
def home():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    username = session['username']
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT points FROM users WHERE username = ?", (username,))
    points = c.fetchone()[0]
    conn.close()
    return render_template('index.html', username=username, points=points)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()
        if row and check_password_hash(row[0], password):
            session['username'] = username
            session.permanent = True  # Set session as permanent to enable timeout
            return redirect(url_for('home'))
        return "Invalid credentials!"
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, points) VALUES (?, ?, ?)", (username, password, 100))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Username already exists"
        finally:
            conn.close()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/game1')
def game1():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('game1.html')

@app.route('/game2')
def game2():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('game2.html')

@app.route('/get_points', methods=['GET'])
def get_points():
    username = session.get('username')  # Get the logged-in user's username

    if username:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT points FROM users WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()

        if row:
            return {'points': row[0]}, 200  # Return points as JSON
    return {'error': 'User not found or not logged in'}, 400


@app.route('/update_points', methods=['POST'])
def update_points():
    username = session.get('username')  # Get the logged-in user's username
    new_points = request.json.get('points')  # Get the new points from the request

    if username and new_points is not None:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET points = ? WHERE username = ?", (new_points, username))
        conn.commit()
        conn.close()
        return {'success': True}, 200
    return {'error': 'Invalid request'}, 400


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged off successfully!', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
