from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "supersecretkey"
db = SQLAlchemy(app)

# ---------------- Models ----------------
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product:
    def __init__(self, id, title, cost, image, category, is_popular=False):
        self.id = id
        self.title = title
        self.cost = cost
        self.image = image
        self.category = category
        self.is_popular = is_popular

products = [
    Product(1, "Casual T-Shirt", 100, "tshirt1.png", "T-shirts", is_popular=True),
    Product(2, "Long sleeves shirt", 150, "shirt1.png", "Shirts", is_popular=False),
    Product(3, "Graphic T-shirt", 120, "tshirt2.png", "T-shirts", is_popular=True),
    Product(4, "Buttoned up shirt", 210, "shirt2.png", "Shirts", is_popular=False),
    Product(5, "Classic hoodie", 180, "hoodie1.png", "Hoodie", is_popular=True),
    Product(6, "Simple shorts", 250, "shorts1.png", "Shorts", is_popular=False)
]

# ---------------- Routes ----------------
@app.route('/')
def home():
    # CUSTOMER SECURITY CHECK:
    # If not logged in, redirect to the customer login page
    if 'user_id' not in session:
        return redirect(url_for('login'))

    top_categories = [
        {'title': "Cotton Collection", 'desc': "comfortable and breathable", 'link': "new-arrivals", 'img': 'uniqloshirt.avif'},
        {'title': "Men's Fashion", 'desc': "Classic and contemporary designs", 'link': "shop?category=mens", 'img': 'mens.jpg'},
        {'title': "Women's Fashion", 'desc': "Elegant and trendy pieces", 'link': "shop?category=womens", 'img': 'womens.jpg'},
    ]

    trending_now = [
        {'img': 'shirt1.jpg', 'alt': 'Basketball graphic tee', 'title': 'Graphic tee', 'price': '$12.99', 'link': "#"},
        {'img': 'uniqloshirt.avif', 'alt': 'Broadcloth shirt long sleeve', 'title': 'Broadcloth shirt long sleeve', 'price': '$35', 'link': "#"},
        {'img': 'womendress.avif', 'alt': 'Linen tiered dress', 'title': 'Linen tiered dress', 'price': '$50.00', 'link': "#"},
        {'img': 'sweatshirt.avif', 'alt': 'Cotton sweatshirt', 'title': 'Cotton sweatshirt', 'price': '$32.99', 'link': "#"},
    ]

    quick_links = [
        {'title': "Customer Service", 'desc': "Get help with your orders", 'link': "contact"},
        {'title': "Promotions", 'desc': "Check out our latest deals", 'link': "promotions"},
    ]

    return render_template('index.html',
                           top_categories=top_categories,
                           trending_now=trending_now,
                           quick_links=quick_links)

@app.route('/all')
def all_products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    selected_categories = request.args.getlist("category")
    max_price = request.args.get("max_price", default=9999, type=int)
    
    filtered_products = [p for p in products if (not selected_categories or p.category in selected_categories) and p.cost <= max_price]
    return render_template('all.html', products=filtered_products)

@app.route('/popular')
def popular():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    popular_products = [p for p in products if p.is_popular]
    return render_template('popular.html', products=popular_products)

@app.route('/newarrivals')
def newarrivals():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    new_products = products[-2:]
    return render_template('newarrivals.html', products=new_products)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    product = next((p for p in products if p.id == product_id), None)
    
    if product:
        if 'cart' not in session:
            session['cart'] = []
        
        cart = session['cart']
        found = False
        for item in cart:
            if isinstance(item, dict) and 'id' in item and item['id'] == product_id:
                item['quantity'] = item.get('quantity', 0) + 1
                found = True
                break
        
        if not found:
            cart.append({
                'id': product.id,
                'title': product.title,
                'price': float(product.cost),
                'image': product.image,
                'quantity': 1
            })
        
        session['cart'] = cart
        return redirect(url_for('cart'))
    
    return redirect(url_for('all_products'))

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    cart_items = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    for item in cart_items:
        item['subtotal'] = item['price'] * item['quantity']
    return render_template("cart.html", cart=cart_items, total=total)

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    action = request.form.get('action')
    cart = session.get('cart', [])
    
    for i, item in enumerate(cart):
        if item['id'] == product_id:
            if action == 'increase':
                item['quantity'] += 1
            elif action == 'decrease':
                if item['quantity'] > 1:
                    item['quantity'] -= 1
                else:
                    cart.pop(i)
                    break
            elif action == 'remove':
                cart.pop(i)
                break
            break
    
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/update_quantity/<int:product_id>', methods=['POST'])
def update_quantity(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'})

    try:
        new_quantity = int(request.form.get('quantity', 1))
        cart = session.get('cart', [])
        
        for item in cart:
            if item['id'] == product_id:
                if new_quantity > 0:
                    item['quantity'] = new_quantity
                else:
                    cart = [i for i in cart if i['id'] != product_id]
                break
        
        session['cart'] = cart
        return jsonify({'success': True, 'message': 'Quantity updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
        cart_items = session.get('cart', [])
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        session['cart'] = []
        return render_template('confirmation.html', total=total, order_number=random.randint(100000, 999999))
    return redirect(url_for('cart'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    thank_you_message = None
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        feedback_entry = Feedback(name=name, email=email, message=message)
        db.session.add(feedback_entry)
        db.session.commit()

        thank_you_message = f"Thank you for your feedback, {name}! We appreciate your message."

    return render_template('contact.html', thank_you_message=thank_you_message)

@app.route('/submissions')
def submissions():
    # Protected: Only for Admins
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    all_feedback = Feedback.query.all()
    return render_template('submissions.html', feedbacks=all_feedback)

@app.route('/clear-feedback', methods=['POST'])
def clear_feedback():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    Feedback.query.delete()
    db.session.commit()
    if os.path.exists('feedback.txt'):
        open('feedback.txt', 'w').close() 
    return redirect(url_for('submissions'))

# ---------------- Authentication ----------------

# 1. CUSTOMER SIGNUP
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

# 2. CUSTOMER LOGIN
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
            # SUCCESS: Explicit redirect to home
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid Username or Password")

    return render_template('login.html')

# 3. ADMIN LOGIN
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
         return "Admin already logged in. Panel pending integration."

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == '123':
            session['is_admin'] = True
            return "<h2>Admin Login Successful.</h2><p>Waiting for admin panel integration...</p><a href='/admin/logout'>Logout</a>"
        else:
            return render_template('admin_login.html', error="Invalid Admin Credentials")

    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

# ---------------- Run ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)