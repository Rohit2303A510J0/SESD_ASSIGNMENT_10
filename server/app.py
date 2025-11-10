from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from models import db, Product, Order, OrderItem
import os
from sqlalchemy import inspect

# --------------------
# App & DB Setup
# --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

# Remove old DB if exists (so tables are recreated)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

# Flask app
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

db.init_app(app)

STATUS_FLOW = ['Pending', 'Packed', 'Shipped', 'Out for delivery', 'Delivered']

# --------------------
# Routes
# --------------------
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        prods = Product.query.all()
        return jsonify([p.to_dict() for p in prods])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/order', methods=['POST'])
def create_order():
    data = request.get_json()
    items = data.get('items', [])
    if not items:
        return jsonify({'error': 'No items provided'}), 400

    total = 0.0
    for it in items:
        prod = Product.query.get(it['product_id'])
        if not prod:
            return jsonify({'error': f"Product {it['product_id']} not found"}), 404
        if prod.inventory < it['quantity']:
            return jsonify({'error': f"Not enough inventory for {prod.name}"}), 400
        total += prod.price * it['quantity']

    order = Order(total_amount=total, status='Pending')
    db.session.add(order)
    db.session.flush()

    for it in items:
        prod = Product.query.get(it['product_id'])
        prod.inventory -= it['quantity']
        oi = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            quantity=it['quantity'],
            unit_price=prod.price
        )
        db.session.add(oi)

    db.session.commit()
    return jsonify({'order_id': order.id, 'status': order.status}), 201

@app.route('/api/track/<int:order_id>', methods=['GET'])
def track_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    return jsonify(order.to_dict())

@app.route('/api/payment', methods=['POST'])
def payment():
    data = request.get_json()
    order_id = data.get('order_id')
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    order.status = 'Packed'
    db.session.commit()
    return jsonify({'order_id': order.id, 'status': order.status})

@app.route('/api/advance/<int:order_id>', methods=['POST'])
def advance_status(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    try:
        idx = STATUS_FLOW.index(order.status)
        if idx < len(STATUS_FLOW) - 1:
            order.status = STATUS_FLOW[idx + 1]
            db.session.commit()
    except ValueError:
        order.status = 'Pending'
        db.session.commit()
    return jsonify({'order_id': order.id, 'status': order.status})

# --------------------
# Seed / DB Helpers
# --------------------
def seed_data():
    default_inventory = 50
    products = Product.query.all()
    if not products:
        sample_products = [
            Product(name="Laptop", price=60000, inventory=default_inventory),
            Product(name="Smartphone", price=15000, inventory=default_inventory),
            Product(name="Headphones", price=2000, inventory=default_inventory),
            Product(name="Keyboard", price=1200, inventory=default_inventory),
        ]
        db.session.add_all(sample_products)
        db.session.commit()
    else:
        for p in products:
            if p.inventory < default_inventory:
                p.inventory = default_inventory
        db.session.commit()

# --------------------
# Debug Route
# --------------------
@app.route('/api/debug', methods=['GET'])
def debug_db():
    try:
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        return jsonify({"tables": tables})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --------------------
# Main
# --------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()   # Ensure all tables exist
        seed_data()       # Seed default products if needed

    app.run(host="0.0.0.0", port=5000)
