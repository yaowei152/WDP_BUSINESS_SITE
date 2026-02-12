from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)

# Database Config
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "site.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "supersecretkey"
db = SQLAlchemy(app)

# ---------------- Models ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    orders = db.relationship('Order', backref='customer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_popular = db.Column(db.Boolean, default=False)
    reviews = db.relationship('Review', backref='product', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    user_name = db.Column(db.String(80), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_ordered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Processing')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)

# ---------------- Context Processor ----------------
@app.context_processor
def inject_context():
    cart = session.get('cart', [])
    cart_length = sum(item.get('quantity', 0) for item in cart)
    return dict(cart_length=cart_length)

# ---------------- Routes ----------------
@app.route('/')
def home():
    if 'user_id' not in session: return redirect(url_for('login'))
    trending = Product.query.filter_by(is_popular=True).limit(4).all()
    new_arrivals = Product.query.order_by(Product.id.desc()).limit(4).all()
    return render_template('index.html', trending=trending, new_arrivals=new_arrivals)

@app.route('/all')
def all_products():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    search_query = request.args.get('q', '').strip()
    selected_cats = request.args.getlist("category")
    max_price = request.args.get("max_price", default=1000, type=int)
    
    query = Product.query
    if search_query:
        query = query.filter(Product.title.ilike(f'%{search_query}%'))
    if selected_cats:
        query = query.filter(Product.category.in_(selected_cats))
    query = query.filter(Product.cost <= max_price)
    
    products = query.all()
    all_categories = [r.category for r in db.session.query(Product.category).distinct()]
    
    return render_template('all.html', products=products, all_categories=all_categories, current_cats=selected_cats, max_price=max_price, search=search_query)

@app.route('/product/<int:product_id>')
def product_details(product_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    product = Product.query.get_or_404(product_id)
    return render_template('product_details.html', product=product)

# --- Cart & Checkout ---
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    product = Product.query.get(product_id)
    if product:
        cart = session.get('cart', [])
        found = False
        for item in cart:
            if item['id'] == product_id:
                item['quantity'] += 1
                found = True
                break
        if not found:
            cart.append({'id': product.id, 'title': product.title, 'price': product.cost, 'image': product.image, 'quantity': 1})
        session['cart'] = cart
        flash(f"Added {product.title} to cart", "success")
    return redirect(request.referrer or url_for('all_products'))

@app.route('/cart')
def cart():
    if 'user_id' not in session: return redirect(url_for('login'))
    cart = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    return render_template("cart.html", cart=cart, total=total)

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    action = request.form.get('action')
    cart = session.get('cart', [])
    new_cart = []
    for item in cart:
        if item['id'] == product_id:
            if action == 'increase':
                item['quantity'] += 1
                new_cart.append(item)
            elif action == 'decrease':
                item['quantity'] -= 1
                if item['quantity'] > 0: new_cart.append(item)
        else:
            new_cart.append(item)
    session['cart'] = new_cart
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session: return redirect(url_for('login'))
    cart = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    
    if request.method == 'POST':
        # Create Order
        new_order = Order(total_price=total * 1.08, user_id=session['user_id']) # 8% Tax included
        db.session.add(new_order)
        db.session.commit()
        
        # Add Items to Order
        for item in cart:
            order_item = OrderItem(
                product_name=item['title'],
                price=item['price'],
                quantity=item['quantity'],
                order_id=new_order.id
            )
            db.session.add(order_item)
        
        db.session.commit()
        session['cart'] = [] # Clear cart
        return redirect(url_for('confirmation', order_id=new_order.id))

    return render_template('checkout.html', cart=cart, total=total, tax=total*0.08, grand_total=total*1.08)

@app.route('/confirmation/<int:order_id>')
def confirmation(order_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('confirmation.html', order_number=order_id)

# --- User Profile ---
@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    # Get user's orders, sorted by newest first
    orders = Order.query.filter_by(user_id=user.id).order_by(Order.date_ordered.desc()).all()
    return render_template('profile.html', user=user, orders=orders)

# --- Auth ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username # Store for header
            return redirect(url_for('home'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter((User.username==username)|(User.email==email)).first():
            return render_template('signup.html', error="User already exists")
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/popular')
def popular():
    if 'user_id' not in session: return redirect(url_for('login'))
    products = Product.query.filter_by(is_popular=True).all()
    return render_template('all.html', products=products, all_categories=[], hide_filters=True, search_query="Popular Items")

@app.route('/newarrivals')
def newarrivals():
    if 'user_id' not in session: return redirect(url_for('login'))
    products = Product.query.order_by(Product.id.desc()).limit(8).all()
    return render_template('all.html', products=products, all_categories=[], hide_filters=True, search_query="New Arrivals")

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash("Message sent! We'll be in touch.", "success")
        return redirect(url_for('contact'))
    return render_template('contact.html')

# --- DB Setup ---
def populate_db():
    if Product.query.first(): return
    products_data = [
        {"title": "Essential Cotton Tee", "cost": 45.00, "image": "tshirt1.png", "category": "T-shirts", "is_popular": True, "description": "100% organic cotton daily wear."},
        {"title": "Oxford Button-Down", "cost": 89.00, "image": "shirt1.png", "category": "Shirts", "is_popular": False, "description": "Classic fit for work or leisure."},
        {"title": "Urban Graphic Tee", "cost": 55.00, "image": "tshirt2.png", "category": "T-shirts", "is_popular": True, "description": "Bold design with premium print."},
        {"title": "Executive Dress Shirt", "cost": 120.00, "image": "shirt2.png", "category": "Shirts", "is_popular": False, "description": "Wrinkle-free Egyptian cotton."},
        {"title": "Signature Hoodie", "cost": 110.00, "image": "hoodie1.png", "category": "Hoodie", "is_popular": True, "description": "Heavyweight fleece comfort."},
        {"title": "Weekend Chino Shorts", "cost": 65.00, "image": "shorts1.png", "category": "Shorts", "is_popular": False, "description": "Stretch-cotton casual shorts."}
    ]
    for p in products_data:
        product = Product(**p)
        db.session.add(product)
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        populate_db()
    app.run(debug=True)