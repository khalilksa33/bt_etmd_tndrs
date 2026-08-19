from flask import Flask, render_template_string, request, redirect, url_for, Response, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()
DATABASE_PATH = os.environ.get("DATABASE_PATH", "tenders.db")
UPLOAD_FOLDER = 'logos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)

def check_auth(username, password):
    return username == os.environ.get("ADMIN_USER", "admin") and password == os.environ.get("ADMIN_PASS", "admin123")

def authenticate():
    return Response('Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            logo TEXT
        )
    ''')
    # Try adding the logo column if it doesn't exist (for existing tables)
    try:
        conn.execute('ALTER TABLE companies ADD COLUMN logo TEXT')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Manage Companies - Tenders Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f4f4f4; }
        .container { background: white; padding: 20px; border-radius: 8px; max-width: 800px; margin: auto; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h2 { color: #333; }
        form { margin-bottom: 20px; }
        input[type="text"], input[type="email"], input[type="file"] { width: 100%; padding: 10px; margin: 5px 0 15px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
        input[type="submit"] { background: #d9534f; color: white; border: none; padding: 10px 15px; cursor: pointer; border-radius: 4px; }
        input[type="submit"]:hover { background: #c9302c; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; border-bottom: 1px solid #ddd; text-align: left; }
        th { background-color: #f8f8f8; }
        .delete-btn { color: #d9534f; text-decoration: none; font-weight: bold; }
        img.logo-preview { max-height: 40px; max-width: 100px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Add Company</h2>
        <form method="POST" action="{{ url_for('add_company') }}" enctype="multipart/form-data">
            <label>Company Name:</label>
            <input type="text" name="name" required>
            <label>Email Address:</label>
            <input type="email" name="email" required>
            <label>Company Logo (Optional):</label>
            <input type="file" name="logo" accept="image/*">
            <input type="submit" value="Add Company">
        </form>

        <h2>Current Subscribers</h2>
        <table>
            <tr>
                <th>Logo</th>
                <th>Name</th>
                <th>Email</th>
                <th>Action</th>
            </tr>
            {% for company in companies %}
            <tr>
                <td>
                    {% if company['logo'] %}
                        <img class="logo-preview" src="{{ url_for('uploaded_file', filename=company['logo']) }}" alt="Logo">
                    {% else %}
                        No logo
                    {% endif %}
                </td>
                <td>{{ company['name'] }}</td>
                <td>{{ company['email'] }}</td>
                <td><a class="delete-btn" href="{{ url_for('delete_company', id=company['id']) }}">Remove</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
'''

@app.route('/')
@requires_auth
def index():
    init_db()
    conn = get_db()
    companies = conn.execute('SELECT * FROM companies').fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, companies=companies)

@app.route('/add', methods=['POST'])
@requires_auth
def add_company():
    name = request.form['name']
    email = request.form['email']
    
    logo_filename = None
    if 'logo' in request.files:
        file = request.files['logo']
        if file.filename != '':
            logo_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], logo_filename))

    conn = get_db()
    try:
        conn.execute('INSERT INTO companies (name, email, logo) VALUES (?, ?, ?)', (name, email, logo_filename))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Email already exists
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
@requires_auth
def delete_company(id):
    conn = get_db()
    conn.execute('DELETE FROM companies WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/logos/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)


