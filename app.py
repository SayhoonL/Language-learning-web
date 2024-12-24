from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import random
import os
from dotenv import load_dotenv
import openai

load_dotenv() 

openai.api_key = os.getenv("OPENAI_API_KEY")
print("OPENAI_API_KEY =>", openai.api_key)

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Session timeout set to 30 minutes

# Database setup

OFFICIAL_DEFINITION = "The process by which green plants use sunlight to synthesize foods from carbon dioxide and water."
WORD = "Photosynthesis"


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

    # Create Items table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Items (
            itemID INTEGER PRIMARY KEY AUTOINCREMENT,
            itemName TEXT NOT NULL,
            description TEXT,
            image_url TEXT,
            price INTEGER NOT NULL
        )
    ''')

    # Create UserItems table to track items owned by users
    c.execute('''
        CREATE TABLE IF NOT EXISTS UserItems (
            userItemID INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            itemID INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (username) REFERENCES Account(username),
            FOREIGN KEY (itemID) REFERENCES Items(itemID)
        )
    ''')

    # Insert default pets with images
    c.execute('''
        INSERT OR IGNORE INTO Pets (petID, petName, image_url)
        VALUES 
        (1, 'charmander', '/static/uploads/pet1.png'),
        (2, 'charmeleon', '/static/uploads/pet2.png'),
        (3, 'charizard', '/static/uploads/pet3.png'),
        (4, 'pikachu', '/static/uploads/pet4.png'),
        (5, 'bulbasaur', '/static/uploads/pet5.png')
    ''')

    # Insert default items
    c.execute('''
        INSERT OR IGNORE INTO Items (itemID, itemName, description, image_url, price)
        VALUES 
        (1, 'Potion', 'Restores 20 health points to a pet', '/static/uploads/item1.png', 10),
        (2, 'Super Potion', 'Restores 50 health points to a pet', '/static/uploads/item2.png', 20),
        (3, 'Revive', 'Revives a fainted pet with 50% health', '/static/uploads/item3.png', 30),
        (4, 'Rare Candy', 'Instantly levels up a pet', '/static/uploads/item4.png', 50),
        (5, 'Berry', 'Slightly increases a pet\'\'s experience', '/static/uploads/item5.png', 5)
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
            c.execute("INSERT INTO Account (username, password, points) VALUES (?, ?, ?)", (username, password, 100))
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

@app.route('/shop')
def shop():
    """Renders the shop page."""
    if not is_logged_in():
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()

    # Fetch all items available in the shop
    c.execute("SELECT itemID, itemName, description, image_url FROM Items")
    items = c.fetchall()
    conn.close()

    # Pass the items to the shop template
    shop_items = [
        {"id": item[0], "name": item[1], "description": item[2], "image_url": item[3]}
        for item in items
    ]
    
    return render_template('shop.html', items=shop_items)

