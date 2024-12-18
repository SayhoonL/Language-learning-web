from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Session timeout set to 30 minutes

# Database setup

def init_db():
    """Initializes the database with the required tables and seed data."""
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()

    # Create Account table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Account (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            userLevel INTEGER DEFAULT 1
        )
    ''')

    # Create Pets table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Pets (
            petID INTEGER PRIMARY KEY,
            petName TEXT NOT NULL,
            image_url TEXT
        )
    ''')

    # Create UserPets table
    c.execute('''
        CREATE TABLE IF NOT EXISTS UserPets (
            userPetID INTEGER PRIMARY KEY AUTOINCREMENT,
            petID INTEGER NOT NULL,
            username TEXT NOT NULL,
            petLevel INTEGER DEFAULT 1,
            expPoints INTEGER DEFAULT 0,
            FOREIGN KEY (username) REFERENCES Account(username),
            FOREIGN KEY (petID) REFERENCES Pets(petID)
        )
    ''')

    # Insert default pets with image URLs
    c.execute('''
        INSERT OR IGNORE INTO Pets (petID, petName, image_url) 
        VALUES 
        (1, 'charmander', '/static/uploads/pet1.png'),
        (2, 'charmeleon', '/static/uploads/pet2.png'),
        (3, 'charizard', '/static/uploads/pet3.png'),
        (4, 'pikachu', '/static/uploads/pet4.png'),
        (5, 'sayhoon', '/static/uploads/pet5.png')
    ''')

    conn.commit()
    conn.close()

# Helper function

def is_logged_in():
    """Checks if the user is logged in."""
    return 'username' in session

@app.before_request
def enforce_session_timeout():
    """Enforce session timeout for every request."""
    session.permanent = True
    if 'username' in session:
        session.modified = True

# Routes

@app.route('/')
def home():
    """Home page displaying user information if logged in."""
    if not is_logged_in():
        return redirect(url_for('login'))

    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()
    c.execute("SELECT points FROM Account WHERE username = ?", (username,))
    user_data = c.fetchone()
    conn.close()

    if user_data:
        points = user_data[0]
        return render_template('index.html', username=username, points=points)
    return "User not found."

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('pets_database.db')
        c = conn.cursor()
        c.execute("SELECT password FROM Account WHERE username = ?", (username,))
        row = c.fetchone()
        conn.close()

        if row and check_password_hash(row[0], password):
            session['username'] = username
            session.permanent = True
            return redirect(url_for('home'))
        flash("Invalid username or password!", 'danger')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles user registration."""
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        conn = sqlite3.connect('pets_database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO Account (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Username already exists!", 'danger')
            return redirect(url_for('signup'))
        finally:
            conn.close()

        flash("Account created successfully!", 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/lobby')
def lobby():
    """Displays the game lobby."""
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('lobby.html')

@app.route('/games')
def games():
    """Renders the main games page that includes all games."""
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('games.html')

@app.route('/game<int:game_id>')
def game(game_id):
    """Handles routing for individual games."""
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template(f'game{game_id}.html')

@app.route('/pet')
def pet():
    """Renders the pet details page."""
    if not is_logged_in():
        return redirect(url_for('login'))
    
    pet_id = request.args.get('id')  # Get the pet ID from the query parameters
    if not pet_id:
        return "Pet ID not specified!", 400
    
    return render_template('pet.html', pet_id=pet_id)

@app.route('/manage_pets')
def manage_pets():
    """Displays the manage pets page."""
    if not is_logged_in():
        return redirect(url_for('login'))

    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()
    c.execute("SELECT petID, petName FROM Pets")
    pets = c.fetchall()
    conn.close()

    return render_template('manage_pets.html', username=username, pets=pets)

@app.route('/get_egg', methods=['POST'])
def get_egg():
    """Randomly assigns a pet to the user from the available pets."""
    if not is_logged_in():
        return jsonify({'message': 'User not logged in'}), 401

    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()

    # Get all available pet IDs
    c.execute("SELECT petID FROM Pets")
    pet_ids = [row[0] for row in c.fetchall()]
    print("Available pet IDs:", pet_ids)  # Debug: Check pet IDs

    if not pet_ids:
        print("No pets available.")  # Debug: No pets available
        return jsonify({'message': 'No pets available to assign.'}), 400

    # Randomly select a pet ID
    random_pet_id = random.choice(pet_ids)
    print("Selected pet ID:", random_pet_id)  # Debug: Selected pet ID

    try:
        c.execute("INSERT INTO UserPets (username, petID, petLevel, expPoints) VALUES (?, ?, 1, 0)", (username, random_pet_id))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print("Integrity error:", e)  # Debug: Database error
        return jsonify({'message': 'Pet already linked or an error occurred'}), 400
    finally:
        conn.close()

    return jsonify({'message': 'Egg hatched! You received a new pet!', 'petID': random_pet_id}), 200

@app.route('/link_pet', methods=['POST'])
def link_pet():
    """Links a pet to a user."""
    if not is_logged_in():
        return jsonify({'message': 'User not logged in'}), 401

    data = request.json
    username = session['username']
    pet_id = data.get('petID')

    if not pet_id:
        return jsonify({'message': 'Pet ID is required'}), 400

    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO UserPets (username, petID, petLevel, expPoints) VALUES (?, ?, 1, 0)", (username, pet_id))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Pet already linked or invalid data'}), 400
    finally:
        conn.close()

    return jsonify({'message': 'Pet linked successfully!', 'username': username, 'petID': pet_id}), 200

@app.route('/delete_pet', methods=['POST'])
def delete_pet():
    """Deletes a pet linked to the logged-in user."""
    if not is_logged_in():
        return jsonify({'message': 'User not logged in'}), 401

    data = request.json
    pet_id = data.get('petID')

    if not pet_id:
        return jsonify({'message': 'Pet ID is required'}), 400

    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()

    try:
        c.execute("DELETE FROM UserPets WHERE userPetID = ? AND username = ?", (pet_id, username))
        conn.commit()
    except Exception as e:
        return jsonify({'message': 'Error deleting pet', 'error': str(e)}), 500
    finally:
        conn.close()

    return jsonify({'message': 'Pet deleted successfully!', 'petID': pet_id}), 200

@app.route('/get_user_info', methods=['GET'])
def get_user_info():
    """Fetches logged-in user's information."""
    if not is_logged_in():
        return jsonify({'error': 'User not logged in'}), 401

    username = session['username']
    return jsonify({'username': username}), 200

