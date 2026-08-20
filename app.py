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
    <style>
        .hero-bg {
            background-color: #0f172a;
            background-image: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);
        }
        /* CSS Slider */
        .slider {
            width: 100%;
            height: 400px;
            overflow: hidden;
            border-radius: 1rem;
            position: relative;
        }
        .slides {
            display: flex;
            width: 400%;
            height: 100%;
            animation: slide 20s infinite;
        }
        .slide {
            width: 25%;
            height: 100%;
            background-size: cover;
            background-position: center;
        }
        @keyframes slide {
            0% { transform: translateX(0%); }
            20% { transform: translateX(0%); }
            25% { transform: translateX(-25%); }
            45% { transform: translateX(-25%); }
            50% { transform: translateX(-50%); }
            70% { transform: translateX(-50%); }
            75% { transform: translateX(-75%); }
            95% { transform: translateX(-75%); }
            100% { transform: translateX(0%); }
        }
    </style>
</head>
<body class="bg-gray-50 text-gray-800 font-sans antialiased">
    
    <!-- Navbar -->
    <nav class="bg-white shadow-sm border-b border-gray-100 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16 items-center">
                <div class="flex-shrink-0 flex items-center">
                    <span class="text-2xl font-black text-blue-600 tracking-tighter">Tenders<span class="text-gray-800">Hub</span></span>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="{{ url_for('admin') }}" class="text-gray-500 hover:text-gray-900 text-sm font-medium">Admin Dashboard</a>
                    <a href="?lang=ar" class="text-sm font-medium text-gray-500 hover:text-gray-900">عربي</a>
                    <a href="#subscribe" class="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700">Get Started</a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <div class="hero-bg relative overflow-hidden">
        <div class="max-w-7xl mx-auto">
            <div class="relative z-10 pb-12 sm:pb-16 md:pb-20 lg:max-w-2xl lg:w-full lg:pb-28 xl:pb-32 pt-20">
                <main class="mt-10 mx-auto max-w-7xl px-4 sm:mt-12 sm:px-6 md:mt-16 lg:mt-20 lg:px-8 xl:mt-28">
                    <div class="sm:text-center lg:text-left">
                        <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold text-blue-100 bg-blue-900 mb-4">
                            🚀 The #1 B2B Tender Alert Platform in KSA
                        </span>
                        <h1 class="text-4xl tracking-tight font-extrabold text-white sm:text-5xl md:text-6xl">
                            <span class="block xl:inline">Win more contracts with</span>
                            <span class="block text-blue-400 xl:inline">daily tender reports</span>
                        </h1>
                        <p class="mt-3 text-base text-gray-300 sm:mt-5 sm:text-lg sm:max-w-xl sm:mx-auto md:mt-5 md:text-xl lg:mx-0">
                            Stop manually checking for government contracts. Get beautifully formatted, fully translated daily PDF reports straight to your inbox featuring the latest opportunities from <strong>Forsah.sa</strong> and <strong>Etimad.sa</strong>.
                        </p>
                        <div class="mt-8 sm:flex sm:justify-center lg:justify-start">
                            <div class="rounded-md shadow">
                                <a href="#subscribe" class="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-blue-900 bg-blue-100 hover:bg-blue-200 md:py-4 md:text-lg md:px-10 transition duration-150">
                                    Start 7-Day Free Trial
                                </a>
                            </div>
                            <div class="mt-3 sm:mt-0 sm:ml-3">
                                <a href="#features" class="w-full flex items-center justify-center px-8 py-3 border border-gray-600 text-base font-medium rounded-md text-gray-300 bg-transparent hover:bg-gray-800 md:py-4 md:text-lg md:px-10 transition duration-150">
                                    Learn More
                                </a>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
        </div>
        <div class="lg:absolute lg:inset-y-0 lg:right-0 lg:w-1/2 flex items-center justify-center p-8 lg:p-12 lg:mt-0 hidden lg:flex">
            <!-- Project Image Slider -->
            <div class="slider shadow-2xl border-4 border-gray-800">
                <div class="slides">
                    <div class="slide" style="background-image: url('https://images.unsplash.com/photo-1541888086925-0c13d4f40f0c?auto=format&fit=crop&w=800&q=80');"></div>
                    <div class="slide" style="background-image: url('https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=800&q=80');"></div>
                    <div class="slide" style="background-image: url('https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80');"></div>
                    <div class="slide" style="background-image: url('https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=800&q=80');"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- SEO & Content Section -->
    <div class="py-16 bg-blue-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="lg:text-center">
                <h2 class="text-base text-blue-600 font-semibold tracking-wide uppercase">Saudi Arabia Government Procurement</h2>
                <p class="mt-2 text-3xl leading-8 font-extrabold tracking-tight text-gray-900 sm:text-4xl">
                    Never miss a contracting opportunity
                </p>
                <p class="mt-4 max-w-2xl text-xl text-gray-500 lg:mx-auto">
                    The Saudi Arabian market is expanding rapidly under Vision 2030. Navigating procurement portals like Etimad and Forsah can be time-consuming. We do the heavy lifting by scraping, translating, and curating tenders tailored to your industry, directly into your inbox.
                </p>
            </div>
        </div>
    </div>

    <!-- Features Section -->
    <div id="features" class="py-16 bg-white">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                <div class="bg-gray-50 rounded-xl p-8 border border-gray-100 shadow-sm transition hover:shadow-md">
                    <div class="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-6 text-2xl">📊</div>
                    <h3 class="text-xl font-bold text-gray-900 mb-3">4 Daily Reports</h3>
                    <p class="text-gray-600">Receive comprehensive PDF updates four times a day at 9 AM, 11 AM, 1 PM, and 3 PM.</p>
                </div>
                <div class="bg-gray-50 rounded-xl p-8 border border-gray-100 shadow-sm transition hover:shadow-md">
                    <div class="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-6 text-2xl">🇸🇦</div>
                    <h3 class="text-xl font-bold text-gray-900 mb-3">Etimad & Forsah Coverage</h3>
                    <p class="text-gray-600">Full coverage of the two largest government procurement and enterprise portals in Saudi Arabia.</p>
                </div>
                <div class="bg-gray-50 rounded-xl p-8 border border-gray-100 shadow-sm transition hover:shadow-md">
                    <div class="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-6 text-2xl">🌍</div>
                    <h3 class="text-xl font-bold text-gray-900 mb-3">Instant Translation</h3>
                    <p class="text-gray-600">All Arabic tenders are automatically translated into English, helping international contractors bid seamlessly.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Subscription Form Section -->
    <div id="subscribe" class="bg-gray-900 py-16">
        <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="bg-white rounded-2xl shadow-xl overflow-hidden p-8 border border-blue-100">
                <div class="text-center mb-8">
                    <h2 class="text-3xl font-extrabold text-gray-900">Start Your 1-Week Free Trial</h2>
                    <p class="mt-2 text-gray-600">No credit card required. Experience the full power of daily tender reports completely free for 7 days.</p>
                </div>
                
                {% if success %}
                <div class="bg-green-50 border-l-4 border-green-400 p-4 mb-8">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <span class="text-green-400">✓</span>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm text-green-700 font-medium">
                                Success! Your 7-day free trial has started. Our representative will contact you shortly for further assistance.
                            </p>
                        </div>
                    </div>
                </div>
                {% endif %}

                <form method="POST" action="/subscribe" class="space-y-6">
                    <!-- Pricing Toggle -->
                    <div class="flex justify-center mb-6">
                        <div class="flex space-x-4 bg-gray-100 p-1 rounded-lg">
                            <label class="cursor-pointer relative">
                                <input type="radio" name="subscription_type" value="Monthly" class="peer sr-only" checked>
                                <div class="px-6 py-2 rounded-md peer-checked:bg-blue-600 peer-checked:text-white font-medium text-gray-600 transition-colors">
                                    Monthly Plan (100 SAR/mo after trial)
                                </div>
                            </label>
                            <label class="cursor-pointer relative">
                                <input type="radio" name="subscription_type" value="Annual" class="peer sr-only">
                                <div class="px-6 py-2 rounded-md peer-checked:bg-blue-600 peer-checked:text-white font-medium text-gray-600 transition-colors">
                                    Annual Plan (1000 SAR/yr after trial)
                                </div>
                            </label>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Company Name *</label>
                            <input type="text" name="name" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Email Address *</label>
                            <input type="email" name="email" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Phone Number *</label>
                            <input type="text" name="phone" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">CR Number</label>
                            <input type="text" name="cr_number" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Contact Person *</label>
                            <input type="text" name="contact_person" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Industry / Category</label>
                            <input type="text" name="industry" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div class="md:col-span-2">
                            <label class="block text-sm font-medium text-gray-700">Preferred Language</label>
                            <select name="language" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                                <option value="English">English</option>
                                <option value="Arabic">Arabic</option>
                            </select>
                        </div>
                    </div>
                    <div class="pt-4">
                        <button type="submit" class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-lg font-bold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition duration-150">
                            Start 7-Day Free Trial
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="bg-gray-900 py-8 border-t border-gray-800">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center flex flex-col items-center">
            <span class="text-xl font-black text-gray-400 tracking-tighter mb-4">Tenders<span class="text-white">Hub</span></span>
            <p class="text-gray-500 text-sm mb-4">Connecting your business with the best procurement opportunities in Saudi Arabia.</p>
            <p class="text-gray-600 text-xs">&copy; 2026 TendersHub. All rights reserved.</p>
        </div>
    </footer>
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
    <style>
        .hero-bg {
            background-color: #0f172a;
            background-image: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);
        }
        /* CSS Slider */
        .slider {
            width: 100%;
            height: 400px;
            overflow: hidden;
            border-radius: 1rem;
            position: relative;
        }
        .slides {
            display: flex;
            width: 400%;
            height: 100%;
            animation: slide 20s infinite;
        }
        .slide {
            width: 25%;
            height: 100%;
            background-size: cover;
            background-position: center;
        }
        @keyframes slide {
            0% { transform: translateX(0%); }
            20% { transform: translateX(0%); }
            25% { transform: translateX(-25%); }
            45% { transform: translateX(-25%); }
            50% { transform: translateX(-50%); }
            70% { transform: translateX(-50%); }
            75% { transform: translateX(-75%); }
            95% { transform: translateX(-75%); }
            100% { transform: translateX(0%); }
        }
    </style>