@app.route('/manage_pets')
def manage_pets():
    """Displays the manage pets page."""
    if not is_logged_in():
        return redirect(url_for('login'))

    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()
    c.execute("SELECT petID, petName, image_url FROM Pets")
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
    c.execute("SELECT petID, petName FROM Pets")
    pets = c.fetchall()  # Fetch all pet IDs and names
    print("Available pets:", pets)  # Debug: Check available pets

    if not pets:
        print("No pets available.")  # Debug: No pets available
        return jsonify({'message': 'No pets available to assign.'}), 400

    # Randomly select a pet
    random_pet = random.choice(pets)
    random_pet_id = random_pet[0]
    random_pet_name = random_pet[1]
    print("Selected pet ID and name:", random_pet_id, random_pet_name)  # Debug: Selected pet details

    try:
        # Insert the selected pet into the UserPets table
        c.execute(
            "INSERT INTO UserPets (username, petID, petLevel, expPoints) VALUES (?, ?, 1, 0)",
            (username, random_pet_id)
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        print("Integrity error:", e)  # Debug: Database error
        return jsonify({'message': 'Pet already linked or an error occurred'}), 400
    finally:
        conn.close()

    # Return the pet details
    return jsonify({
        'message': f'Egg hatched! You received a new pet: {random_pet_name}!',
        'petID': random_pet_id,
        'petName': random_pet_name
    }), 200


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
    """Fetches logged-in user's information, including points."""
    if not is_logged_in():
        return jsonify({'error': 'User not logged in'}), 401

    username = session['username']
    conn = sqlite3.connect('pets_database.db') 
    c = conn.cursor()

    c.execute("""
        SELECT username, points 
        FROM Account 
        WHERE username = ?
    """, (username,))
    user_info = c.fetchone()
    conn.close()

    if not user_info:
        return jsonify({'error': 'User not found'}), 404

    user_data = {
        'username': user_info[0],
        'points': user_info[1]
    }
    return jsonify(user_data), 200

@app.route('/update_user', methods=['POST'])
def update_user():
    """Updates logged-in user's information, such as points."""
    # Step 1: Check if the user is logged in
    if not is_logged_in():
        return jsonify({'error': 'User not logged in'}), 401

    username = session.get('username')
    if not username:
        return jsonify({'error': 'Session expired. Please log in again.'}), 401

    # Step 2: Parse and validate request data
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request data: No JSON received'}), 400

    points = data.get('points')
    if points is None:
        return jsonify({'error': 'Points value is required'}), 400

    try:
        # Step 3: Connect to the database
        conn = sqlite3.connect('pets_database.db')
        c = conn.cursor()

        # Step 4: Update the user's points in the Account table
        c.execute("""
            UPDATE Account
            SET points = ?
            WHERE username = ?
        """, (points, username))
        conn.commit()

        # Step 5: Check if any rows were updated
        if c.rowcount == 0:
            return jsonify({'error': 'User not found or no changes made'}), 404
    except sqlite3.Error as e:
        # Step 6: Handle database errors
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

    # Step 7: Return success response
    return jsonify({'message': 'User information updated successfully'}), 200



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
        SELECT p.petName, p.image_url, up.expPoints, up.petLevel 
        FROM UserPets up 
        JOIN Pets p ON up.petID = p.petID 
        WHERE up.userPetID = ? AND up.username = ?
    """, (pet_id, username))
    pet = c.fetchone()
    conn.close()

    if pet:
        return jsonify({'pet': {'name': pet[0], 'image_url': pet[1], 'exp': pet[2], 'level': pet[3]}}), 200
    return jsonify({'error': 'Pet not found'}), 404

@app.route('/feed_pet', methods=['POST'])
def feed_pet():
    """Handles feeding an item to a pet."""
    if not is_logged_in():
        return jsonify({'error': 'User not logged in'}), 401

    data = request.json
    pet_id = data.get('petID')
    item_id = data.get('itemID')

    if not pet_id or not item_id:
        return jsonify({'error': 'Pet ID and Item ID are required'}), 400

    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()

    # Check if the user owns the item
    c.execute("""
        SELECT quantity 
        FROM UserItems 
        WHERE username = ? AND itemID = ?
    """, (username, item_id))
    item = c.fetchone()

    if not item or item[0] <= 0:
        conn.close()
        return jsonify({'error': 'You do not own this item or are out of stock'}), 400

    # Reduce item quantity
    c.execute("""
        UPDATE UserItems 
        SET quantity = quantity - 1 
        WHERE username = ? AND itemID = ?
    """, (username, item_id))

    # Get item effects (e.g., exp boost)
    c.execute("SELECT itemName FROM Items WHERE itemID = ?", (item_id,))
    item_name = c.fetchone()[0]

    exp_gain = 0
    if item_name == 'Potion':
        exp_gain = 10
    elif item_name == 'Berry':
        exp_gain = 5
    elif item_name == 'Rare Candy':
        exp_gain = 100  # Level up directly
    # Add more item effects as needed

    # Update pet's experience points and handle leveling up
    c.execute("""
        SELECT expPoints, petLevel 
        FROM UserPets 
        WHERE userPetID = ? AND username = ?
    """, (pet_id, username))
    pet = c.fetchone()

    if not pet:
        conn.close()
        return jsonify({'error': 'Pet not found'}), 404

    new_exp = pet[0] + exp_gain
    new_level = pet[1]

    if new_exp >= 100:
        new_level += 1
        new_exp -= 100  # Reset experience after leveling up

    c.execute("""
        UPDATE UserPets 
        SET expPoints = ?, petLevel = ? 
        WHERE userPetID = ? AND username = ?
    """, (new_exp, new_level, pet_id, username))

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'newExp': new_exp,
        'newLevel': new_level,
        'message': f"{item_name} was successfully used!"
    }), 200


@app.route('/get_shop_items', methods=['GET'])
def get_shop_items():
    """Fetches all items available in the shop, including prices."""
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()
    c.execute("SELECT itemID, itemName, description, image_url, price FROM Items")
    items = c.fetchall()
    conn.close()

    # Include price in the response
    items_list = [
        {
            'id': item[0],
            'name': item[1],
            'description': item[2],
            'image_url': item[3],
            'price': item[4]
        }
        for item in items
    ]
    return jsonify({'items': items_list}), 200


@app.route('/purchase_item', methods=['POST'])
def purchase_item():
    """Handles purchasing an item."""
    if not is_logged_in():
        return jsonify({'message': 'User not logged in'}), 401

    data = request.json
    item_id = data.get('itemID')
    username = session['username']

    if not item_id:
        return jsonify({'message': 'Item ID is required'}), 400

    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()

    # Check if the user has enough points
    c.execute("SELECT points FROM Account WHERE username = ?", (username,))
    user_points = c.fetchone()
    if not user_points or user_points[0] < 10:  # Example: Assume all items cost 10 points
        conn.close()
        return jsonify({'message': 'Not enough points to purchase this item'}), 400

    # Deduct points and add item to user's inventory
    c.execute("UPDATE Account SET points = points - 10 WHERE username = ?", (username,))
    c.execute("INSERT INTO UserItems (username, itemID) VALUES (?, ?)", (username, item_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True}), 200

@app.route('/get_user_items', methods=['GET'])
def get_user_items():
    """Fetches items owned by the logged-in user."""
    if not is_logged_in():
        return jsonify({'error': 'User not logged in'}), 401

    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()
    c.execute("""
        SELECT ui.userItemID, ui.itemID, i.itemName, i.image_url
        FROM UserItems ui
        JOIN Items i ON ui.itemID = i.itemID
        WHERE ui.username = ?
    """, (username,))
    items = c.fetchall()
    conn.close()

    # Map fetched data to the expected JSON structure
    items_list = [{'userItemID': item[0], 'itemID': item[1], 'name': item[2], 'image_url': item[3]} for item in items]
    return jsonify({'items': items_list}), 200


@app.route('/delete_item', methods=['POST'])
def delete_item():
    """Deletes an item linked to the logged-in user by userItemID."""
    if not is_logged_in():
        return jsonify({'message': 'User not logged in'}), 401

    data = request.json
    user_item_id = data.get('userItemID')  # Expecting userItemID from the frontend

    if not user_item_id:
        return jsonify({'message': 'userItemID is required'}), 400

    username = session['username']
    conn = sqlite3.connect('pets_database.db')
    c = conn.cursor()

    try:
        # Delete the item based on userItemID and username
        c.execute("DELETE FROM UserItems WHERE userItemID = ? AND username = ?", (user_item_id, username))
        conn.commit()
    except Exception as e:
        return jsonify({'message': 'Error deleting item', 'error': str(e)}), 500
    finally:
        conn.close()

    return jsonify({'message': 'Item deleted successfully!', 'userItemID': user_item_id}), 200

@app.route("/check-definition", methods=["POST"])
def check_definition():
    try:
        data = request.get_json()
        user_definition = data.get("userDefinition", "")

        # Updated system instruction:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a strict vocabulary teacher. "
                    "I will provide: "
                    "1) a word, "
                    "2) its official definition, and "
                    "3) the student's definition. "
                    "You must decide if the student's definition matches "
                    "the essential meaning of the official definition. "
                    "Respond in the following format:\n\n"
                    "Correctness: Yes or No\n"
                    "Explanation: [brief explanation]\n\n"
                    "Be concise."
                )
            },
            {
                "role": "user",
                "content": (
                    f'Word: "{WORD}"\n'
                    f'Official Definition: "{OFFICIAL_DEFINITION}"\n'
                    f'Student\'s Definition: "{user_definition}"'
                )
            }
        ]

        # Call OpenAI (using the old ChatCompletion or new Chat interface)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=60,
            temperature=0.0
        )

        response_text = response.choices[0]["message"]["content"].strip()
        print("ChatGPT raw answer:", response_text)

        # Parse the response
        lines = response_text.splitlines()
        correctness_line = None
        explanation_line = None

        for line in lines:
            if line.lower().startswith("correctness:"):
                correctness_line = line
            elif line.lower().startswith("explanation:"):
                explanation_line = line

        is_correct = False
        explanation = ""

        if correctness_line:
            # e.g. "Correctness: Yes" => "Yes"
            correctness_value = correctness_line.split(":", 1)[1].strip()
            is_correct = (correctness_value.lower() == "yes")

        if explanation_line:
            # e.g. "Explanation: The student left out carbon dioxide..."
            explanation = explanation_line.split(":", 1)[1].strip()

        return jsonify({
            "correct": is_correct,
            "modelAnswer": "Yes" if is_correct else "No",
            "explanation": explanation
        })

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Something went wrong"}), 500

@app.route('/logout')
def logout():
    """Logs out the user."""
    session.pop('username', None)
    flash('You have been logged out successfully!', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
