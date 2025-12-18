from flask import Flask, request, jsonify
from flask_cors import CORS
from email.message import EmailMessage
import smtplib
import os
from datetime import datetime

app = Flask(__name__)

# =============================================================================
# DEPLOYMENT CONFIGURATION
# =============================================================================

# Check if running on Render.com
IS_PRODUCTION = os.environ.get('RENDER') == 'true'

# Database configuration
if IS_PRODUCTION:
    # Use PostgreSQL on Render (free tier)
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # Use PostgreSQL
        import psycopg2
        from psycopg2.extras import RealDictCursor
        DB_TYPE = 'postgresql'
        print(f"Production mode: Using PostgreSQL database")
    else:
        # Fallback to SQLite (but data won't persist on free tier)
        import sqlite3
        DB_TYPE = 'sqlite'
        DB_NAME = 'users.db'
        print(f"Production mode: Using SQLite (WARNING: Data won't persist on restarts)")
else:
    # Local development - use SQLite
    import sqlite3
    DB_TYPE = 'sqlite'
    DB_NAME = 'users.db'
    print(f"Development mode: Using SQLite at {DB_NAME}")

# Email configuration from environment variables
GMAIL_USER = os.environ.get('GMAIL_USER', 'ramcaleb50@gmail.com')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')

# Enable CORS for production
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# =============================================================================
# DATABASE HELPER FUNCTIONS
# =============================================================================

