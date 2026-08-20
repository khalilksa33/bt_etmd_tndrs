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
<script>
        var themeToggleDarkIconAdmin = document.getElementById('theme-toggle-dark-icon-admin');
        var themeToggleLightIconAdmin = document.getElementById('theme-toggle-light-icon-admin');
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            if(themeToggleLightIconAdmin) themeToggleLightIconAdmin.classList.remove('hidden');
        } else {
            if(themeToggleDarkIconAdmin) themeToggleDarkIconAdmin.classList.remove('hidden');
        }
        var themeToggleBtnAdmin = document.getElementById('theme-toggle-admin');
        if(themeToggleBtnAdmin) {
            themeToggleBtnAdmin.addEventListener('click', function() {
                themeToggleDarkIconAdmin.classList.toggle('hidden');
                themeToggleLightIconAdmin.classList.toggle('hidden');
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
        }
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
<script>
        var themeToggleDarkIconAdmin = document.getElementById('theme-toggle-dark-icon-admin');
        var themeToggleLightIconAdmin = document.getElementById('theme-toggle-light-icon-admin');
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            if(themeToggleLightIconAdmin) themeToggleLightIconAdmin.classList.remove('hidden');
        } else {
            if(themeToggleDarkIconAdmin) themeToggleDarkIconAdmin.classList.remove('hidden');
        }
        var themeToggleBtnAdmin = document.getElementById('theme-toggle-admin');
        if(themeToggleBtnAdmin) {
            themeToggleBtnAdmin.addEventListener('click', function() {
                themeToggleDarkIconAdmin.classList.toggle('hidden');
                themeToggleLightIconAdmin.classList.toggle('hidden');
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
        }
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
        tailwind.config = {
            darkMode: 'class',
        }
    </script>
    <script>
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark')
        }
    </script>
</head>
<body class="bg-gray-100 dark:bg-gray-900 font-sans text-gray-900 dark:text-gray-100">
    <nav class="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16 items-center">
                <div class="flex-shrink-0 flex items-center">
                    <span class="text-2xl font-black text-blue-600 dark:text-blue-500 tracking-tighter">Tenders<span class="text-gray-800 dark:text-gray-100">Hub</span> <span class="text-sm font-normal text-gray-500 ml-2">Admin</span></span>
                </div>
                <div class="flex items-center space-x-4">
                    <button id="theme-toggle-admin" type="button" class="text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700 rounded-lg text-sm p-2">
                        <svg id="theme-toggle-dark-icon-admin" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path></svg>
                        <svg id="theme-toggle-light-icon-admin" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" fill-rule="evenodd" clip-rule="evenodd"></path></svg>
                    </button>
                    <a href="{{ url_for('index') }}" class="text-sm font-medium text-gray-500 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">View Live Site</a>
                </div>
            </div>
        </div>
    </nav>
    <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div class="bg-white dark:bg-gray-800 shadow px-4 py-5 sm:rounded-lg sm:p-6">
            
            <div class="border-b border-gray-200 mb-6">
                <nav class="-mb-px flex space-x-8">
                    <a href="{{ url_for('admin') }}" class="{% if active_tab == 'companies' %}border-blue-500 text-blue-600{% else %}border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300{% endif %} whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm">
                        Subscribers
                    </a>
                    <a href="{{ url_for('admin_settings') }}" class="{% if active_tab == 'settings' %}border-blue-500 text-blue-600{% else %}border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300{% endif %} whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm">
                        SMTP Settings
                    </a>
                </nav>
            </div>

            {% if active_tab == 'companies' %}
                <div class="mb-4 flex justify-end">
                    <a href="{{ url_for('admin_add') }}" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
                        + Add Subscriber
                    </a>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50 dark:bg-gray-700">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan & Details</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                            {% for c in companies %}
                            <tr>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="font-medium text-gray-900 dark:text-white">{{ c['name'] }}</div>
                                    <div class="text-sm text-gray-500">CR: {{ c['cr_number'] }}</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900 dark:text-white">{{ c['email'] }}</div>
                                    <div class="text-sm text-gray-500">{{ c['contact_person'] }} - {{ c['phone'] }}</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-semibold text-blue-600">{{ c['subscription_type'] or 'Monthly' }}</div>
                                    <div class="text-xs text-gray-500">{{ c['industry'] }} | {{ c['language'] }}</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                    <a href="{{ url_for('admin_edit', id=c['id']) }}" class="text-blue-600 hover:text-blue-900 mr-3">Edit</a>
                                    <a href="{{ url_for('delete_company', id=c['id']) }}" class="text-red-600 hover:text-red-900">Delete</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            {% endif %}
            
            {% if active_tab == 'edit' or active_tab == 'add' %}
                <h2 class="text-xl font-bold mb-4 dark:text-white">{{ 'Edit' if active_tab == 'edit' else 'Add' }} Subscriber</h2>
                <form method="POST" action="{{ url_for('admin_edit', id=company['id']) if active_tab == 'edit' else url_for('admin_add') }}" class="space-y-6 max-w-2xl">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Company Name</label>
                            <input type="text" name="name" value="{{ company['name'] if company else '' }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Email Address</label>
                            <input type="email" name="email" value="{{ company['email'] if company else '' }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Phone Number</label>
                            <input type="text" name="phone" value="{{ company['phone'] if company else '' }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Contact Person</label>
                            <input type="text" name="contact_person" value="{{ company['contact_person'] if company else '' }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">CR Number</label>
                            <input type="text" name="cr_number" value="{{ company['cr_number'] if company else '' }}" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Industry / Category</label>
                            <input type="text" name="industry" value="{{ company['industry'] if company else '' }}" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Language</label>
                            <select name="language" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                                <option value="English" {% if company and company['language'] == 'English' %}selected{% endif %}>English</option>
                                <option value="Arabic" {% if company and company['language'] == 'Arabic' %}selected{% endif %}>Arabic</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Subscription Type</label>
                            <select name="subscription_type" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                                <option value="Monthly" {% if company and company['subscription_type'] == 'Monthly' %}selected{% endif %}>Monthly</option>
                                <option value="Annual" {% if company and company['subscription_type'] == 'Annual' %}selected{% endif %}>Annual</option>
                            </select>
                        </div>
                    </div>
                    <div class="mt-4 flex items-center">
                        <button type="submit" class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                            Save Subscriber
                        </button>
                        <a href="{{ url_for('admin') }}" class="ml-4 text-gray-600 hover:text-gray-900 font-medium">Cancel</a>
                    </div>
                </form>
            {% endif %}

            {% if active_tab == 'settings' %}
                <form method="POST" action="{{ url_for('save_settings') }}" class="space-y-6 max-w-2xl">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">SMTP Host</label>
                        <input type="text" name="smtp_host" value="{{ config_data.get('smtp_host', '') }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">SMTP Port</label>
                        <input type="text" name="smtp_port" value="{{ config_data.get('smtp_port', '') }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">SMTP Username</label>
                        <input type="text" name="smtp_user" value="{{ config_data.get('smtp_user', '') }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">SMTP Password</label>
                        <input type="password" name="smtp_pass" value="{{ config_data.get('smtp_pass', '') }}" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">From Email Address</label>
                        <input type="email" name="email_from" value="{{ config_data.get('email_from', '') }}" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-2">
                    </div>
                    <button type="submit" class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                        Save Settings
                    </button>
                </form>
            {% endif %}
        </div>
    </div>
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
<script>
        var themeToggleDarkIconAdmin = document.getElementById('theme-toggle-dark-icon-admin');
        var themeToggleLightIconAdmin = document.getElementById('theme-toggle-light-icon-admin');
        if (localStorage.getItem('color-theme') === 'dark' || (!('color-theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            if(themeToggleLightIconAdmin) themeToggleLightIconAdmin.classList.remove('hidden');
        } else {
            if(themeToggleDarkIconAdmin) themeToggleDarkIconAdmin.classList.remove('hidden');
        }
        var themeToggleBtnAdmin = document.getElementById('theme-toggle-admin');
        if(themeToggleBtnAdmin) {
            themeToggleBtnAdmin.addEventListener('click', function() {
                themeToggleDarkIconAdmin.classList.toggle('hidden');
                themeToggleLightIconAdmin.classList.toggle('hidden');
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
        }
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



