from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os

app = Flask(__name__)
# Ensure instance path exists for the database file
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
    # Relationship to reviews
    reviews = db.relationship('Review', backref='product', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    user_name = db.Column(db.String(80), nullable=False) # Simplified for now
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)

# ---------------- Helper to Populate DB ----------------
def populate_db():
    if Product.query.first():
        return # DB already populated

    products_data = [
        {"title": "Casual T-Shirt", "cost": 100, "image": "tshirt1.png", "category": "T-shirts", "is_popular": True, "description": "A comfortable, everyday t-shirt made from soft cotton."},
        {"title": "Long sleeves shirt", "cost": 150, "image": "shirt1.png", "category": "Shirts", "is_popular": False, "description": "A stylish long-sleeve shirt suitable for casual or semi-formal occasions."},
        {"title": "Graphic T-shirt", "cost": 120, "image": "tshirt2.png", "category": "T-shirts", "is_popular": True, "description": "Stand out with this unique graphic tee featuring a bold design."},
        {"title": "Buttoned up shirt", "cost": 210, "image": "shirt2.png", "category": "Shirts", "is_popular": False, "description": "A classic button-up shirt made from high-quality fabric. Perfect for the office."},
        {"title": "Classic hoodie", "cost": 180, "image": "hoodie1.png", "category": "Hoodie", "is_popular": True, "description": "Stay warm and cozy in this classic pullover hoodie with a front pocket."},
        {"title": "Simple shorts", "cost": 250, "image": "shorts1.png", "category": "Shorts", "is_popular": False, "description": "Comfortable and versatile shorts, perfect for warm weather or lounging."}
    ]

    for p_data in products_data:
        product = Product(**p_data)
        db.session.add(product)
        db.session.commit() # Commit to get the ID

        # Add some dummy reviews for each product
        review1 = Review(rating=random.randint(4, 5), comment="Great product, fits well!", user_name="Alex", product_id=product.id)
        review2 = Review(rating=random.randint(3, 4), comment="Good quality, but shipping was slow.", user_name="Sam", product_id=product.id)
        db.session.add_all([review1, review2])
    
    db.session.commit()
    print("Database populated with dummy data.")


# ---------------- Context Processor ----------------
# This makes the cart length available to the navbar in base.html on every page
@app.context_processor
def inject_cart_length():
    cart = session.get('cart', [])
    return dict(cart_length=sum(item.get('quantity', 0) for item in cart))


# ---------------- Routes ----------------
@app.route('/')
def home():
    # CUSTOMER SECURITY CHECK
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch trending products from DB
    trending_products = Product.query.filter_by(is_popular=True).limit(4).all()

    # Prepare data for the template (adapter to match old structure if needed, or update template)
    trending_now = []
    for p in trending_products:
        trending_now.append({
            'id': p.id,
            'img': p.image,
            'title': p.title,
            'price': f"${p.cost:.2f}"
        })

    top_categories = [
        {'title': "Cotton Collection", 'desc': "Comfortable and breathable.", 'link': url_for('newarrivals'), 'img': 'uniqloshirt.avif'},
        {'title': "Men's Fashion", 'desc': "Classic and contemporary designs.", 'link': url_for('all_products', category='Shirts'), 'img': 'mens.jpg'},
        {'title': "Women's Fashion", 'desc': "Elegant and trendy pieces.", 'link': url_for('all_products'), 'img': 'womens.jpg'},
    ]

    return render_template('index.html', top_categories=top_categories, trending_now=trending_now)


@app.route('/product/<int:product_id>')
def product_details(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    product = Product.query.get_or_404(product_id)
    return render_template('product_details.html', product=product)


@app.route('/all')
def all_products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    search_query = request.args.get('q', '').strip()
    selected_categories = request.args.getlist("category")
    max_price = request.args.get("max_price", default=9999, type=int)
    
    query = Product.query

    # Apply Search Filter
    if search_query:
        query = query.filter(Product.title.ilike(f'%{search_query}%') | Product.description.ilike(f'%{search_query}%'))

    # Apply Category Filter
    if selected_categories:
        query = query.filter(Product.category.in_(selected_categories))
    
    # Apply Price Filter
    query = query.filter(Product.cost <= max_price)

    filtered_products = query.all()

    # Get all unique categories for the filter sidebar
    all_categories = [r.category for r in db.session.query(Product.category).distinct()]

    return render_template('all.html', products=filtered_products, all_categories=all_categories, current_categories=selected_categories, max_price=max_price, search_query=search_query)


@app.route('/popular')
def popular():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    popular_products = Product.query.filter_by(is_popular=True).all()
    return render_template('popular.html', products=popular_products)


@app.route('/newarrivals')
def newarrivals():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Assuming higher IDs are newer. Get last 4.
    new_products = Product.query.order_by(Product.id.desc()).limit(4).all()
    return render_template('newarrivals.html', products=new_products)


@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
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
            cart.append({
                'id': product.id,
                'title': product.title,
                'price': product.cost,
                'image': product.image,
                'quantity': 1
            })
        
        session['cart'] = cart
        flash(f'{product.title} added to cart!', 'success')
        return redirect(request.referrer or url_for('all_products'))
    
    return redirect(url_for('all_products'))


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    cart_items = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template("cart.html", cart=cart_items, total=total)


@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

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
                if item['quantity'] > 0:
                    new_cart.append(item)
            elif action == 'remove':
                pass # Do not append, effectively removing
        else:
            new_cart.append(item)
    
    session['cart'] = new_cart
    return redirect(url_for('cart'))


@app.route('/clear_cart')
def clear_cart():
    session['cart'] = []
    return redirect(url_for('cart'))


@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cart_items = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    tax = total * 0.08
    grand_total = total + tax
    return render_template('checkout.html', cart=cart_items, total=total, tax=tax, grand_total=grand_total)


@app.route('/confirmation', methods=['GET', 'POST'])
def confirmation():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        session['cart'] = []
        return render_template('confirmation.html', order_number=random.randint(100000, 999999))
    return redirect(url_for('cart'))


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        feedback_entry = Feedback(name=name, email=email, message=message)
        db.session.add(feedback_entry)
        db.session.commit()
        flash(f"Thank you for your feedback, {name}!", 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')


# ---------------- Authentication & Admin ----------------
# (Keep your existing auth/admin routes here: signup, login, logout, admin_login, submissions, clear_feedback, etc.)
# ... [Insert your existing Auth/Admin routes from previous step here] ...

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            return render_template('signup.html', error="Username or Email already taken!")

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid Username or Password")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# ---------------- Run ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        populate_db() # Populate DB with initial data if empty
    app.run(debug=True)