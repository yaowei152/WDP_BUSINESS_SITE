from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from models import Product
import random

app = Flask(__name__ ) 
app.secret_key = "your_secret_key_here"

@app.route('/') 
def home(): 
    products = [
        Product(1,"Casual T-Shirt", 100, "tshirt1.png", "T-shirts"),
        Product(2,"Long sleeves shirt", 150, "shirt1.png", "Shirts"),
        Product(3,"Graphic T-shirt", 120, "tshirt2.png", "T-shirts"),
        Product(4,"Buttoned up shirt", 210, "shirt2.png", "Shirts"),
        Product(5,"Classic hoodie", 180, "hoodie1.png", "Hoodie"),
        Product(6,"Simple shorts", 250, "shorts1.png", "Shorts")
    ]

    selected_categories = request.args.getlist("category")
    max_price = request.args.get("max_price", default=9999, type=int)

    print("Selected categories:", selected_categories)
    print("Max price:", max_price)

    filtered_products = []

    for product in products:
        # Category filter
        if selected_categories and product.category not in selected_categories:
            continue

        # Price filter
        if max_price and product.cost > max_price:
            continue

        filtered_products.append(product)

    return render_template('all.html', products = filtered_products)

products = [
        Product(1,"Casual T-Shirt", 100, "tshirt1.png", "T-shirts", is_popular=True),
        Product(2,"Long sleeves shirt", 150, "shirt1.png", "Shirts", is_popular= False),
        Product(3,"Graphic T-shirt", 120, "tshirt2.png", "T-shirts", is_popular= True),
        Product(4,"Buttoned up shirt", 210, "shirt2.png", "Shirts", is_popular= False),
        Product(5,"Classic hoodie", 180, "hoodie1.png", "Hoodie", is_popular= True),
        Product(6,"Simple shorts", 250, "shorts1.png", "Shorts", is_popular=False)
    ]

@app.route('/all')
def all_products(): 
    return render_template('all.html', products = products)

@app.route('/popular')
def popular(): 
 popular_products = [p for p in products if p.is_popular]
 return render_template('popular.html', products = popular_products)

@app.route('/newarrivals')
def newarrivals(): 
 new_products = products[-2:]
 return render_template('newarrivals.html', products = new_products )

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    # Find the product
    product = next((p for p in products if p.id == product_id), None)
    
    if product:
        # Initialize cart if not exists
        if 'cart' not in session:
            session['cart'] = []
        
        cart = session['cart']
        
        # Check if product already in cart
        found = False
        for item in cart:
            # Check if item has 'id' key before accessing
            if isinstance(item, dict) and 'id' in item and item['id'] == product_id:
                item['quantity'] = item.get('quantity', 0) + 1
                found = True
                break
        
        # If not found, add new item with CORRECT structure
        if not found:
            cart.append({
                'id': product.id,           
                'title': product.title,     
                'price': float(product.cost),  
                'image': product.image,
                'quantity': 1
            })
        
        session['cart'] = cart
        print(f"DEBUG - Cart after adding: {cart}")  # Debug
        return redirect(url_for('cart'))
    
    return redirect(url_for('all_products'))

@app.route('/cart')
def cart():
    cart_items = session.get('cart', [])
    
    # Calculate total and subtotals
    total = 0
    for item in cart_items:
        item['subtotal'] = item['price'] * item['quantity']
        total += item['subtotal']
    
    return render_template("cart.html", cart=cart_items, total=total)

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
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
    try:
        new_quantity = int(request.form.get('quantity', 1))
        cart = session.get('cart', [])
        
        for item in cart:
            if item['id'] == product_id:
                if new_quantity > 0:
                    item['quantity'] = new_quantity
                else:
                    # Remove item if quantity is 0 or negative
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
    # Get cart from session
    cart_items = session.get('cart', [])
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Calculate tax and grand total
    tax = total * 0.08  # 8% tax
    grand_total = total + tax
    
    # Pass all variables to template
    return render_template('checkout.html', 
                         cart=cart_items, 
                         total=total,
                         tax=tax,
                         grand_total=grand_total)

@app.route('/confirmation', methods=['GET', 'POST'])
def confirmation():
    if request.method == 'POST':
        # Get cart total before clearing
        cart_items = session.get('cart', [])
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        
        # Clear the cart after purchase
        session['cart'] = []
        
        # Render confirmation with order details
        return render_template('confirmation.html', 
                             total=total,
                             order_number=random.randint(100000, 999999))
    
    # If GET request, redirect to cart
    return redirect(url_for('cart'))

if __name__ == '__main__': 
 app.run(debug=True) 