def get_db_connection():
    """Get database connection based on environment"""
    if DB_TYPE == 'postgresql':
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    
    if DB_TYPE == 'postgresql':
        c = conn.cursor()
        
        # Main user table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bulbs table
        c.execute('''
            CREATE TABLE IF NOT EXISTS bulbs (
                id SERIAL PRIMARY KEY,
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
        
    else:  # SQLite
        c = conn.cursor()
        
        # Main user table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bulbs table
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
    
    conn.commit()
    conn.close()
    print("Database initialized")

# =============================================================================
# PASSWORD HASHING
# =============================================================================

import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_hash, provided_password):
    return stored_hash == hash_password(provided_password)

# =============================================================================
# HEALTH CHECK ENDPOINTS
# =============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for uptime monitoring"""
    try:
        conn = get_db_connection()
        if DB_TYPE == 'postgresql':
            cur = conn.cursor()
            cur.execute('SELECT 1')
            cur.close()
        else:
            conn.execute('SELECT 1')
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "db_type": DB_TYPE,
            "environment": "production" if IS_PRODUCTION else "development",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/api/info', methods=['GET'])
def api_info():
    """API information endpoint"""
    return jsonify({
        "name": "Smart Bulb API",
        "version": "1.0.0",
        "database": DB_TYPE,
        "environment": "production" if IS_PRODUCTION else "development",
        "endpoints": {
            "/health": "Health check",
            "/api/info": "API information",
            "/send_code": "Send verification code",
            "/check_email": "Check email availability",
            "/register": "User registration",
            "/login": "User login",
            "/reset_password": "Password reset",
            "/add_bulb": "Add bulb to account",
            "/get_bulbs": "Get user's bulbs",
            "/update_bulb": "Update bulb details",
            "/delete_bulb": "Delete bulb from account"
        }
    }), 200

# =============================================================================
# API ENDPOINTS
# =============================================================================

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
        if IS_PRODUCTION:
            if not GMAIL_APP_PASSWORD:
                return jsonify({'status': 'error', 'message': 'Email service not configured'}), 500
            email_password = GMAIL_APP_PASSWORD
        else:
            with open("hello.txt", "r") as f:
                email_password = f.read().strip()

        email_sender = GMAIL_USER
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

        print(f"Sent verification code to {email_recipient}")
        return jsonify({'status': 'success', 'code': code})

    except Exception as e:
        print(f"Failed to send email: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to send email'}), 500

@app.route('/check_email', methods=['POST'])
def check_email():
    data = request.get_json()
    email = data.get('email', '').strip()
    
    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400
    
    try:
        conn = get_db_connection()
        
        if DB_TYPE == 'postgresql':
            cur = conn.cursor()
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            cur.close()
        else:
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            user = c.fetchone()
        
        conn.close()
        
        if user:
            return jsonify({'status': 'success', 'available': False})
        else:
            return jsonify({'status': 'success', 'available': True})
    
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({'status': 'error', 'message': 'Database error'}), 500

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400
    
    if '@' not in email or '.' not in email.split('@')[1]:
        return jsonify({'status': 'error', 'message': 'Invalid email format'}), 400
    
    if len(password) < 8:
        return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters'}), 400
    
    try:
        conn = get_db_connection()
        password_hash = hash_password(password)
        
        if DB_TYPE == 'postgresql':
            cur = conn.cursor()
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({'status': 'error', 'message': 'Email already registered'}), 409
            
            cur.execute('INSERT INTO users (email, password_hash) VALUES (%s, %s)', (email, password_hash))
            conn.commit()
            cur.close()
        else:
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            if c.fetchone():
                conn.close()
                return jsonify({'status': 'error', 'message': 'Email already registered'}), 409
            
            c.execute('INSERT INTO users (email, password_hash) VALUES (?, ?)', (email, password_hash))
            conn.commit()
        
        conn.close()
        print(f"User registered: {email}")
        return jsonify({'status': 'success', 'message': 'User registered successfully'})
    
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'status': 'error', 'message': 'Registration failed'}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400
    
    try:
        conn = get_db_connection()
        
        if DB_TYPE == 'postgresql':
            cur = conn.cursor()
            cur.execute('SELECT password_hash FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            cur.close()
        else:
            c = conn.cursor()
            c.execute('SELECT password_hash FROM users WHERE email = ?', (email,))
            user = c.fetchone()
        
        conn.close()

        if not user:
            return jsonify({'status': 'error', 'message': 'Email not registered'}), 404
        
        stored_hash = user[0] if DB_TYPE == 'postgresql' else user['password_hash']
        
        if verify_password(stored_hash, password):
            return jsonify({'status': 'success', 'message': 'Login successful'})
        else:
            return jsonify({'status': 'error', 'message': 'Incorrect password'}), 401
    
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'status': 'error', 'message': 'Login failed'}), 500

@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email', '').strip()
    new_password = data.get('password', '')
    
    if not email or not new_password:
        return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400
    
    if len(new_password) < 8:
        return jsonify({'status': 'error', 'message': 'Password must be at least 8 characters'}), 400
    
    try:
        conn = get_db_connection()
        password_hash = hash_password(new_password)
        
        if DB_TYPE == 'postgresql':
            cur = conn.cursor()
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            if not cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({'status': 'error', 'message': 'Email not registered'}), 404
            
            cur.execute('UPDATE users SET password_hash = %s WHERE email = %s', (password_hash, email))
            conn.commit()
            cur.close()
        else:
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = ?', (email,))
            if not c.fetchone():
                conn.close()
                return jsonify({'status': 'error', 'message': 'Email not registered'}), 404
            
            c.execute('UPDATE users SET password_hash = ? WHERE email = ?', (password_hash, email))
            conn.commit()
        
        conn.close()
        return jsonify({'status': 'success', 'message': 'Password reset successful'})
    
    except Exception as e:
        print(f"Password reset error: {e}")
        return jsonify({'status': 'error', 'message': 'Password reset failed'}), 500

@app.route('/add_bulb', methods=['POST'])
def add_bulb():
    data = request.get_json()
    user_email = data.get('email', '').strip()
    bulb_id = data.get('bulb_id', '').strip()
    bulb_name = data.get('bulb_name', '').strip()
    room_name = data.get('room_name', '').strip()
    is_simulated = data.get('is_simulated', False)
    
    if not user_email or not bulb_id or not bulb_name:
        return jsonify({'status': 'error', 'message': 'Email, bulb_id, and bulb_name are required'}), 400
    
    try:
        conn = get_db_connection()
        
        if DB_TYPE == 'postgresql':
            cur = conn.cursor()
            cur.execute('SELECT id FROM users WHERE email = %s', (user_email,))
            if not cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({'status': 'error', 'message': 'User not found'}), 404
            
            cur.execute('SELECT id FROM bulbs WHERE user_email = %s AND bulb_id = %s', (user_email, bulb_id))
            if cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({'status': 'error', 'message': 'Bulb already added'}), 409
            
            cur.execute('INSERT INTO bulbs (user_email, bulb_id, bulb_name, room_name, is_simulated) VALUES (%s, %s, %s, %s, %s)',
                       (user_email, bulb_id, bulb_name, room_name, 1 if is_simulated else 0))
            conn.commit()
            cur.close()
        else:
            c = conn.cursor()
            c.execute('SELECT id FROM users WHERE email = ?', (user_email,))
            if not c.fetchone():
                conn.close()
                return jsonify({'status': 'error', 'message': 'User not found'}), 404
            
            c.execute('SELECT id FROM bulbs WHERE user_email = ? AND bulb_id = ?', (user_email, bulb_id))
            if c.fetchone():
                conn.close()
                return jsonify({'status': 'error', 'message': 'Bulb already added'}), 409
            
            c.execute('INSERT INTO bulbs (user_email, bulb_id, bulb_name, room_name, is_simulated) VALUES (?, ?, ?, ?, ?)',
                     (user_email, bulb_id, bulb_name, room_name, 1 if is_simulated else 0))
            conn.commit()
        
        conn.close()
        return jsonify({'status': 'success', 'message': 'Bulb added successfully'})
    
    except Exception as e:
        print(f"Add bulb error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to add bulb'}), 500

@app.route('/get_bulbs', methods=['POST'])
def get_bulbs():
    data = request.get_json()
    user_email = data.get('email', '').strip()
    simulator_mode = data.get('simulator_mode', True)
    
    if not user_email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400
    
    try:
        conn = get_db_connection()
        
        if simulator_mode:
            query = '''SELECT bulb_id, bulb_name, room_name, added_at, last_seen, is_simulated 
                      FROM bulbs WHERE user_email = {} AND is_simulated = 1 
                      ORDER BY added_at DESC'''
        else:
            query = '''SELECT bulb_id, bulb_name, room_name, added_at, last_seen, is_simulated 
                      FROM bulbs WHERE user_email = {} AND (is_simulated = 0 OR is_simulated IS NULL)
                      ORDER BY added_at DESC'''
        
        if DB_TYPE == 'postgresql':
            query = query.format('%s')
            cur = conn.cursor()
            cur.execute(query, (user_email,))
            rows = cur.fetchall()
            cur.close()
        else:
            query = query.format('?')
            c = conn.cursor()
            c.execute(query, (user_email,))
            rows = c.fetchall()
        
        bulbs = []
        for row in rows:
            is_sim = bool(row[5]) if row[5] is not None else False
            bulbs.append({
                'bulb_id': row[0],
                'bulb_name': row[1],
                'room_name': row[2],
                'added_at': str(row[3]),
                'last_seen': str(row[4]),
                'is_simulated': is_sim
            })
        
        conn.close()
        return jsonify({'status': 'success', 'bulbs': bulbs})
    
    except Exception as e:
        print(f"Get bulbs error: {e}")
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
        conn = get_db_connection()
        
        updates = []
        params = []
        
        if bulb_name:
            updates.append('bulb_name = {}')
            params.append(bulb_name.strip())
        
        if room_name:
            updates.append('room_name = {}')
            params.append(room_name.strip())
        
        params.extend([user_email, bulb_id])
        
        if DB_TYPE == 'postgresql':
            placeholders = [f'%s' for _ in range(len(params))]
            update_str = ', '.join([u.format(placeholders[i]) for i, u in enumerate(updates)])
            query = f"UPDATE bulbs SET {update_str} WHERE user_email = %s AND bulb_id = %s"
            
            cur = conn.cursor()
            cur.execute(query, params)
            rowcount = cur.rowcount
            conn.commit()
            cur.close()
        else:
            placeholders = ['?' for _ in range(len(params))]
            update_str = ', '.join([u.format(placeholders[i]) for i, u in enumerate(updates)])
            query = f"UPDATE bulbs SET {update_str} WHERE user_email = ? AND bulb_id = ?"
            
            c = conn.cursor()
            c.execute(query, params)
            rowcount = c.rowcount
            conn.commit()
        
        conn.close()
        
        if rowcount == 0:
            return jsonify({'status': 'error', 'message': 'Bulb not found'}), 404
        
        return jsonify({'status': 'success', 'message': 'Bulb updated successfully'})
    
    except Exception as e:
        print(f"Update bulb error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to update bulb'}), 500

@app.route('/delete_bulb', methods=['POST'])
def delete_bulb():
    data = request.get_json()
    user_email = data.get('email', '').strip()
    bulb_id = data.get('bulb_id', '').strip()
    
    if not user_email or not bulb_id:
        return jsonify({'status': 'error', 'message': 'Email and bulb_id are required'}), 400
    
    try:
        conn = get_db_connection()
        
        if DB_TYPE == 'postgresql':
            cur = conn.cursor()
            cur.execute('DELETE FROM bulbs WHERE user_email = %s AND bulb_id = %s', (user_email, bulb_id))
            rowcount = cur.rowcount
            conn.commit()
            cur.close()
        else:
            c = conn.cursor()
            c.execute('DELETE FROM bulbs WHERE user_email = ? AND bulb_id = ?', (user_email, bulb_id))
            rowcount = c.rowcount
            conn.commit()
        
        conn.close()
        
        if rowcount == 0:
            return jsonify({'status': 'error', 'message': 'Bulb not found'}), 404
        
        return jsonify({'status': 'success', 'message': 'Bulb deleted successfully'})
    
    except Exception as e:
        print(f"Delete bulb error: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete bulb'}), 500

# =============================================================================
# APPLICATION STARTUP
# =============================================================================

if __name__ == "__main__":
    init_db()
    print("\n" + "="*50)
    print("Flask Server Starting...")
    print(f"Environment: {'PRODUCTION (Render)' if IS_PRODUCTION else 'DEVELOPMENT'}")
    print(f"Database: {DB_TYPE}")
    print("="*50 + "\n")
    
    port = int(os.environ.get('PORT', 5000))
    
    if not IS_PRODUCTION:
        app.run(debug=True, host='0.0.0.0', port=port)
