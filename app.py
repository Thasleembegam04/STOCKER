import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import threading
import time
import webbrowser
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Hardcoded credentials for demo
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"
ADMIN_EMAIL = "admin@stocker.com"

# Stock data with realistic prices
STOCKS = {
    'AAPL': {'name': 'Apple Inc.', 'price': 180.50},
    'GOOGL': {'name': 'Alphabet Inc.', 'price': 2750.80},
    'MSFT': {'name': 'Microsoft Corp.', 'price': 380.20},
    'AMZN': {'name': 'Amazon.com Inc.', 'price': 3350.75},
    'TSLA': {'name': 'Tesla Inc.', 'price': 850.40},
    'META': {'name': 'Meta Platforms Inc.', 'price': 320.15},
    'NVDA': {'name': 'NVIDIA Corp.', 'price': 450.90},
    'NFLX': {'name': 'Netflix Inc.', 'price': 420.60},
    'PYPL': {'name': 'PayPal Holdings Inc.', 'price': 280.30},
    'ADBE': {'name': 'Adobe Inc.', 'price': 520.75},
    'CRM': {'name': 'Salesforce Inc.', 'price': 210.45},
    'ORCL': {'name': 'Oracle Corp.', 'price': 95.80},
    'IBM': {'name': 'IBM Corp.', 'price': 140.25},
    'INTC': {'name': 'Intel Corp.', 'price': 65.30},
    'AMD': {'name': 'Advanced Micro Devices', 'price': 120.90},
    'UBER': {'name': 'Uber Technologies', 'price': 45.70},
    'SNAP': {'name': 'Snap Inc.', 'price': 35.80},
    'TWTR': {'name': 'Twitter Inc.', 'price': 52.40},
    'SPOT': {'name': 'Spotify Technology', 'price': 180.60},
    'SQ': {'name': 'Block Inc.', 'price': 85.20},
    'ZOOM': {'name': 'Zoom Video Communications', 'price': 120.15}
}

def init_db():
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Portfolio table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_symbol TEXT,
            quantity INTEGER,
            purchase_price REAL,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Trade history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_symbol TEXT,
            action TEXT,
            quantity INTEGER,
            price REAL,
            total_amount REAL,
            trade_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, to_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def send_sns_notification(message):
    # Mock SNS notification for local version
    print(f"SNS Notification: {message}")

def update_stock_prices():
    while True:
        for symbol in STOCKS:
            # Simulate price fluctuation
            current_price = STOCKS[symbol]['price']
            change = random.uniform(-0.05, 0.05)  # ±5% change
            new_price = current_price * (1 + change)
            STOCKS[symbol]['price'] = round(new_price, 2)
        time.sleep(10)

# Start background thread for price updates
price_thread = threading.Thread(target=update_stock_prices, daemon=True)
price_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        conn = sqlite3.connect('stocker.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email, password_hash, role FROM users WHERE username = ? AND role = ?', 
                      (username, role))
        user = cursor.fetchone()
        conn.close()
        
        if user and user[3] == hash_password(password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = user[2]
            session['role'] = user[4]
            
            # Send notifications
            send_sns_notification(f"User {username} logged in as {role}")
            send_email(user[2], "Login Notification", f"You have successfully logged in to Stocker as {role}.")
            
            if role == 'Admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials or role')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        # Password validation
        if len(password) < 8 or not any(c.isdigit() for c in password) or not any(c in '!@#$%^&*' for c in password):
            flash('Password must be at least 8 characters with 1 number and 1 special character')
            return render_template('signup.html')
        
        conn = sqlite3.connect('stocker.db')
        cursor = conn.cursor()
        
        # Check if username already exists for this role
        cursor.execute('SELECT id FROM users WHERE username = ? AND role = ?', (username, role))
        if cursor.fetchone():
            flash('Username already exists for this role')
            conn.close()
            return render_template('signup.html')
        
        # Insert new user
        cursor.execute('INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
                      (username, email, hash_password(password), role))
        conn.commit()
        conn.close()
        
        # Send notifications
        send_sns_notification(f"New user {username} signed up as {role}")
        send_email(email, "Welcome to Stocker", f"Welcome to Stocker! Your account has been created successfully as {role}.")
        
        flash('Account created successfully! Please login.')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/check_username')
def check_username():
    username = request.args.get('username')
    role = request.args.get('role')
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ? AND role = ?', (username, role))
    exists = cursor.fetchone() is not None
    conn.close()
    
    return jsonify({'exists': exists})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    return render_template('dashboard.html', stocks=STOCKS)

@app.route('/trade')
def trade():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    return render_template('trade.html', stocks=STOCKS)

