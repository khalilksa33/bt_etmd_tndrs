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
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
            logo TEXT,
            phone TEXT,
            contact_person TEXT,
            cr_number TEXT,
            industry TEXT,
            language TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Add new columns if they don't exist
    for col in ['phone', 'contact_person', 'cr_number', 'industry', 'language']:
        try:
            conn.execute(f'ALTER TABLE companies ADD COLUMN {col} TEXT')
        except sqlite3.OperationalError:
            pass
            
    conn.commit()
    conn.close()


LANDING_PAGE_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tenders Report - Daily Forsah & Etimad Updates</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-800 font-sans antialiased">
    <!-- Hero Section -->
    <div class="relative bg-white overflow-hidden">
        <div class="max-w-7xl mx-auto">
            <div class="relative z-10 pb-8 bg-white sm:pb-16 md:pb-20 lg:max-w-2xl lg:w-full lg:pb-28 xl:pb-32">
                <main class="mt-10 mx-auto max-w-7xl px-4 sm:mt-12 sm:px-6 md:mt-16 lg:mt-20 lg:px-8 xl:mt-28">
                    <div class="sm:text-center lg:text-left">
                        <h1 class="text-4xl tracking-tight font-extrabold text-gray-900 sm:text-5xl md:text-6xl">
                            <span class="block xl:inline">Win more contracts with</span>
                            <span class="block text-blue-600 xl:inline">daily tender reports</span>
                        </h1>
                        <p class="mt-3 text-base text-gray-500 sm:mt-5 sm:text-lg sm:max-w-xl sm:mx-auto md:mt-5 md:text-xl lg:mx-0">
                            Get four beautifully formatted, fully translated daily PDF reports straight to your inbox featuring the latest opportunities from <strong>Forsah.sa</strong> and <strong>Etimad.sa</strong>.
                        </p>
                    </div>
                </main>
            </div>
        </div>
        <div class="lg:absolute lg:inset-y-0 lg:right-0 lg:w-1/2 bg-blue-50 flex items-center justify-center p-8">
             <div class="w-full max-w-md bg-white rounded-xl shadow-xl overflow-hidden p-8">
                <h2 class="text-2xl font-bold text-gray-900 mb-6 text-center">Subscribe Now</h2>
                
                {% if success %}
                <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
                    <strong>Success!</strong> You have successfully subscribed to the daily reports.
                </div>
                {% endif %}

                <form method="POST" action="/subscribe" enctype="multipart/form-data" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Company Name *</label>
                        <input type="text" name="name" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Email Address *</label>
                        <input type="email" name="email" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Phone Number</label>
                            <input type="text" name="phone" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">CR Number</label>
                            <input type="text" name="cr_number" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Contact Person</label>
                            <input type="text" name="contact_person" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Preferred Language</label>
                            <select name="language" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                                <option value="English">English</option>
                                <option value="Arabic">Arabic</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">Company Logo (Optional)</label>
                        <input type="file" name="logo" accept="image/*" class="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 border p-1">
                    </div>
                    <button type="submit" class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                        Start Receiving Reports
                    </button>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
'''

ADMIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans">
    <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div class="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
            <h1 class="text-3xl font-bold text-gray-900 mb-6">Admin Dashboard</h1>
            
            <div class="border-b border-gray-200 mb-6">
                <nav class="-mb-px flex space-x-8">
                    <a href="{{ url_for('index') }}" class="{% if active_tab == 'companies' %}border-blue-500 text-blue-600{% else %}border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300{% endif %} whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm">
                        Subscribers
                    </a>
                    <a href="{{ url_for('admin_settings') }}" class="{% if active_tab == 'settings' %}border-blue-500 text-blue-600{% else %}border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300{% endif %} whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm">
                        SMTP Settings
                    </a>
                </nav>
            </div>

            {% if active_tab == 'companies' %}
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Logo</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            {% for c in companies %}
                            <tr>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if c['logo'] %}
                                        <img class="h-10 w-auto" src="{{ url_for('uploaded_file', filename=c['logo']) }}">
                                    {% else %}
                                        <span class="text-gray-400 text-sm">None</span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="font-medium text-gray-900">{{ c['name'] }}</div>
                                    <div class="text-sm text-gray-500">{{ c['cr_number'] }}</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">{{ c['email'] }}</div>
                                    <div class="text-sm text-gray-500">{{ c['contact_person'] }} - {{ c['phone'] }}</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                    {{ c['language'] }}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                    <a href="{{ url_for('delete_company', id=c['id']) }}" class="text-red-600 hover:text-red-900">Delete</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% endif %}

            {% if active_tab == 'settings' %}
                <form method="POST" action="{{ url_for('save_settings') }}" class="space-y-6 max-w-2xl">
                    <div>
                        <label class="block text-sm font-medium text-gray-700">SMTP Host</label>
                        <input type="text" name="smtp_host" value="{{ config_data.get('smtp_host', '') }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">SMTP Port</label>
                        <input type="text" name="smtp_port" value="{{ config_data.get('smtp_port', '') }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">SMTP Username</label>
                        <input type="text" name="smtp_user" value="{{ config_data.get('smtp_user', '') }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">SMTP Password</label>
                        <input type="password" name="smtp_pass" value="{{ config_data.get('smtp_pass', '') }}" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700">From Email Address</label>
                        <input type="email" name="email_from" value="{{ config_data.get('email_from', '') }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <button type="submit" class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                        Save Settings
                    </button>
                </form>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

@app.route('/landing')
def landing():
    init_db()
    success = request.args.get('success') == '1'
    return render_template_string(LANDING_PAGE_HTML, success=success)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    init_db()
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')
    contact = request.form.get('contact_person', '')
    cr = request.form.get('cr_number', '')
    language = request.form.get('language', 'English')
    
    logo_filename = None
    if 'logo' in request.files:
        file = request.files['logo']
        if file.filename != '':
            logo_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], logo_filename))

    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO companies 
            (name, email, logo, phone, contact_person, cr_number, language) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, logo_filename, phone, contact, cr, language))
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Email already exists
    conn.close()
    return redirect(url_for('index', success='1'))

@app.route('/')
@app.route('/admin')
@requires_auth
def admin():
    init_db()
    conn = get_db()
    companies = conn.execute('SELECT * FROM companies').fetchall()
    conn.close()
    return render_template_string(ADMIN_HTML, companies=companies, active_tab='companies')

@app.route('/admin/settings')
@requires_auth
def admin_settings():
    init_db()
    conn = get_db()
    settings_rows = conn.execute('SELECT * FROM settings').fetchall()
    conn.close()
    
    config_data = {}
    for row in settings_rows:
        config_data[row['key']] = row['value']
        
    return render_template_string(ADMIN_HTML, config_data=config_data, active_tab='settings')

@app.route('/admin/settings/save', methods=['POST'])
@requires_auth
def save_settings():
    conn = get_db()
    fields = ['smtp_host', 'smtp_port', 'smtp_user', 'email_from']
    for field in fields:
        val = request.form.get(field, '')
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (field, val))
        
    smtp_pass = request.form.get('smtp_pass', '')
    if smtp_pass:
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('smtp_pass', smtp_pass))
        
    conn.commit()
    conn.close()
    return redirect(url_for('admin_settings'))

@app.route('/admin/delete/<int:id>')
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

