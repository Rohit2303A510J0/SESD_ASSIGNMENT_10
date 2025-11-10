from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from models import db, Product, Order, OrderItem
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

app = Flask(__name__, static_folder='../client', static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

db.init_app(app)

STATUS_FLOW = ['Pending', 'Packed', 'Shipped', 'Out for delivery', 'Delivered']

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    prods = Product.query.all()
    return jsonify([p.to_dict() for p in prods])

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
        oi = OrderItem(order_id=order.id, product_id=prod.id, quantity=it['quantity'], unit_price=prod.price)
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

def seed_data():
    default_inventory = 50  # Inventory will reset to 50 every restart if below this

    products = Product.query.all()

    if not products:  # No products in DB → first time seed
        print("Seeding database with initial products...")
        sample_products = [
            Product(name="Laptop", price=60000, inventory=default_inventory),
            Product(name="Smartphone", price=15000, inventory=default_inventory),
            Product(name="Headphones", price=2000, inventory=default_inventory),
            Product(name="Keyboard", price=1200, inventory=default_inventory)
        ]
        db.session.add_all(sample_products)
        db.session.commit()
        print("Seeding complete with default inventory!")
    else:
        # Products exist ->Reset inventory if low or zero
        updated = False
        for p in products:
            if p.inventory < default_inventory:
                print(f"🔁 Resetting inventory for {p.name} ({p.inventory} → {default_inventory})")
                p.inventory = default_inventory
                updated = True
        
        if updated:
            db.session.commit()
            print("Inventory reset complete!")
        else:
            print("Inventory already sufficient. No changes needed.")



if __name__ == "__main__":
    with app.app_context():
        db.create_all()   # Creates DB and tables if not exists
        seed_data()       # Auto insert products only first time
    app.run(host="0.0.0.0", port=5000)

