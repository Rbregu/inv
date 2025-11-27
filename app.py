from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)

# --- Configuration & Setup ---
# 1. Use environment variable for DB_URL (Best Practice)
# Fallback to the hardcoded URL if the environment variable is not set (for local testing)
DB_URL = os.environ.get("DATABASE_URL", 
    "postgresql://reception:SXxBcqpo48ruWU2giHuoZVk6eQCYylvj@dpg-d4j1puadbo4c73ebei2g-a.oregon-postgres.render.com/reception_db_jvsg")


def get_db_connection():
    """Returns a new database connection using RealDictCursor."""
    # Use the DB_URL from the environment or the hardcoded fallback
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def get_albania_time():
    """Get current time in Albania timezone (UTC+1) as a timezone-aware datetime object."""
    # Define the Albania timezone offset (UTC+1)
    albania_tz = timezone(timedelta(hours=1))
    return datetime.now(albania_tz)

def initialize_database():
    """Initialize database with sample data if empty (simplified check)."""
    try:
        # 2. Optimization: Use 'with' statement for connection/cursor management
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Note: This count check is currently non-functional as no data is inserted.
                cur.execute("SELECT COUNT(*) as count FROM products")
                count = cur.fetchone()['count']
        
    except Exception as e:
        # Note: In production, consider logging this error instead of just printing.
        print(f"Error initializing database: {e}")

# --- Helper Function for Data Routes ---

