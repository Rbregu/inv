from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timezone, timedelta
import json
import os

app = Flask(__name__)

# File to store data
DATA_FILE = 'products.json'

def get_albania_time():
    """Get current time in Albania timezone (UTC+1 or UTC+2 for DST)"""
    # Albania is in Central European Time (CET) which is UTC+1
    # For simplicity, we'll use UTC+1 (you can adjust for DST if needed)
    utc_time = datetime.now(timezone.utc)
    albania_offset = timedelta(hours=1)  # UTC+1
    # For summer time (Daylight Saving Time), use hours=2
    # You can implement DST detection if needed
    
    albania_time = utc_time + albania_offset
    return albania_time

def load_data():
    """Load data from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'products': [],
        'sold_products': [],
        'clinic_products': []
    }

def save_data(data):
    """Save data to JSON file"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@app.route('/')
def index():
    data = load_data()
    # Filter out products with quantity 0
    active_products = [p for p in data['products'] if p['quantity'] > 0]
    return render_template('products.html', products=active_products)

@app.route('/products')
def products():
    data = load_data()
    # Filter out products with quantity 0
    active_products = [p for p in data['products'] if p['quantity'] > 0]
    return render_template('products.html', products=active_products)

@app.route('/sold')
def sold():
    data = load_data()
    return render_template('sold.html', sold_products=data['sold_products'])

@app.route('/clinic')
def clinic():
    data = load_data()
    return render_template('clinic.html', clinic_products=data['clinic_products'])

# API Routes
@app.route('/api/add_product', methods=['POST'])
def add_product():
    data = load_data()
    product_name = request.json.get('name', '').strip()
    quantity = int(request.json.get('quantity', 0))
    
    if not product_name or quantity <= 0:
        return jsonify({'success': False, 'error': 'Invalid product name or quantity'})
    
    # Check if product already exists
    for product in data['products']:
        if product['name'].lower() == product_name.lower():
            product['quantity'] += quantity
            break
    else:
        # Add new product
        data['products'].append({
            'name': product_name,
            'quantity': quantity
        })
    
    save_data(data)
    return jsonify({'success': True})

@app.route('/api/sell_product', methods=['POST'])
def sell_product():
    data = load_data()
    product_name = request.json.get('name', '').strip()
    quantity = int(request.json.get('quantity', 0))
    
    if not product_name or quantity <= 0:
        return jsonify({'success': False, 'error': 'Invalid product name or quantity'})
    
    # Find and update product
    for product in data['products']:
        if product['name'].lower() == product_name.lower():
            if product['quantity'] >= quantity:
                product['quantity'] -= quantity
                
                # Add to sold products
                data['sold_products'].append({
                    'name': product_name,
                    'quantity': quantity,
                    'date_time': get_albania_time().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                save_data(data)
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Insufficient quantity'})
    
    return jsonify({'success': False, 'error': 'Product not found'})

@app.route('/api/send_to_clinic', methods=['POST'])
def send_to_clinic():
    data = load_data()
    product_name = request.json.get('name', '').strip()
    
    if not product_name:
        return jsonify({'success': False, 'error': 'Invalid product name'})
    
    # Find product
    for product in data['products']:
        if product['name'].lower() == product_name.lower():
            if product['quantity'] > 0:
                product['quantity'] -= 1
                
                # Add to clinic products
                data['clinic_products'].append({
                    'name': product_name,
                    'date_time': get_albania_time().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                save_data(data)
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Product out of stock'})
    
    return jsonify({'success': False, 'error': 'Product not found'})

@app.route('/api/search_products')
def search_products():
    data = load_data()
    query = request.args.get('q', '').lower()
    
    if not query:
        # Return all products with quantity > 0
        results = [p for p in data['products'] if p['quantity'] > 0]
        return jsonify(results)
    
    results = []
    for product in data['products']:
        if query in product['name'].lower() and product['quantity'] > 0:
            results.append(product)
    
    return jsonify(results)

@app.route('/api/get_stats')
def get_stats():
    """API endpoint to get statistics for the dashboard"""
    data = load_data()
    
    total_products = sum(product['quantity'] for product in data['products'])
    total_sold = len(data['sold_products'])
    total_clinic = len(data['clinic_products'])
    
    return jsonify({
        'total_products': total_products,
        'total_sold': total_sold,
        'total_clinic': total_clinic
    })

if __name__ == '__main__':
    # Create data file if it doesn't exist
    if not os.path.exists(DATA_FILE):
        save_data({
            'products': [],
            'sold_products': [],
            'clinic_products': []
        })
    app.run(host="0.0.0.0", port=5000, debug=True)