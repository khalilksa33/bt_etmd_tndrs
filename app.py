from flask import Flask, render_template_string, request, redirect, url_for, Response, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename
import subprocess
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
            language TEXT,
            subscription_type TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Add new columns if they don't exist
    for col in ['phone', 'contact_person', 'cr_number', 'industry', 'language', 'subscription_type']:
        try:
            conn.execute(f'ALTER TABLE companies ADD COLUMN {col} TEXT')
        except sqlite3.OperationalError:
            pass
            
    conn.commit()
    conn.close()

LANDING_PAGE_HTML_EN = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Get daily tender reports from Forsah.sa and Etimad.sa. Never miss a government procurement or contracting opportunity in Saudi Arabia. Translated and delivered to your inbox 4 times a day.">
    <meta name="keywords" content="Saudi Arabia Tenders, Etimad tenders, Forsah tenders, KSA government contracts, B2B procurement, contracting opportunities, business in Saudi Arabia">
    <title>Tenders Report - Daily Forsah & Etimad Updates</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        var themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
        var themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            themeToggleLightIcon.classList.remove('hidden');
        } else {
            themeToggleDarkIcon.classList.remove('hidden');
        }
        var themeToggleBtn = document.getElementById('theme-toggle');
        themeToggleBtn.addEventListener('click', function() {
            themeToggleDarkIcon.classList.toggle('hidden');
            themeToggleLightIcon.classList.toggle('hidden');
            if (localStorage.getItem('color-theme')) {
                if (localStorage.getItem('color-theme') === 'light') {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                } else {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                }
            } else {
                if (document.documentElement.classList.contains('dark')) {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                } else {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                }
            }
        });
    </script>
</body>
</html>
'''

LANDING_PAGE_HTML_AR = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Get تقارير المناقصات اليومية from Forsah.sa and Etimad.sa. Never miss a government procurement or contracting opportunity in Saudi Arabia. Translated and delivered to your inbox 4 times a day.">
    <meta name="keywords" content="Saudi Arabia Tenders, Etimad tenders, Forsah tenders, KSA government contracts, B2B procurement, contracting opportunities, business in Saudi Arabia">
    <title>Tenders Report - Daily Forsah & Etimad Updates</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        var themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
        var themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            themeToggleLightIcon.classList.remove('hidden');
        } else {
            themeToggleDarkIcon.classList.remove('hidden');
        }
        var themeToggleBtn = document.getElementById('theme-toggle');
        themeToggleBtn.addEventListener('click', function() {
            themeToggleDarkIcon.classList.toggle('hidden');
            themeToggleLightIcon.classList.toggle('hidden');
            if (localStorage.getItem('color-theme')) {
                if (localStorage.getItem('color-theme') === 'light') {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                } else {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                }
            } else {
                if (document.documentElement.classList.contains('dark')) {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                } else {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                }
            }
        });
    </script>
</body>
</html>
'''

ADMIN_HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        var themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
        var themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            themeToggleLightIcon.classList.remove('hidden');
        } else {
            themeToggleDarkIcon.classList.remove('hidden');
        }
        var themeToggleBtn = document.getElementById('theme-toggle');
        themeToggleBtn.addEventListener('click', function() {
            themeToggleDarkIcon.classList.toggle('hidden');
            themeToggleLightIcon.classList.toggle('hidden');
            if (localStorage.getItem('color-theme')) {
                if (localStorage.getItem('color-theme') === 'light') {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                } else {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                }
            } else {
                if (document.documentElement.classList.contains('dark')) {
                    document.documentElement.classList.remove('dark');
                    localStorage.setItem('color-theme', 'light');
                } else {
                    document.documentElement.classList.add('dark');
                    localStorage.setItem('color-theme', 'dark');
                }
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    init_db()
    success = request.args.get('success') == '1'
    lang = request.args.get('lang', 'en')
    html_template = LANDING_PAGE_HTML_AR if lang == 'ar' else LANDING_PAGE_HTML_EN
    return render_template_string(html_template, success=success)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    init_db()
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')
    contact = request.form.get('contact_person', '')
    cr = request.form.get('cr_number', '')
    industry = request.form.get('industry', '')
    language = request.form.get('language', 'English')
    sub_type = request.form.get('subscription_type', 'Monthly')
    
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO companies 
            (name, email, phone, contact_person, cr_number, industry, language, subscription_type) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, contact, cr, industry, language, sub_type))
        conn.commit()
        # Trigger immediate test report for new subscriber
        try:
            # We assume it runs from the project root
            subprocess.Popen(f"venv/bin/python3 forsah_tenders.py --email '{email}' >> test_report.log 2>&1", shell=True)
        except Exception as e:
            print("Failed to trigger report:", e)
    except sqlite3.IntegrityError:
        pass # Email already exists
    conn.close()
    return redirect(url_for('index', success='1'))

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
    return redirect(url_for('admin'))


@app.route('/admin/add', methods=['GET', 'POST'])
@requires_auth
def admin_add():
    if request.method == 'POST':
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        contact = request.form.get('contact_person', '')
        cr = request.form.get('cr_number', '')
        industry = request.form.get('industry', '')
        language = request.form.get('language', 'English')
        sub_type = request.form.get('subscription_type', 'Monthly')
        
        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO companies 
                (name, email, phone, contact_person, cr_number, industry, language, subscription_type) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, phone, contact, cr, industry, language, sub_type))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        conn.close()
        return redirect(url_for('admin'))
    return render_template_string(ADMIN_HTML, active_tab='add', company=None)

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@requires_auth
def admin_edit(id):
    conn = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        contact = request.form.get('contact_person', '')
        cr = request.form.get('cr_number', '')
        industry = request.form.get('industry', '')
        language = request.form.get('language', 'English')
        sub_type = request.form.get('subscription_type', 'Monthly')
        
        conn.execute('''
            UPDATE companies 
            SET name=?, email=?, phone=?, contact_person=?, cr_number=?, industry=?, language=?, subscription_type=?
            WHERE id=?
        ''', (name, email, phone, contact, cr, industry, language, sub_type, id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
        
    company = conn.execute('SELECT * FROM companies WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template_string(ADMIN_HTML, active_tab='edit', company=company)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)