def fetch_history_data(table_name, date_col, time_col):
    """Fetches and formats data from p_sold or p_clinic tables."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Order by date, then time, then ID for precise chronological sorting
                cur.execute(f"""
                    SELECT id, p_name, {date_col}, {time_col} 
                    FROM {table_name} 
                    ORDER BY {date_col} DESC, {time_col} DESC, id DESC
                """)
                data = cur.fetchall()
        
        products = []
        for product in data:
            date_val = product[date_col]
            time_val = product[time_col]
            
            datetime_str = 'N/A'
            if date_val and time_val:
                # Combine date and time (no longer need the complex strftime check if DB stores time objects)
                try:
                    time_str = time_val.strftime('%H:%M:%S')
                except AttributeError:
                    time_str = str(time_val) # Fallback if time_val isn't a datetime.time object
                
                datetime_str = f"{date_val} {time_str}"
            
            products.append({
                'name': product['p_name'],
                'date_time': datetime_str,
                # Sold table needs quantity=1 for template compatibility (assuming single-unit recording)
                # Clinic table does not need it, but we add it conditionally for flexibility
                **({'quantity': 1} if table_name == 'p_sold' else {}) 
            })
        
        return products
        
    except Exception as e:
        print(f"Error fetching history data from {table_name}: {e}")
        return []


# --- Web Routes ---

@app.route('/')
def index():
    return redirect(url_for('products'))

@app.route('/products')
def products():
    products_data = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Query for products currently in stock
                cur.execute("SELECT p_name, p_amount FROM products WHERE p_amount > 0 ORDER BY p_name")
                products_data = cur.fetchall()
        
        products = [{'name': p['p_name'], 'quantity': p['p_amount']} for p in products_data]
        return render_template('products.html', products=products)
        
    except Exception as e:
        print(f"Error loading products: {e}")
        return render_template('products.html', products=[])

@app.route('/sold')
def sold():
    # 3. Optimization: Use helper function
    sold_products = fetch_history_data('p_sold', 'sold_date', 'sold_time')
    return render_template('sold.html', sold_products=sold_products)

@app.route('/clinic')
def clinic():
    # 3. Optimization: Use helper function
    clinic_products = fetch_history_data('p_clinic', 'clinic_date', 'clinic_time')
    return render_template('clinic.html', clinic_products=clinic_products)


# --- API Routes ---

@app.route('/api/add_product', methods=['POST'])
def add_product():
    try:
        product_name = request.json.get('name', '').strip()
        quantity = int(request.json.get('quantity', 0))
        
        if not product_name or quantity <= 0:
            return jsonify({'success': False, 'error': 'Invalid product name or quantity'})
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
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
            # Connection is committed automatically when exiting the 'with' block successfully
            # If an exception occurs, the 'with' block ensures a rollback/cleanup.
            
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error adding product: {e}")
        return jsonify({'success': False, 'error': 'Database error'})

@app.route('/api/sell_product', methods=['POST'])
def sell_product():
    try:
        product_name = request.json.get('name', '').strip()
        # Assumes a single unit is sold per request for simplicity of the p_sold table design
        # If the front-end allows quantity > 1, you'd need a loop here or adjust the p_sold table.
        quantity = int(request.json.get('quantity', 1)) 
        
        if not product_name or quantity <= 0:
            return jsonify({'success': False, 'error': 'Invalid product name or quantity'})
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT p_id, p_amount FROM products WHERE p_name = %s FOR UPDATE", (product_name,)) # Lock the row
                product = cur.fetchone()
                
                if product:
                    if product['p_amount'] >= quantity:
                        new_quantity = product['p_amount'] - quantity
                        cur.execute(
                            "UPDATE products SET p_amount = %s WHERE p_id = %s",
                            (new_quantity, product['p_id'])
                        )
                        
                        # Get Albania time 
                        albania_time = get_albania_time()
                        current_date = albania_time.date()
                        current_time = albania_time.time()
                        
                        # 4. Optimization: Insert a record for each unit sold
                        for _ in range(quantity):
                            cur.execute(
                                "INSERT INTO p_sold (p_id, p_name, sold_date, sold_time) VALUES (%s, %s, %s, %s)",
                                (product['p_id'], product_name, current_date, current_time)
                            )
                        
                        return jsonify({'success': True})
                    else:
                        # Raise an exception to trigger the finally/with block rollback (optional, but cleaner)
                        raise ValueError('Insufficient quantity') 
                
                return jsonify({'success': False, 'error': 'Product not found'})
            
    except ValueError as ve:
        # Handle custom errors from the try block
        return jsonify({'success': False, 'error': str(ve)})
        
    except Exception as e:
        print(f"Error selling product: {e}")
        return jsonify({'success': False, 'error': 'Database error'})

@app.route('/api/send_to_clinic', methods=['POST'])
def send_to_clinic():
    # This route is simplified to always decrement by 1, based on your original logic
    try:
        product_name = request.json.get('name', '').strip()
        
        if not product_name:
            return jsonify({'success': False, 'error': 'Invalid product name'})
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT p_id, p_amount FROM products WHERE p_name = %s FOR UPDATE", (product_name,))
                product = cur.fetchone()
                
                if product:
                    if product['p_amount'] > 0:
                        new_quantity = product['p_amount'] - 1
                        cur.execute(
                            "UPDATE products SET p_amount = %s WHERE p_id = %s",
                            (new_quantity, product['p_id'])
                        )
                        
                        # Get Albania time
                        albania_time = get_albania_time()
                        current_date = albania_time.date()
                        current_time = albania_time.time()
                        
                        cur.execute(
                            "INSERT INTO p_clinic (p_id, p_name, clinic_date, clinic_time) VALUES (%s, %s, %s, %s)",
                            (product['p_id'], product_name, current_date, current_time)
                        )
                        
                        return jsonify({'success': True})
                    else:
                        return jsonify({'success': False, 'error': 'Product out of stock'})
                
                return jsonify({'success': False, 'error': 'Product not found'})
            
    except Exception as e:
        print(f"Error sending to clinic: {e}")
        return jsonify({'success': False, 'error': 'Database error'})

@app.route('/api/search_products')
def search_products():
    try:
        query = request.args.get('q', '').lower()
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if not query:
                    cur.execute("SELECT p_name, p_amount FROM products WHERE p_amount > 0 ORDER BY p_name")
                else:
                    # Optimized search query for pattern matching
                    cur.execute(
                        "SELECT p_name, p_amount FROM products WHERE LOWER(p_name) LIKE %s AND p_amount > 0 ORDER BY p_name",
                        (f'%{query}%',)
                    )
                
                results_data = cur.fetchall()
        
        # Convert to the format expected by JavaScript in a list comprehension
        results = [{'p_name': p['p_name'], 'p_amount': p['p_amount']} for p in results_data]
        
        return jsonify(results)
            
    except Exception as e:
        print(f"Error searching products: {e}")
        return jsonify([])

if __name__ == '__main__':
    # 5. Security: Use getenv for port, defaulting to 5000
    port = int(os.environ.get("PORT", 5000))
    initialize_database()
    app.run(debug=True, host='0.0.0.0', port=port)
