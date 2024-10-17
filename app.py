import sqlite3
import requests
import os
from flask import Flask, render_template, request, url_for, flash, redirect, abort, session
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from flask_wtf import Form
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, FileField
from wtforms.validators import DataRequired
from flask import send_from_directory

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'  # Replace with a real secret key

csrf = CSRFProtect(app)  # Initialize CSRF protection

# Define the path to the "uploads" folder within the Flask app directory
upload_folder = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = upload_folder

# Create the upload folder if it doesn't exist
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

# Set maximum file size for uploads (e.g., 16 MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS posts")
    cursor.execute("DROP TABLE IF EXISTS users")

    cursor.execute("""
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('index.html', posts=posts)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    photo = FileField('Photo')

@app.route('/create', methods=['GET', 'POST'])
def create():
    form = PostForm()
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        image_url = None

        if form.photo.data:
            photo = form.photo.data
            if photo.filename != '' and allowed_file(photo.filename):
                try:
                    filename = secure_filename(photo.filename)
                    photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_url = url_for('uploaded_file', filename=filename)
                except Exception as e:
                    flash(f"Error saving file: {str(e)}", 'error')
            elif photo.filename != '' and not allowed_file(photo.filename):
                flash("File type not allowed. Please upload a valid image file.", 'error')

        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO posts (title, content, image_url) VALUES (?, ?, ?)', 
                         (title, content, image_url))
            conn.commit()
            flash("Post created successfully!", 'success')
        except sqlite3.Error as e:
            flash(f"Database error: {str(e)}", 'error')
        finally:
            conn.close()

        return redirect(url_for('index'))

    return render_template('create.html', form=form)

""" @app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        if not title:
            flash('Title is required!')
        elif not content:
            flash('Content is required!')
        else:
            conn = get_db_connection()
            conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)', (title, content))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
    return render_template('create.html') """

def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post

@app.route('/<int:id>/edit/', methods=('GET', 'POST'))
def edit(id):
    post = get_post(id)
    form = PostForm(title=post['title'], content=post['content'])

    if request.method == 'POST':
        if form.validate_on_submit():
            title = form.title.data
            content = form.content.data
            image_url = post['image_url']

            if form.photo.data:
                photo = form.photo.data
                if photo.filename != '' and allowed_file(photo.filename):
                    try:
                        filename = secure_filename(photo.filename)
                        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        image_url = url_for('uploaded_file', filename=filename)
                    except Exception as e:
                        flash(f"Error saving file: {str(e)}", 'error')
                elif photo.filename != '' and not allowed_file(photo.filename):
                    flash("File type not allowed. Please upload a valid image file.", 'error')

            try:
                conn = get_db_connection()
                conn.execute('UPDATE posts SET title = ?, content = ?, image_url = ? WHERE id = ?', (title, content, image_url, id))
                conn.commit()
                flash("Post updated successfully!", 'success')
            except sqlite3.Error as e:
                flash(f"Database error: {str(e)}", 'error')
            finally:
                conn.close()

            return redirect(url_for('index'))

    return render_template('edit.html', post=post, form=form)

@app.route('/<int:id>/delete/', methods=('POST',))
def delete(id):
    post = get_post(id)
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash(f'"{post["title"]}" was successfully deleted!')
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')

def get_exchange_rate():
    url = "https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/er-eeri-daily"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            records = data['result']['records']
            if records:
                rate_yen = float(records[0]['jpy']) if records[0]['jpy'] else None
                rate_euro = float(records[0]['eur']) if records[0]['eur'] else None
                return rate_yen, rate_euro
        print(f"Failed to retrieve data. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error fetching exchange rate: {e}")
    return None, None

def get_products_with_conversion(exchange_rates):
    rate_yen, rate_euro = exchange_rates
    bags = [
        {
            "name": "Dior Medium Lady Dior Bag",
            "image": "dior.png",
            "price_euro": 5900,
            "price_yen": 980000,
            "price_hkd": 54000,
        },
        {
            "name": "Chanel CLASSIC 11.12 HANDBAG",
            "image": "chanel.png",
            "price_euro": 10300,
            "price_yen": 1744600,
            "price_hkd": 82700,
        },
        {
            "name": "LV Speedy Bandoulière 25",
            "image": "lv.png",
            "price_euro": 1550,
            "price_yen": 279400,
            "price_hkd": 15600,
        },
        {
            "name": "Loewe Small Puzzle bag in soft grained calfskin",
            "image": "loewe.png",
            "price_euro": 2800,
            "price_yen": 504900,
            "price_hkd": 27850,
        }
    ]
    
    for product in bags:
        product["converted_hkd_from_yen"] = round(product["price_yen"] * rate_yen, 2) if rate_yen else None
        product["converted_hkd_from_yen_tax"] = round(product["converted_hkd_from_yen"] * 0.9, 2) if product["converted_hkd_from_yen"] else None
        product["converted_hkd_from_euro"] = round(product["price_euro"] * rate_euro, 2) if rate_euro else None
        product["converted_hkd_from_euro_tax"] = round(product["converted_hkd_from_euro"] * 0.88, 2) if product["converted_hkd_from_euro"] else None

    return bags

def get_watches_with_conversion(exchange_rates):
    rate_yen, rate_euro = exchange_rates
    watches = [
        {
            "name": "Vacheron Constantin Overseas",
            "image": "overseas.png",
            "price_euro": 27300,
            "price_yen": 3718000,
            "price_hkd": 200000,
        },
        {
            "name": "Omega Speedmaster Calibre 321",
            "image": "omega_speedmaster.png",
            "price_euro": 16900,
            "price_yen": 2376000,
            "price_hkd": 121500,
        },
        {
            "name": "Jaeger-LeCoultre Reverso Classic Monoface Small Seconds",
            "image": "reverso.png",
            "price_euro": 11400,
            "price_yen": 1645600,
            "price_hkd": 80000,
        },
        {
            "name": "Rolex Submariner",
            "image": "rolex_sub.png",
            "price_euro": 10500,
            "price_yen": 1481700,
            "price_hkd": 84400,
        }
    ]

    for product in watches:
        product["converted_hkd_from_yen"] = round(product["price_yen"] * rate_yen, 2) if rate_yen else None
        product["converted_hkd_from_yen_tax"] = round(product["converted_hkd_from_yen"] * 0.9, 2) if product["converted_hkd_from_yen"] else None
        product["converted_hkd_from_euro"] = round(product["price_euro"] * rate_euro, 2) if rate_euro else None
        product["converted_hkd_from_euro_tax"] = round(product["converted_hkd_from_euro"] * 0.88, 2) if product["converted_hkd_from_euro"] else None

    return watches

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.route('/for_her', methods=['GET', 'POST'])
def for_her():
    exchange_rates = get_exchange_rate()
    products = get_products_with_conversion(exchange_rates)

    hkd_amount_yen = None
    hkd_amount_euro = None
    error = None
    api_error = None

    if None in exchange_rates:
        api_error = "Failed to retrieve the exchange rate. Conversion is not available at the moment."

    if request.method == 'POST':
        yen_amount_str = request.form.get('yen_amount', '0')
        euro_amount_str = request.form.get('euro_amount', '0')

        try:
            yen_amount = float(yen_amount_str) if yen_amount_str else 0
            euro_amount = float(euro_amount_str) if euro_amount_str else 0

            if yen_amount > 0 and exchange_rates[0] is not None:
                hkd_amount_yen = round(yen_amount * exchange_rates[0], 2)
            elif yen_amount > 0:
                error = "Could not retrieve the Yen exchange rate. Please try again later."

            if euro_amount > 0 and exchange_rates[1] is not None:
                hkd_amount_euro = round(euro_amount * exchange_rates[1], 2)
            elif euro_amount > 0:
                error = "Could not retrieve the Euro exchange rate. Please try again later."

        except ValueError:
            error = "Please enter a valid number for Yen or Euro amount."
        
    return render_template('for_her.html', products=products, exchange_rates=exchange_rates, 
                           hkd_amount_yen=hkd_amount_yen, hkd_amount_euro=hkd_amount_euro, 
                           error=error, api_error=api_error)

@app.route('/for_him', methods=['GET', 'POST'])
def for_him():
    exchange_rates = get_exchange_rate()
    products = get_watches_with_conversion(exchange_rates)

    hkd_amount_yen = None
    hkd_amount_euro = None
    error = None
    api_error = None

    if None in exchange_rates:
        api_error = "Failed to retrieve the exchange rate. Conversion is not available at the moment."

    if request.method == 'POST':
        yen_amount_str = request.form.get('yen_amount', '0')
        euro_amount_str = request.form.get('euro_amount', '0')

        try:
            yen_amount = float(yen_amount_str) if yen_amount_str else 0
            euro_amount = float(euro_amount_str) if euro_amount_str else 0

            if yen_amount > 0 and exchange_rates[0] is not None:
                hkd_amount_yen = round(yen_amount * exchange_rates[0], 2)
            elif yen_amount > 0:
                error = "Could not retrieve the Yen exchange rate. Please try again later."

            if euro_amount > 0 and exchange_rates[1] is not None:
                hkd_amount_euro = round(euro_amount * exchange_rates[1], 2)
            elif euro_amount > 0:
                error = "Could not retrieve the Euro exchange rate. Please try again later."

        except ValueError:
            error = "Please enter a valid number for Yen or Euro amount."
        
    return render_template('for_him.html', products=products, exchange_rates=exchange_rates, 
                           hkd_amount_yen=hkd_amount_yen, hkd_amount_euro=hkd_amount_euro, 
                           error=error, api_error=api_error)


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class SignInForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    form = SignInForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and user['password'] == password:  # Check plain text password
            session['user'] = email  # Store user in session
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('sign_in.html', form=form)

@app.route('/sign_out')
def sign_out():
    session.pop('user', None)  # Remove user from session
    flash('You have been signed out.', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        if not email or not password:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('register'))

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, password))
            conn.commit()
            flash('Registration successful! You can now sign in.', 'success')
            return redirect(url_for('sign_in'))
        except sqlite3.IntegrityError:
            flash('Email already registered. Please choose another.', 'danger')
        finally:
            conn.close()
    
    return render_template('register.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)