</head>
<body class="bg-gray-50 text-gray-800 font-sans antialiased">
    
    <!-- Navbar -->
    <nav class="bg-white shadow-sm border-b border-gray-100 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16 items-center">
                <div class="flex-shrink-0 flex items-center">
                    <span class="text-2xl font-black text-blue-600 tracking-tighter">Tenders<span class="text-gray-800">Hub</span></span>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="{{ url_for('admin') }}" class="text-gray-500 hover:text-gray-900 text-sm font-medium">لوحة الإدارة</a>
                    <a href="?lang=en" class="text-sm font-medium text-gray-500 hover:text-gray-900">English</a>
                    <a href="#subscribe" class="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700">ابدأ الآن</a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <div class="hero-bg relative overflow-hidden">
        <div class="max-w-7xl mx-auto">
            <div class="relative z-10 pb-12 sm:pb-16 md:pb-20 lg:max-w-2xl lg:w-full lg:pb-28 xl:pb-32 pt-20">
                <main class="mt-10 mx-auto max-w-7xl px-4 sm:mt-12 sm:px-6 md:mt-16 lg:mt-20 lg:px-8 xl:mt-28">
                    <div class="sm:text-center lg:text-right">
                        <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold text-blue-100 bg-blue-900 mb-4">
                            🚀 🚀 المنصة الأولى للتنبيه بالمناقصات للشركات في السعودية
                        </span>
                        <h1 class="text-4xl tracking-tight font-extrabold text-white sm:text-5xl md:text-6xl">
                            <span class="block xl:inline">اربح المزيد من العقود مع</span>
                            <span class="block text-blue-400 xl:inline">تقارير المناقصات اليومية</span>
                        </h1>
                        <p class="mt-3 text-base text-gray-300 sm:mt-5 sm:text-lg sm:max-w-xl sm:mx-auto md:mt-5 md:text-xl lg:mx-0">
                            توقف عن البحث اليدوي عن العقود الحكومية. احصل على تقارير يومية منسقة بصيغة PDF مباشرة إلى بريدك الإلكتروني لأحدث الفرص من <strong>منصة فرصة</strong> و<strong>اعتماد</strong>.
                        </p>
                        <div class="mt-8 sm:flex sm:justify-center lg:justify-start">
                            <div class="rounded-md shadow">
                                <a href="#subscribe" class="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-blue-900 bg-blue-100 hover:bg-blue-200 md:py-4 md:text-lg md:px-10 transition duration-150">
                                    ابدأ تجربتك المجانية لمدة 7 أيام
                                </a>
                            </div>
                            <div class="mt-3 sm:mt-0 sm:ml-3">
                                <a href="#features" class="w-full flex items-center justify-center px-8 py-3 border border-gray-600 text-base font-medium rounded-md text-gray-300 bg-transparent hover:bg-gray-800 md:py-4 md:text-lg md:px-10 transition duration-150">
                                    اعرف المزيد
                                </a>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
        </div>
        <div class="lg:absolute lg:inset-y-0 lg:right-0 lg:w-1/2 flex items-center justify-center p-8 lg:p-12 lg:mt-0 hidden lg:flex">
            <!-- Project Image Slider -->
            <div class="slider shadow-2xl border-4 border-gray-800">
                <div class="slides">
                    <div class="slide" style="background-image: url('https://images.unsplash.com/photo-1541888086925-0c13d4f40f0c?auto=format&fit=crop&w=800&q=80');"></div>
                    <div class="slide" style="background-image: url('https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=800&q=80');"></div>
                    <div class="slide" style="background-image: url('https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&q=80');"></div>
                    <div class="slide" style="background-image: url('https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=800&q=80');"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- SEO & Content Section -->
    <div class="py-16 bg-blue-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="lg:text-center">
                <h2 class="text-base text-blue-600 font-semibold tracking-wide uppercase">المشتريات الحكومية في السعودية</h2>
                <p class="mt-2 text-3xl leading-8 font-extrabold tracking-tight text-gray-900 sm:text-4xl">
                    لا تفوت أي فرصة تعاقد
                </p>
                <p class="mt-4 max-w-2xl text-xl text-gray-500 lg:mx-auto">
                    السوق السعودي يتوسع بسرعة في ظل رؤية 2030. تصفح المنصات مثل اعتماد وفرصة يستغرق وقتاً طويلاً. نحن نقوم بالعمل الشاق من خلال استخراج وترجمة وتنسيق المناقصات وإرسالها مباشرة إلى بريدك.
                </p>
            </div>
        </div>
    </div>

    <!-- Features Section -->
    <div id="features" class="py-16 bg-white">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                <div class="bg-gray-50 rounded-xl p-8 border border-gray-100 shadow-sm transition hover:shadow-md">
                    <div class="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-6 text-2xl">📊</div>
                    <h3 class="text-xl font-bold text-gray-900 mb-3">4 تقارير يومية</h3>
                    <p class="text-gray-600">احصل على تحديثات شاملة 4 مرات يومياً.</p>
                </div>
                <div class="bg-gray-50 rounded-xl p-8 border border-gray-100 shadow-sm transition hover:shadow-md">
                    <div class="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-6 text-2xl">🇸🇦</div>
                    <h3 class="text-xl font-bold text-gray-900 mb-3">تغطية شاملة لاعتماد وفرصة</h3>
                    <p class="text-gray-600">تغطية كاملة لأكبر منصات المشتريات الحكومية في المملكة.</p>
                </div>
                <div class="bg-gray-50 rounded-xl p-8 border border-gray-100 shadow-sm transition hover:shadow-md">
                    <div class="w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-6 text-2xl">🌍</div>
                    <h3 class="text-xl font-bold text-gray-900 mb-3">ترجمة فورية</h3>
                    <p class="text-gray-600">تتم ترجمة جميع المناقصات تلقائياً لتسهيل العمل.</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Subscription Form Section -->
    <div id="subscribe" class="bg-gray-900 py-16">
        <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="bg-white rounded-2xl shadow-xl overflow-hidden p-8 border border-blue-100">
                <div class="text-center mb-8">
                    <h2 class="text-3xl font-extrabold text-gray-900">ابدأ تجربتك المجانية لمدة أسبوع</h2>
                    <p class="mt-2 text-gray-600">No credit card required. Experience the full power of تقارير المناقصات اليومية completely free for 7 days.</p>
                </div>
                
                {% if success %}
                <div class="bg-green-50 border-l-4 border-green-400 p-4 mb-8">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <span class="text-green-400">✓</span>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm text-green-700 font-medium">
                                نجاح! بدأت تجربتك المجانية لمدة 7 أيام. سيتواصل معك مندوبنا قريباً.
                            </p>
                        </div>
                    </div>
                </div>
                {% endif %}

                <form method="POST" action="/subscribe" class="space-y-6">
                    <!-- Pricing Toggle -->
                    <div class="flex justify-center mb-6">
                        <div class="flex space-x-4 bg-gray-100 p-1 rounded-lg">
                            <label class="cursor-pointer relative">
                                <input type="radio" name="subscription_type" value="Monthly" class="peer sr-only" checked>
                                <div class="px-6 py-2 rounded-md peer-checked:bg-blue-600 peer-checked:text-white font-medium text-gray-600 transition-colors">
                                    الباقة الشهرية (100 ريال شهرياً بعد التجربة)
                                </div>
                            </label>
                            <label class="cursor-pointer relative">
                                <input type="radio" name="subscription_type" value="Annual" class="peer sr-only">
                                <div class="px-6 py-2 rounded-md peer-checked:bg-blue-600 peer-checked:text-white font-medium text-gray-600 transition-colors">
                                    الباقة السنوية (1000 ريال سنوياً بعد التجربة)
                                </div>
                            </label>
                        </div>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label class="block text-sm font-medium text-gray-700">اسم الشركة *</label>
                            <input type="text" name="name" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">البريد الإلكتروني *</label>
                            <input type="email" name="email" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">رقم الجوال *</label>
                            <input type="text" name="phone" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">رقم السجل التجاري</label>
                            <input type="text" name="cr_number" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">الشخص المسؤول *</label>
                            <input type="text" name="contact_person" required class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">مجال العمل / التصنيف</label>
                            <input type="text" name="industry" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                        </div>
                        <div class="md:col-span-2">
                            <label class="block text-sm font-medium text-gray-700">اللغة المفضلة للتقارير</label>
                            <select name="language" class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm border p-3 bg-gray-50">
                                <option value="الإنجليزية">الإنجليزية</option>
                                <option value="العربية">العربية</option>
                            </select>
                        </div>
                    </div>
                    <div class="pt-4">
                        <button type="submit" class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-lg font-bold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition duration-150">
                            ابدأ تجربتك المجانية لمدة 7 أيام
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="bg-gray-900 py-8 border-t border-gray-800">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center flex flex-col items-center">
            <span class="text-xl font-black text-gray-400 tracking-tighter mb-4">Tenders<span class="text-white">Hub</span></span>
            <p class="text-gray-500 text-sm mb-4">Connecting your business with the best procurement opportunities in Saudi Arabia.</p>
            <p class="text-gray-600 text-xs">&copy; 2026 تندرز هب. All rights reserved.</p>
        </div>
    </footer>
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
    <nav class="bg-white shadow-sm border-b border-gray-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16 items-center">
                <div class="flex-shrink-0 flex items-center">
                    <span class="text-2xl font-black text-blue-600 tracking-tighter">Tenders<span class="text-gray-800">Hub</span> <span class="text-sm font-normal text-gray-500 ml-2">Admin</span></span>
                </div>
                <div>
                    <a href="{{ url_for('index') }}" class="text-sm font-medium text-gray-500 hover:text-gray-900">View Live Site</a>
                </div>
            </div>
        </div>
    </nav>
    <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div class="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
            
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
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Company</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan & Details</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            {% for c in companies %}
                            <tr>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="font-medium text-gray-900">{{ c['name'] }}</div>
                                    <div class="text-sm text-gray-500">CR: {{ c['cr_number'] }}</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">{{ c['email'] }}</div>
                                    <div class="text-sm text-gray-500">{{ c['contact_person'] }} - {{ c['phone'] }}</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-semibold text-blue-600">{{ c['subscription_type'] or 'Monthly' }}</div>
                                    <div class="text-xs text-gray-500">{{ c['industry'] }} | {{ c['language'] }}</div>
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

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)


