from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)

# PostgreSQL connection
DB_URL = "postgresql://reception:SXxBcqpo48ruWU2giHuoZVk6eQCYylvj@dpg-d4j1puadbo4c73ebei2g-a.oregon-postgres.render.com/reception_db_jvsg"

def get_db_connection():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    return conn

def get_albania_time():
    """Get current time in Albania timezone (UTC+1)"""
    utc_time = datetime.now(timezone.utc)
    albania_offset = timedelta(hours=1)
    albania_time = utc_time + albania_offset
    return albania_time

def initialize_database():
    """Initialize database with sample data if empty"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) as count FROM products")
        count = cur.fetchone()['count']
        
        if count == 0:
            sample_products = [
                ('Aspirin', 50),
                ('Bandages', 100),
                ('Syringes', 75)
            ]
            
            for product_name, quantity in sample_products:
                cur.execute(
                    "INSERT INTO products (p_name, p_amount) VALUES (%s, %s) ON CONFLICT (p_name) DO NOTHING",
                    (product_name, quantity)
                )
            
            conn.commit()
            print("Initial sample data added to PostgreSQL")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error initializing database: {e}")

@app.route('/')
def index():
    return redirect(url_for('products'))

@app.route('/products')
def products():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT p_id, p_name, p_amount FROM products WHERE p_amount > 0 ORDER BY p_name")
        products_data = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Convert to the format expected by templates
        products = []
        for product in products_data:
            products.append({
                'name': product['p_name'],
                'quantity': product['p_amount']
            })
        
        return render_template('products.html', products=products)
        
    except Exception as e:
        print(f"Error loading products: {e}")
        return render_template('products.html', products=[])

@app.route('/sold')
def sold():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Use both date and time columns
        cur.execute("""
            SELECT ps.id, ps.p_name, ps.sold_date, ps.sold_time 
            FROM p_sold ps 
            ORDER BY ps.sold_date DESC, ps.sold_time DESC, ps.id DESC
        """)
        sold_data = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Convert to the format expected by templates
        sold_products = []
        for product in sold_data:
            # Combine date and time
            if product['sold_date'] and product['sold_time']:
                # Format the time properly
                time_str = product['sold_time'].strftime('%H:%M:%S') if hasattr(product['sold_time'], 'strftime') else str(product['sold_time'])
                datetime_str = f"{product['sold_date']} {time_str}"
            else:
                datetime_str = 'N/A'
                
            sold_products.append({
                'name': product['p_name'],
                'date_time': datetime_str
            })
        
        return render_template('sold.html', sold_products=sold_products)
        
    except Exception as e:
        print(f"Error loading sold products: {e}")
        return render_template('sold.html', sold_products=[])

@app.route('/clinic')
def clinic():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Use both date and time columns
        cur.execute("""
            SELECT pc.id, pc.p_name, pc.clinic_date, pc.clinic_time 
            FROM p_clinic pc 
            ORDER BY pc.clinic_date DESC, pc.clinic_time DESC, pc.id DESC
        """)
        clinic_data = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Convert to the format expected by templates
        clinic_products = []
        for product in clinic_data:
            # Combine date and time
            if product['clinic_date'] and product['clinic_time']:
                # Format the time properly
                time_str = product['clinic_time'].strftime('%H:%M:%S') if hasattr(product['clinic_time'], 'strftime') else str(product['clinic_time'])
                datetime_str = f"{product['clinic_date']} {time_str}"
            else:
                datetime_str = 'N/A'
                
            clinic_products.append({
                'name': product['p_name'],
                'date_time': datetime_str
            })
        
        return render_template('clinic.html', clinic_products=clinic_products)
        
    except Exception as e:
        print(f"Error loading clinic products: {e}")
        return render_template('clinic.html', clinic_products=[])

# API Routes - FIXED TIME SAVING
@app.route('/api/add_product', methods=['POST'])
def add_product():
    try:
        product_name = request.json.get('name', '').strip()
        quantity = int(request.json.get('quantity', 0))
        
        if not product_name or quantity <= 0:
            return jsonify({'success': False, 'error': 'Invalid product name or quantity'})
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT p_id, p_amount FROM products WHERE p_name = %s", (product_name,))
        existing_product = cur.fetchone()
        
        if existing_product:
            new_quantity = existing_product['p_amount'] + quantity
            cur.execute(
                "UPDATE products SET p_amount = %s WHERE p_id = %s",
                (new_quantity, existing_product['p_id'])
            )
        else:
            cur.execute(
                "INSERT INTO products (p_name, p_amount) VALUES (%s, %s)",
                (product_name, quantity)
            )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error adding product: {e}")
        return jsonify({'success': False, 'error': 'Database error'})

@app.route('/api/sell_product', methods=['POST'])
def sell_product():
    try:
        product_name = request.json.get('name', '').strip()
        quantity = int(request.json.get('quantity', 0))
        
        if not product_name or quantity <= 0:
            return jsonify({'success': False, 'error': 'Invalid product name or quantity'})
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT p_id, p_amount FROM products WHERE p_name = %s", (product_name,))
        product = cur.fetchone()
        
        if product:
            if product['p_amount'] >= quantity:
                new_quantity = product['p_amount'] - quantity
                cur.execute(
                    "UPDATE products SET p_amount = %s WHERE p_id = %s",
                    (new_quantity, product['p_id'])
                )
                
                # Get Albania time and save both date and time
                albania_time = get_albania_time()
                current_date = albania_time.date()
                current_time = albania_time.time()
                
                cur.execute(
                    "INSERT INTO p_sold (p_id, p_name, sold_date, sold_time) VALUES (%s, %s, %s, %s)",
                    (product['p_id'], product_name, current_date, current_time)
                )
                
                conn.commit()
                cur.close()
                conn.close()
                
                return jsonify({'success': True})
            else:
                cur.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Insufficient quantity'})
        
        cur.close()
        conn.close()
        return jsonify({'success': False, 'error': 'Product not found'})
            
    except Exception as e:
        print(f"Error selling product: {e}")
        return jsonify({'success': False, 'error': 'Database error'})

@app.route('/api/send_to_clinic', methods=['POST'])
def send_to_clinic():
    try:
        product_name = request.json.get('name', '').strip()
        
        if not product_name:
            return jsonify({'success': False, 'error': 'Invalid product name'})
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT p_id, p_amount FROM products WHERE p_name = %s", (product_name,))
        product = cur.fetchone()
        
        if product:
            if product['p_amount'] > 0:
                new_quantity = product['p_amount'] - 1
                cur.execute(
                    "UPDATE products SET p_amount = %s WHERE p_id = %s",
                    (new_quantity, product['p_id'])
                )
                
                # Get Albania time and save both date and time
                albania_time = get_albania_time()
                current_date = albania_time.date()
                current_time = albania_time.time()
                
                cur.execute(
                    "INSERT INTO p_clinic (p_id, p_name, clinic_date, clinic_time) VALUES (%s, %s, %s, %s)",
                    (product['p_id'], product_name, current_date, current_time)
                )
                
                conn.commit()
                cur.close()
                conn.close()
                
                return jsonify({'success': True})
            else:
                cur.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Product out of stock'})
        
        cur.close()
        conn.close()
        return jsonify({'success': False, 'error': 'Product not found'})
            
    except Exception as e:
        print(f"Error sending to clinic: {e}")
        return jsonify({'success': False, 'error': 'Database error'})

@app.route('/api/search_products')
def search_products():
    try:
        query = request.args.get('q', '').lower()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        if not query:
            cur.execute("SELECT p_name, p_amount FROM products WHERE p_amount > 0 ORDER BY p_name")
        else:
            cur.execute(
                "SELECT p_name, p_amount FROM products WHERE LOWER(p_name) LIKE %s AND p_amount > 0 ORDER BY p_name",
                (f'%{query}%',)
            )
        
        results_data = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to the format expected by JavaScript
        results = []
        for product in results_data:
            results.append({
                'p_name': product['p_name'],
                'p_amount': product['p_amount']
            })
        
        return jsonify(results)
            
    except Exception as e:
        print(f"Error searching products: {e}")
        return jsonify([])

if __name__ == '__main__':
    initialize_database()
    app.run(debug=False, host='0.0.0.0', port=5000)