@app.route('/get_user_pets', methods=['GET'])
def get_user_pets():
    """Fetches pets linked to the logged-in user."""
    if not is_logged_in():
        return jsonify({'error': 'User not logged in'}), 401

    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()
    c.execute("""
        SELECT up.userPetID, p.petName, up.petLevel, up.expPoints, p.image_url 
        FROM UserPets up 
        JOIN Pets p ON up.petID = p.petID 
        WHERE up.username = ?
    """, (username,))
    user_pets = c.fetchall()
    conn.close()

    pets = [{'id': pet[0], 'name': pet[1], 'level': pet[2], 'exp': pet[3], 'image_url': pet[4]} for pet in user_pets]
    return jsonify({'pets': pets}), 200

@app.route('/get_pet_details', methods=['GET'])
def get_pet_details():
    """Fetches details for a specific pet."""
    if not is_logged_in():
        return jsonify({'error': 'User not logged in'}), 401

    pet_id = request.args.get('id')
    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()
    c.execute("""
        SELECT p.petName, p.image_url, up.expPoints 
        FROM UserPets up 
        JOIN Pets p ON up.petID = p.petID 
        WHERE up.userPetID = ? AND up.username = ?
    """, (pet_id, username))
    pet = c.fetchone()
    conn.close()

    if pet:
        return jsonify({'pet': {'name': pet[0], 'image_url': pet[1], 'exp': pet[2]}}), 200
    return jsonify({'error': 'Pet not found'}), 404

@app.route('/feed_pet', methods=['POST'])
def feed_pet():
    """Increases the experience points of a specific pet."""
    if not is_logged_in():
        return jsonify({'error': 'User not logged in'}), 401

    pet_id = request.args.get('id')
    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()
    c.execute("""
        SELECT expPoints FROM UserPets 
        WHERE userPetID = ? AND username = ?
    """, (pet_id, username))
    pet = c.fetchone()

    if not pet:
        conn.close()
        return jsonify({'error': 'Pet not found'}), 404

    new_exp = pet[0] + 10  # Add 10 exp points
    c.execute("""
        UPDATE UserPets 
        SET expPoints = ? 
        WHERE userPetID = ? AND username = ?
    """, (new_exp, pet_id, username))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'newExp': new_exp}), 200




@app.route('/logout')
def logout():
    """Logs out the user."""
    session.pop('username', None)
    flash('You have been logged out successfully!', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
