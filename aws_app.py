import boto3
import hashlib
import secrets
from datetime import datetime, timedelta
import random
import threading
import time
import webbrowser
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from decimal import Decimal
import json

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# AWS Configuration - Hardcoded for demo
AWS_REGION = 'us-east-1'
AWS_ACCESS_KEY_ID = 'your_access_key'
AWS_SECRET_ACCESS_KEY = 'your_secret_key'
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:235494817119:stocker'
# Initialize AWS services
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION,
                         aws_access_key_id=AWS_ACCESS_KEY_ID,
                         aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
sns = boto3.client('sns', region_name=AWS_REGION,
                   aws_access_key_id=AWS_ACCESS_KEY_ID,
                   aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

# DynamoDB Tables
users_table = dynamodb.Table('stocker_users')
portfolio_table = dynamodb.Table('stocker_portfolio')
trades_table = dynamodb.Table('stocker_trades')
messages_table = dynamodb.Table('stocker_messages')

# Stock data with realistic prices
STOCKS = {
    'AAPL': {'name': 'Apple Inc.', 'price': Decimal('180.50')},
    'GOOGL': {'name': 'Alphabet Inc.', 'price': Decimal('2750.80')},
    'MSFT': {'name': 'Microsoft Corp.', 'price': Decimal('380.20')},
    'AMZN': {'name': 'Amazon.com Inc.', 'price': Decimal('3350.75')},
    'TSLA': {'name': 'Tesla Inc.', 'price': Decimal('850.40')},
    'META': {'name': 'Meta Platforms Inc.', 'price': Decimal('320.15')},
    'NVDA': {'name': 'NVIDIA Corp.', 'price': Decimal('450.90')},
    'NFLX': {'name': 'Netflix Inc.', 'price': Decimal('420.60')},
    'PYPL': {'name': 'PayPal Holdings Inc.', 'price': Decimal('280.30')},
    'ADBE': {'name': 'Adobe Inc.', 'price': Decimal('520.75')},
    'CRM': {'name': 'Salesforce Inc.', 'price': Decimal('210.45')},
    'ORCL': {'name': 'Oracle Corp.', 'price': Decimal('95.80')},
    'IBM': {'name': 'IBM Corp.', 'price': Decimal('140.25')},
    'INTC': {'name': 'Intel Corp.', 'price': Decimal('65.30')},
    'AMD': {'name': 'Advanced Micro Devices', 'price': Decimal('120.90')},
    'UBER': {'name': 'Uber Technologies', 'price': Decimal('45.70')},
    'SNAP': {'name': 'Snap Inc.', 'price': Decimal('35.80')},
    'TWTR': {'name': 'Twitter Inc.', 'price': Decimal('52.40')},
    'SPOT': {'name': 'Spotify Technology', 'price': Decimal('180.60')},
    'SQ': {'name': 'Block Inc.', 'price': Decimal('85.20')},
    'ZOOM': {'name': 'Zoom Video Communications', 'price': Decimal('120.15')}
}

def init_dynamodb_tables():
    """Initialize DynamoDB tables if they don't exist"""
    try:
        # Check if tables exist, create if not
        existing_tables = [table.name for table in dynamodb.tables.all()]
        
        if 'stocker_users' not in existing_tables:
            users_table = dynamodb.create_table(
                TableName='stocker_users',
                KeySchema=[
                    {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'user_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            users_table.wait_until_exists()
        
        print("DynamoDB tables initialized successfully")
    except Exception as e:
        print(f"Error initializing DynamoDB tables: {e}")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_sns_notification(message):
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject='Stocker Platform Notification'
        )
        return True
    except Exception as e:
        print(f"SNS notification failed: {e}")
        return False

def update_stock_prices():
    while True:
        for symbol in STOCKS:
            # Simulate price fluctuation
            current_price = float(STOCKS[symbol]['price'])
            change = random.uniform(-0.05, 0.05)  # ±5% change
            new_price = current_price * (1 + change)
            STOCKS[symbol]['price'] = Decimal(str(round(new_price, 2)))
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
        
        try:
            # Query DynamoDB for user
            response = users_table.scan(
                FilterExpression='username = :username AND #r = :role',
                ExpressionAttributeNames={'#r': 'role'},
                ExpressionAttributeValues={':username': username, ':role': role}
            )
            
            if response['Items'] and response['Items'][0]['password_hash'] == hash_password(password):
                user = response['Items'][0]
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['email'] = user['email']
                session['role'] = user['role']
                
                # Send SNS notification
                send_sns_notification(f"User {username} logged in as {role}")
                
                if role == 'Admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                flash('Invalid credentials or role')
        except Exception as e:
            print(f"Login error: {e}")
            flash('Login error occurred')
    
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
        
        try:
            # Check if username exists
            response = users_table.scan(
                FilterExpression='username = :username AND #r = :role',
                ExpressionAttributeNames={'#r': 'role'},
                ExpressionAttributeValues={':username': username, ':role': role}
            )
            
            if response['Items']:
                flash('Username already exists for this role')
                return render_template('signup.html')
            
            # Create new user
            user_id = f"{username}_{role}_{int(time.time())}"
            users_table.put_item(Item={
                'user_id': user_id,
                'username': username,
                'email': email,
                'password_hash': hash_password(password),
                'role': role,
                'created_at': datetime.now().isoformat()
            })
            
            # Send SNS notification
            send_sns_notification(f"New user {username} signed up as {role}")
            
            flash('Account created successfully! Please login.')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"Signup error: {e}")
            flash('Signup error occurred')
    
    return render_template('signup.html')

@app.route('/check_username')
def check_username():
    username = request.args.get('username')
    role = request.args.get('role')
    
    try:
        response = users_table.scan(
            FilterExpression='username = :username AND #r = :role',
            ExpressionAttributeNames={'#r': 'role'},
            ExpressionAttributeValues={':username': username, ':role': role}
        )
        exists = len(response['Items']) > 0
        return jsonify({'exists': exists})
    except Exception as e:
        print(f"Username check error: {e}")
        return jsonify({'exists': False})

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
    
    current_price = float(STOCKS[stock_symbol]['price'])
    total_amount = current_price * quantity
    
    try:
        # Record trade
        trade_id = f"{session['user_id']}_{stock_symbol}_{int(time.time())}"
        trades_table.put_item(Item={
            'trade_id': trade_id,
            'user_id': session['user_id'],
            'stock_symbol': stock_symbol,
            'action': action,
            'quantity': quantity,
            'price': Decimal(str(current_price)),
            'total_amount': Decimal(str(total_amount)),
            'trade_date': datetime.now().isoformat()
        })
        
        # Update portfolio
        portfolio_id = f"{session['user_id']}_{stock_symbol}"
        if action == 'buy':
            try:
                # Try to update existing position
                response = portfolio_table.get_item(Key={'portfolio_id': portfolio_id})
                if 'Item' in response:
                    existing_quantity = int(response['Item']['quantity'])
                    existing_avg_price = float(response['Item']['avg_price'])
                    
                    new_quantity = existing_quantity + quantity
                    new_avg_price = ((existing_quantity * existing_avg_price) + total_amount) / new_quantity
                    
                    portfolio_table.update_item(
                        Key={'portfolio_id': portfolio_id},
                        UpdateExpression='SET quantity = :q, avg_price = :p, last_updated = :u',
                        ExpressionAttributeValues={
                            ':q': new_quantity,
                            ':p': Decimal(str(new_avg_price)),
                            ':u': datetime.now().isoformat()
                        }
                    )
                else:
                    # Create new position
                    portfolio_table.put_item(Item={
                        'portfolio_id': portfolio_id,
                        'user_id': session['user_id'],
                        'stock_symbol': stock_symbol,
                        'quantity': quantity,
                        'avg_price': Decimal(str(current_price)),
                        'last_updated': datetime.now().isoformat()
                    })
            except Exception as e:
                print(f"Portfolio update error: {e}")
        
        flash(f'{action.capitalize()} order executed successfully!')
        return redirect(url_for('portfolio'))
        
    except Exception as e:
        print(f"Trade execution error: {e}")
        flash('Trade execution failed')
        return redirect(url_for('trade'))

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    try:
        response = portfolio_table.scan(
            FilterExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': session['user_id']}
        )
        
        portfolio_data = []
        for item in response['Items']:
            if int(item['quantity']) > 0:
                stock_symbol = item['stock_symbol']
                current_price = float(STOCKS[stock_symbol]['price'])
                total_value = current_price * int(item['quantity'])
                
                portfolio_data.append({
                    'symbol': stock_symbol,
                    'name': STOCKS[stock_symbol]['name'],
                    'quantity': int(item['quantity']),
                    'avg_price': float(item['avg_price']),
                    'current_price': current_price,
                    'total_value': total_value,
                    'last_updated': item['last_updated']
                })
        
        return render_template('portfolio.html', portfolio=portfolio_data)
        
    except Exception as e:
        print(f"Portfolio error: {e}")
        return render_template('portfolio.html', portfolio=[])

@app.route('/history')
def history():
    if 'user_id' not in session or session['role'] != 'Trader':
        return redirect(url_for('login'))
    
    try:
        response = trades_table.scan(
            FilterExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': session['user_id']}
        )
        
        history_data = []
        for item in response['Items']:
            stock_symbol = item['stock_symbol']
            history_data.append({
                'symbol': stock_symbol,
                'name': STOCKS[stock_symbol]['name'],
                'action': item['action'],
                'quantity': int(item['quantity']),
                'price': float(item['price']),
                'total_amount': float(item['total_amount']),
                'trade_date': item['trade_date']
            })
        
        # Sort by trade date (newest first)
        history_data.sort(key=lambda x: x['trade_date'], reverse=True)
        
        return render_template('history.html', history=history_data)
        
    except Exception as e:
        print(f"History error: {e}")
        return render_template('history.html', history=[])

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        # Get statistics
        users_response = users_table.scan(
            FilterExpression='#r = :role',
            ExpressionAttributeNames={'#r': 'role'},
            ExpressionAttributeValues={':role': 'Trader'}
        )
        total_traders = len(users_response['Items'])
        
        trades_response = trades_table.scan()
        total_trades = len(trades_response['Items'])
        
        portfolio_response = portfolio_table.scan()
        total_portfolio_value = sum(float(item['avg_price']) * int(item['quantity']) 
                                   for item in portfolio_response['Items'])
        
        return render_template('admin_dashboard.html', 
                             total_traders=total_traders,
                             total_trades=total_trades,
                             total_portfolio_value=total_portfolio_value)
        
    except Exception as e:
        print(f"Admin dashboard error: {e}")
        return render_template('admin_dashboard.html', 
                             total_traders=0, total_trades=0, total_portfolio_value=0)

@app.route('/admin_portfolio')
def admin_portfolio():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        # Get all portfolio data with usernames
        portfolio_response = portfolio_table.scan()
        users_response = users_table.scan()
        
        # Create user lookup
        user_lookup = {user['user_id']: user['username'] for user in users_response['Items']}
        
        portfolio_data = []
        for item in portfolio_response['Items']:
            if int(item['quantity']) > 0:
                stock_symbol = item['stock_symbol']
                current_price = float(STOCKS[stock_symbol]['price'])
                total_value = current_price * int(item['quantity'])
                
                portfolio_data.append({
                    'username': user_lookup.get(item['user_id'], 'Unknown'),
                    'symbol': stock_symbol,
                    'name': STOCKS[stock_symbol]['name'],
                    'quantity': int(item['quantity']),
                    'avg_price': float(item['avg_price']),
                    'current_price': current_price,
                    'total_value': total_value
                })
        
        return render_template('admin_portfolio.html', portfolio=portfolio_data)
        
    except Exception as e:
        print(f"Admin portfolio error: {e}")
        return render_template('admin_portfolio.html', portfolio=[])

@app.route('/admin_history')
def admin_history():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        # Get all trade history with usernames
        trades_response = trades_table.scan()
        users_response = users_table.scan()
        
        # Create user lookup
        user_lookup = {user['user_id']: user['username'] for user in users_response['Items']}
        
        history_data = []
        for item in trades_response['Items']:
            stock_symbol = item['stock_symbol']
            history_data.append({
                'username': user_lookup.get(item['user_id'], 'Unknown'),
                'symbol': stock_symbol,
                'name': STOCKS[stock_symbol]['name'],
                'action': item['action'],
                'quantity': int(item['quantity']),
                'price': float(item['price']),
                'total_amount': float(item['total_amount']),
                'trade_date': item['trade_date']
            })
        
        # Sort by trade date (newest first)
        history_data.sort(key=lambda x: x['trade_date'], reverse=True)
        
        return render_template('admin_history.html', history=history_data)
        
    except Exception as e:
        print(f"Admin history error: {e}")
        return render_template('admin_history.html', history=[])

@app.route('/admin_manage')
def admin_manage():
    if 'user_id' not in session or session['role'] != 'Admin':
        return redirect(url_for('login'))
    
    try:
        # Get all users
        users_response = users_table.scan()
        users = [(user['user_id'], user['username'], user['email'], user['role'], user['created_at']) 
                for user in users_response['Items']]
        
    except Exception as e:
        print(f"Admin manage error: {e}")
        return render_template('admin_manage.html', users=[])

@app.route('/get_stock_prices')
def get_stock_prices():
    # Convert Decimal to float for JSON serialization
    stocks_json = {}
    for symbol, data in STOCKS.items():
        stocks_json[symbol] = {
            'name': data['name'],
            'price': float(data['price'])
        }
    return jsonify(stocks_json)

@app.route('/check_session')
def check_session():
    if 'user_id' in session:
        return jsonify({'valid': True})
    return jsonify({'valid': False})

if __name__ == '__main__':
    init_dynamodb_tables()
    app.run(debug=True, host='0.0.0.0', port=5000)
