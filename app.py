from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "supersecretkey"  # replace with a secure random string
db = SQLAlchemy(app)

# ---------------- Models ----------------
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<Feedback {self.name} - {self.email}>"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ---------------- Routes ----------------
@app.route('/')
def home():
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
    all_feedback = Feedback.query.all()
    return render_template('submissions.html', feedbacks=all_feedback)

@app.route('/clear-feedback', methods=['POST'])
def clear_feedback():
    Feedback.query.delete()
    db.session.commit()
    open('feedback.txt', 'w').close()  # optional text file clear
    return redirect(url_for('submissions'))

# ---------------- Authentication ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "Username already taken!"

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if admin credentials
        if username == 'admin' and password == '67sigma':
            session['is_admin'] = True
            return redirect(url_for('admin_accounts'))

        # Check regular user
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('home'))
        else:
            return "Invalid credentials!"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

# ---------------- Admin ----------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == '67sigma':
            session['is_admin'] = True
            return redirect(url_for('admin_accounts'))
        else:
            return "Invalid admin credentials!"

    return render_template('admin_login.html')

@app.route('/admin/accounts', methods=['GET', 'POST'])
def admin_accounts():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    search_query = request.form.get('search', '')

    if search_query:
        users = User.query.filter(User.username.contains(search_query)).all()
    else:
        users = User.query.all()

    return render_template('admin_accounts.html', users=users, search_query=search_query)

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('admin_accounts'))

@app.route('/admin/clear', methods=['POST'])
def clear_users():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    User.query.delete()
    db.session.commit()
    return redirect(url_for('admin_accounts'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('home'))

# ---------------- Run ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)