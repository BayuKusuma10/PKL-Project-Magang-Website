from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- SETUP DATABASE SUPER AMAN ---
def init_db():
    conn = sqlite3.connect('toko.db')
    c = conn.cursor()
    
    # 1. Buat tabel dasar (Tabel users ditambahkan address)
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, name TEXT, email TEXT, phone TEXT, address TEXT, profile_pic TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, desc TEXT, price INTEGER, image TEXT, store_name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cart (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER, name TEXT, price INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, items TEXT, total_price INTEGER, shipping_cost INTEGER, payment_method TEXT, address TEXT, payment_proof TEXT, order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY AUTOINCREMENT, logo_pic TEXT)''')

    # 2. Isi data awal
    c.execute("SELECT COUNT(*) FROM settings")
    if c.fetchone()[0] == 0: c.execute("INSERT INTO settings (logo_pic) VALUES ('')")

    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username, password, name, email, phone, address) VALUES ('admin', '12345', 'Administrator', 'admin@toko.com', '08123456789', 'Jl. Candi Panggung, Malang')")
        
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO products (name, desc, price, image, store_name) VALUES ('Gantungan Kunci', 'Pernak-pernik estetik.', 15000, 'https://via.placeholder.com/300?text=Gantungan', 'Toko 1')")
        c.execute("INSERT INTO products (name, desc, price, image, store_name) VALUES ('Keripik Pedas', 'Cemilan gurih pedas.', 20000, 'https://via.placeholder.com/300?text=Keripik', 'Toko 2')")
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect('toko.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/logo', methods=['GET', 'POST'])
def manage_logo():
    conn = get_db_connection()
    if request.method == 'POST':
        image_file = request.files.get('logo')
        if image_file and image_file.filename != '':
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute("UPDATE settings SET logo_pic = ? WHERE id = 1", (filename,))
            conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    else:
        setting = conn.execute('SELECT logo_pic FROM settings WHERE id = 1').fetchone()
        conn.close()
        return jsonify(dict(setting))

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db_connection()
    user = conn.execute('SELECT id, username, name, email, phone, address, profile_pic FROM users WHERE username = ? AND password = ?', (data['username'], data['password'])).fetchone()
    conn.close()
    if user: return jsonify({"status": "success", "user": dict(user)})
    else: return jsonify({"status": "error", "message": "Username atau Password salah!"})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (username, password, name, email, phone, address) VALUES (?, ?, ?, '', '', '')", (data['username'], data['password'], data['username']))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Akun berhasil dibuat! Silakan Login."})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"status": "error", "message": "Username sudah dipakai! Pilih yang lain."})

@app.route('/api/profile/<int:user_id>', methods=['GET', 'POST'])
def manage_profile(user_id):
    conn = get_db_connection()
    if request.method == 'POST':
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            name, email, phone, address = request.form.get('name'), request.form.get('email'), request.form.get('phone'), request.form.get('address')
            image_file = request.files.get('profile_pic')
            if image_file and image_file.filename != '':
                filename = secure_filename(image_file.filename)
                image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                conn.execute("UPDATE users SET name=?, email=?, phone=?, address=?, profile_pic=? WHERE id=?", (name, email, phone, address, filename, user_id))
            else:
                conn.execute("UPDATE users SET name=?, email=?, phone=?, address=? WHERE id=?", (name, email, phone, address, user_id))
        else:
            data = request.json
            conn.execute("UPDATE users SET name=?, email=?, phone=?, address=? WHERE id=?", (data.get('name'), data.get('email'), data.get('phone'), data.get('address'), user_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    else:
        profile = conn.execute('SELECT name, email, phone, address, profile_pic FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return jsonify(dict(profile))

@app.route('/api/products', methods=['GET', 'POST', 'DELETE'])
def manage_products():
    conn = get_db_connection()
    if request.method == 'POST':
        name, desc, price, store_name = request.form['name'], request.form['desc'], request.form['price'], request.form['store_name']
        image_file = request.files.get('image')
        filename = ""
        if image_file and image_file.filename != '':
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn.execute("INSERT INTO products (name, desc, price, image, store_name) VALUES (?, ?, ?, ?, ?)", (name, desc, int(price), filename, store_name))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    elif request.method == 'DELETE':
        conn.execute("DELETE FROM products WHERE id = ?", (request.json['product_id'],))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    else:
        products = conn.execute('SELECT * FROM products').fetchall()
        conn.close()
        return jsonify([dict(ix) for ix in products])

@app.route('/api/cart/<int:user_id>', methods=['GET', 'POST', 'DELETE'])
def manage_cart(user_id):
    conn = get_db_connection()
    if request.method == 'POST':
        data = request.json
        conn.execute("INSERT INTO cart (user_id, product_id, name, price) VALUES (?, ?, ?, ?)", (user_id, data['id'], data['name'], data['price']))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    elif request.method == 'DELETE':
        conn.execute("DELETE FROM cart WHERE id = ? AND user_id = ?", (request.json['cart_id'], user_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    else:
        cart_items = conn.execute('SELECT * FROM cart WHERE user_id = ?', (user_id,)).fetchall()
        conn.close()
        return jsonify([dict(ix) for ix in cart_items])

@app.route('/api/checkout/<int:user_id>', methods=['POST'])
def process_checkout(user_id):
    conn = get_db_connection()
    cart_items = conn.execute('SELECT name, price FROM cart WHERE user_id = ?', (user_id,)).fetchall()
    if not cart_items:
        conn.close()
        return jsonify({"status": "error", "message": "Keranjang kosong!"})
    
    total_price = sum(item['price'] for item in cart_items)
    shipping_cost = int(total_price * 0.20)
    items_str = ", ".join([item['name'] for item in cart_items])
    
    payment_method = request.form.get('payment_method')
    address = request.form.get('address')
    
    proof_file = request.files.get('payment_proof')
    filename = ""
    if proof_file and proof_file.filename != '':
        filename = secure_filename(proof_file.filename)
        proof_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    conn.execute("INSERT INTO orders (user_id, items, total_price, shipping_cost, payment_method, address, payment_proof) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                 (user_id, items_str, total_price, shipping_cost, payment_method, address, filename))
    conn.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/orders/<int:user_id>', methods=['GET'])
def get_orders(user_id):
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC', (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in orders])

@app.route('/api/order/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)