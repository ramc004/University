from flask import Flask, request, jsonify
from email.message import EmailMessage
import smtplib
import sqlite3
import hashlib
import os
from datetime import datetime

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Bulbs table - UPDATED with is_simulated column
    c.execute('''
        CREATE TABLE IF NOT EXISTS bulbs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            bulb_id TEXT NOT NULL,
            bulb_name TEXT NOT NULL,
            room_name TEXT,
            is_simulated INTEGER DEFAULT 0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email),
            UNIQUE(user_email, bulb_id)
        )
    ''')
    
    # Add is_simulated column to existing tables (migration)
    try:
        c.execute('ALTER TABLE bulbs ADD COLUMN is_simulated INTEGER DEFAULT 0')
        print("✓ Added is_simulated column to bulbs table")
    except sqlite3.OperationalError:
        print("✓ is_simulated column already exists")
    
    conn.commit()
    conn.close()
    print("✓ Database initialized")

# Hash password securely
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Verify password
def verify_password(stored_hash, provided_password):
    return stored_hash == hash_password(provided_password)

# Send verification code email
@app.route('/send_code', methods=['POST'])
def send_code():
    data = request.get_json()
    email_recipient = data.get('email')
    code = data.get('code')

    if not email_recipient or "@" not in email_recipient:
        return jsonify({'status': 'error', 'message': 'Invalid email'}), 400

    if not code or len(code) != 6:
        return jsonify({'status': 'error', 'message': 'Invalid code'}), 400

    email_recipient = email_recipient.strip()
    code = code.strip()

    try:
        with open("hello.txt", "r") as f:
            email_password = f.read().strip()

        email_sender = "ramcaleb50@gmail.com"
        sender_display_name = "Caleb's Home Automation System"
        
        msg = EmailMessage()
        msg["From"] = f"{sender_display_name} <{email_sender}>"
        msg["To"] = email_recipient
        msg["Subject"] = "Your Verification Code"
        
        email_body = f"""Hello,

Your 6-digit verification code is: {code}

This code will expire in 5 minutes. Please do not share this code with anyone.

If you did not request this code, please ignore this email.

Best regards,
Caleb's Home Automation System

---
This is an automated message. Please do not reply to this email."""

        msg.set_content(email_body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_sender, email_password)
            server.send_message(msg)

        print(f"✓ Sent verification code to {email_recipient}")
        return jsonify({'status': 'success', 'code': code})

    except Exception as e:
        print(f"✗ Failed to send email: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to send email'}), 500


# Check if email is already registered
@app.route('/check_email', methods=['POST'])
def check_email():
    data = request.get_json()
    email = data.get('email', '').strip()
    
    print(f"→ Checking email: {email}")
    
    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        
        if user:
            print(f"✗ Email {email} is already registered")
            return jsonify({'status': 'success', 'available': False})
        else:
            print(f"✓ Email {email} is available")
            return jsonify({'status': 'success', 'available': True})
    
    except Exception as e:
        print(f"✗ Database error: {e}")
        return jsonify({'status': 'error', 'message': 'Database error'}), 500


# Register new user
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    print(f"→ Registration attempt for: {email}")
    
    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400
    
    if '@' not in email or '.' not in email.split('@')[1]:
        return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400
    
    if len(password) < 8:
        return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters'}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('SELECT id FROM users WHERE email = ?', (email,))
        if c.fetchone():
            conn.close()
            print(f"✗ Registration failed: {email} already exists")
            return jsonify({'status': 'error', 'message': 'Email already registered'}), 409
        
        password_hash = hash_password(password)
        c.execute('INSERT INTO users (email, password_hash) VALUES (?, ?)', (email, password_hash))
        conn.commit()
        conn.close()
        
        print(f"✓ User registered successfully: {email}")
        return jsonify({'status': 'success', 'message': 'User registered successfully'})
    
    except sqlite3.IntegrityError:
        print(f"✗ Integrity error: {email} already registered")
        return jsonify({'status': 'error', 'message': 'Email already registered'}), 409
    except Exception as e:
        print(f"✗ Registration error: {e}")
        return jsonify({'status': 'error', 'message': 'Registration failed'}), 500


# Login user
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    print(f"→ Login attempt for: {email}")
    
    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT password_hash FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        
        if not user:
            print(f"✗ Login failed: {email} not found")
            return jsonify({'status': 'error', 'message': 'Email not registered'}), 404
        
        if verify_password(user[0], password):
            print(f"✓ Login successful: {email}")
            return jsonify({'status': 'success', 'message': 'Login successful'})
        else:
            print(f"✗ Login failed: incorrect password for {email}")
            return jsonify({'status': 'error', 'message': 'Incorrect password'}), 401
    
    except Exception as e:
        print(f"✗ Login error: {e}")
        return jsonify({'status': 'error', 'message': 'Login failed'}), 500


# Reset password
@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email', '').strip()
    new_password = data.get('password', '')
    
    print(f"→ Password reset for: {email}")
    
    if not email or not new_password:
        return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400
    
    if len(new_password) < 8:
        return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters'}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('SELECT id FROM users WHERE email = ?', (email,))
        if not c.fetchone():
            conn.close()
            print(f"✗ Reset failed: {email} not found")
            return jsonify({'status': 'error', 'message': 'Email not registered'}), 404
        
        password_hash = hash_password(new_password)
        c.execute('UPDATE users SET password_hash = ? WHERE email = ?', (password_hash, email))
        conn.commit()
        conn.close()
        
        print(f"✓ Password reset successful: {email}")
        return jsonify({'status': 'success', 'message': 'Password reset successful'})
    
    except Exception as e:
        print(f"✗ Password reset error: {e}")
        return jsonify({'status': 'error', 'message': 'Password reset failed'}), 500


# ===== BULB MANAGEMENT =====

@app.route('/add_bulb', methods=['POST'])
def add_bulb():
    data = request.get_json()
    user_email = data.get('email', '').strip()
    bulb_id = data.get('bulb_id', '').strip()
    bulb_name = data.get('bulb_name', '').strip()
    room_name = data.get('room_name', '').strip()
    is_simulated = data.get('is_simulated', False)  # NEW
    
    print(f"→ Adding bulb '{bulb_name}' for {user_email} (simulated: {is_simulated})")
    
    if not user_email or not bulb_id or not bulb_name:
        return jsonify({'status': 'error', 'message': 'Email, bulb_id, and bulb_name are required'}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('SELECT id FROM users WHERE email = ?', (user_email,))
        if not c.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        c.execute('SELECT id FROM bulbs WHERE user_email = ? AND bulb_id = ?', (user_email, bulb_id))
        if c.fetchone():
            conn.close()
            print(f"✗ Bulb already added: {bulb_name}")
            return jsonify({'status': 'error', 'message': 'Bulb already added'}), 409
        
        c.execute('INSERT INTO bulbs (user_email, bulb_id, bulb_name, room_name, is_simulated) VALUES (?, ?, ?, ?, ?)',
                  (user_email, bulb_id, bulb_name, room_name, 1 if is_simulated else 0))
        conn.commit()
        conn.close()
        
        print(f"✓ Bulb added: {bulb_name}")
        return jsonify({'status': 'success', 'message': 'Bulb added successfully'})
    
    except Exception as e:
        print(f"✗ Add bulb error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to add bulb'}), 500


@app.route('/get_bulbs', methods=['POST'])
def get_bulbs():
    data = request.get_json()
    user_email = data.get('email', '').strip()
    simulator_mode = data.get('simulator_mode', True)  # Filter based on mode
    
    if not user_email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Filter bulbs based on simulator mode
        if simulator_mode:
            # In simulator mode, show ONLY simulated bulbs (is_simulated = 1)
            query = '''SELECT bulb_id, bulb_name, room_name, added_at, last_seen, is_simulated 
                      FROM bulbs WHERE user_email = ? AND is_simulated = 1 
                      ORDER BY added_at DESC'''
            print(f"📱 Simulator Mode ON - Loading SIMULATED bulbs for {user_email}")
        else:
            # In real hardware mode, show ONLY real bulbs (is_simulated = 0 or NULL)
            query = '''SELECT bulb_id, bulb_name, room_name, added_at, last_seen, is_simulated 
                      FROM bulbs WHERE user_email = ? AND (is_simulated = 0 OR is_simulated IS NULL)
                      ORDER BY added_at DESC'''
            print(f"🔌 Real Hardware Mode - Loading REAL bulbs for {user_email}")
        
        c.execute(query, (user_email,))
        
        bulbs = []
        for row in c.fetchall():
            is_sim = bool(row[5]) if row[5] is not None else False
            bulbs.append({
                'bulb_id': row[0],
                'bulb_name': row[1],
                'room_name': row[2],
                'added_at': row[3],
                'last_seen': row[4],
                'is_simulated': is_sim
            })
            print(f"  - {row[1]} (simulated: {is_sim})")
        
        conn.close()
        print(f"✓ Retrieved {len(bulbs)} bulbs (simulator_mode={simulator_mode})")
        return jsonify({'status': 'success', 'bulbs': bulbs})
    
    except Exception as e:
        print(f"✗ Get bulbs error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': 'Failed to retrieve bulbs'}), 500


@app.route('/update_bulb', methods=['POST'])
def update_bulb():
    data = request.get_json()
    user_email = data.get('email', '').strip()
    bulb_id = data.get('bulb_id', '').strip()
    bulb_name = data.get('bulb_name')
    room_name = data.get('room_name')
    
    if not user_email or not bulb_id:
        return jsonify({'status': 'error', 'message': 'Email and bulb_id are required'}), 400
    
    if not bulb_name and not room_name:
        return jsonify({'status': 'error', 'message': 'At least one field to update is required'}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        updates = []
        params = []
        
        if bulb_name:
            updates.append('bulb_name = ?')
            params.append(bulb_name.strip())
        
        if room_name:
            updates.append('room_name = ?')
            params.append(room_name.strip())
        
        params.extend([user_email, bulb_id])
        
        query = f"UPDATE bulbs SET {', '.join(updates)} WHERE user_email = ? AND bulb_id = ?"
        c.execute(query, params)
        
        if c.rowcount == 0:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Bulb not found'}), 404
        
        conn.commit()
        conn.close()
        
        print(f"✓ Bulb updated: {bulb_id}")
        return jsonify({'status': 'success', 'message': 'Bulb updated successfully'})
    
    except Exception as e:
        print(f"✗ Update bulb error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to update bulb'}), 500


@app.route('/delete_bulb', methods=['POST'])
def delete_bulb():
    data = request.get_json()
    user_email = data.get('email', '').strip()
    bulb_id = data.get('bulb_id', '').strip()
    
    if not user_email or not bulb_id:
        return jsonify({'status': 'error', 'message': 'Email and bulb_id are required'}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('DELETE FROM bulbs WHERE user_email = ? AND bulb_id = ?', (user_email, bulb_id))
        
        if c.rowcount == 0:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Bulb not found'}), 404
        
        conn.commit()
        conn.close()
        
        print(f"✓ Bulb deleted: {bulb_id}")
        return jsonify({'status': 'success', 'message': 'Bulb deleted successfully'})
    
    except Exception as e:
        print(f"✗ Delete bulb error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete bulb'}), 500


if __name__ == "__main__":
    init_db()
    print("\n" + "="*50)
    print("🚀 Flask Server Starting...")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