@app.route('/execute_trade', methods=['POST'])
def execute_trade():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    stock_symbol = request.form['stock_symbol']
    action = request.form['action']
    quantity = int(request.form['quantity'])
    
    current_price = STOCKS[stock_symbol]['price']
    total_amount = current_price * quantity
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    
    # Record trade
    cursor.execute('''
        INSERT INTO trade_history (user_id, stock_symbol, action, quantity, price, total_amount)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], stock_symbol, action, quantity, current_price, total_amount))
    
    # Update portfolio
    if action == 'buy':
        cursor.execute('''
            INSERT INTO portfolio (user_id, stock_symbol, quantity, purchase_price)
            VALUES (?, ?, ?, ?)
        ''', (session['user_id'], stock_symbol, quantity, current_price))
    else:  # sell
        cursor.execute('''
            SELECT id, quantity FROM portfolio WHERE user_id = ? AND stock_symbol = ?
            ORDER BY purchase_date LIMIT 1
        ''', (session['user_id'], stock_symbol))
        
        portfolio_item = cursor.fetchone()
        if portfolio_item:
            if portfolio_item[1] > quantity:
                cursor.execute('''
                    UPDATE portfolio SET quantity = quantity - ? WHERE id = ?
                ''', (quantity, portfolio_item[0]))
            else:
                cursor.execute('DELETE FROM portfolio WHERE id = ?', (portfolio_item[0],))
    
    conn.commit()
    conn.close()
    
    flash(f'{action.capitalize()} order executed successfully!')
    return redirect(url_for('portfolio'))

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT stock_symbol, SUM(quantity) as total_quantity, AVG(purchase_price) as avg_price, MAX(purchase_date) as last_purchase
        FROM portfolio WHERE user_id = ? GROUP BY stock_symbol HAVING total_quantity > 0
    ''', (session['user_id'],))
    
    portfolio_data = []
    for row in cursor.fetchall():
        stock_symbol, total_quantity, avg_price, last_purchase = row
        current_price = STOCKS[stock_symbol]['price']
        total_value = current_price * total_quantity
        portfolio_data.append({
            'symbol': stock_symbol,
            'name': STOCKS[stock_symbol]['name'],
            'quantity': total_quantity,
            'avg_price': avg_price,
            'current_price': current_price,
            'total_value': total_value,
            'last_purchase': last_purchase
        })
    
    conn.close()
    return render_template('portfolio.html', portfolio=portfolio_data)

@app.route('/history')
def history():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT stock_symbol, action, quantity, price, total_amount, trade_date
        FROM trade_history WHERE user_id = ? ORDER BY trade_date DESC
    ''', (session['user_id'],))
    
    history_data = []
    for row in cursor.fetchall():
        stock_symbol, action, quantity, price, total_amount, trade_date = row
        history_data.append({
            'symbol': stock_symbol,
            'name': STOCKS[stock_symbol]['name'],
            'action': action,
            'quantity': quantity,
            'price': price,
            'total_amount': total_amount,
            'trade_date': trade_date
        })
    
    conn.close()
    return render_template('history.html', history=history_data)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    
    # Get statistics
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "Trader"')
    total_traders = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM trade_history')
    total_trades = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(quantity * purchase_price) FROM portfolio')
    total_portfolio_value = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         total_traders=total_traders,
                         total_trades=total_trades,
                         total_portfolio_value=total_portfolio_value)

@app.route('/admin_portfolio')
def admin_portfolio():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.username, p.stock_symbol, SUM(p.quantity) as total_quantity, AVG(p.purchase_price) as avg_price
        FROM portfolio p JOIN users u ON p.user_id = u.id
        GROUP BY u.username, p.stock_symbol HAVING total_quantity > 0
        ORDER BY u.username, p.stock_symbol
    ''')
    
    portfolio_data = []
    for row in cursor.fetchall():
        username, stock_symbol, total_quantity, avg_price = row
        current_price = STOCKS[stock_symbol]['price']
        total_value = current_price * total_quantity
        portfolio_data.append({
            'username': username,
            'symbol': stock_symbol,
            'name': STOCKS[stock_symbol]['name'],
            'quantity': total_quantity,
            'avg_price': avg_price,
            'current_price': current_price,
            'total_value': total_value
        })
    
    conn.close()
    return render_template('admin_portfolio.html', portfolio=portfolio_data)

@app.route('/admin_history')
def admin_history():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.username, t.stock_symbol, t.action, t.quantity, t.price, t.total_amount, t.trade_date
        FROM trade_history t JOIN users u ON t.user_id = u.id
        ORDER BY t.trade_date DESC
    ''')
    
    history_data = []
    for row in cursor.fetchall():
        username, stock_symbol, action, quantity, price, total_amount, trade_date = row
        history_data.append({
            'username': username,
            'symbol': stock_symbol,
            'name': STOCKS[stock_symbol]['name'],
            'action': action,
            'quantity': quantity,
            'price': price,
            'total_amount': total_amount,
            'trade_date': trade_date
        })
    
    conn.close()
    return render_template('admin_history.html', history=history_data)

@app.route('/admin_manage')
def admin_manage():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('stocker.db')
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute('SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    
    conn.close()
    return render_template('admin_manage.html', users=users)

@app.route('/get_stock_prices')
def get_stock_prices():
    return jsonify(STOCKS)

@app.route('/check_session')
def check_session():
    if 'user_id' in session:
        return jsonify({'valid': True})
    return jsonify({'valid': False})

if __name__ == '__main__':
    init_db()
    webbrowser.open('http://127.0.0.1:5000')
    app.run(debug=True, host='0.0.0.0', port=5000)
