import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY") 
ADMIN_PASSWORD = "PBE-Global-2026"

app = Flask(__name__)
app.secret_key = "PBE_HYBRID_STABLE_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db(): return psycopg2.connect(DATABASE_URL)

PBE_GUILDS = ["ELECTRICAL ENGINEERING", "SOLAR & ENERGY", "PLUMBING & HYDRAULICS", "MASONRY & CONSTRUCTION", "MECHANICAL & AUTO", "PBE TV", "CCTV & SECURITY", "ICT & SOFTWARE", "HVAC & COOLING", "FASHION DESIGN", "GENERAL TECHNICAL"]
GH_REGIONS = ["Greater Accra", "Ashanti", "Western", "Central", "Eastern", "Volta", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Savannah", "North East", "Oti", "Western North"]

# --- 2. SELF-HEALING SYSTEM (The Doctor) ---
def perform_self_heal():
    conn = get_db(); cur = conn.cursor()
    # Forces columns to exist so the system NEVER crashes on login
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, 
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, rank TEXT, department TEXT,
            phone_no TEXT UNIQUE, email TEXT UNIQUE, ghana_card TEXT UNIQUE, 
            photo_url TEXT, status TEXT DEFAULT 'PENDING', otp_code TEXT, 
            region TEXT, issuance_date DATE, expiry_date DATE
        );
        CREATE TABLE IF NOT EXISTS pbe_soul_audit (
            id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            action TEXT, actor TEXT, details TEXT, ip TEXT, device TEXT
        );
    """)
    conn.commit(); cur.close(); conn.close()

with app.app_context(): perform_self_heal()

# --- 3. HYBRID ARKESEL PULL (Works with V1 or V2 Keys) ---
def get_arkesel_balance():
    # Try V2 first
    try:
        r2 = requests.get(f"https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=3)
        if r2.status_code == 200:
            return f"{r2.json().get('data', {}).get('available_balance', '0.00')} GHS"
    except: pass
    
    # Fallback to V1 logic if V2 fails
    try:
        r1 = requests.get(f"https://sms.arkesel.com/api/v1/check-balance?api_key={ARKESEL_API_KEY}&response=json", timeout=3)
        if r1.status_code == 200:
            return f"{r1.json().get('balance', '0.00')} GHS"
    except: pass
    
    return "Offline"

# --- 4. PERSONNEL REGISTRY FORM (The missing part) ---
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if not cur.fetchone(): return "INVALID OTP."
        
        photo = cloudinary.uploader.upload(request.files['photo'])
        
        # ID logic: PBE + Year/Month + 3 letters + Random numbers (15 total)
        now = datetime.datetime.now()
        uid = f"PBE{now.strftime('%y%m')}{request.form.get('firstname')[:3].upper()}{''.join(random.choices(string.digits, k=6))}"
        lic = f"PBELIC{request.form.get('surname')[:3].upper()}{''.join(random.choices(string.digits, k=6))}"
        
        cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, pbe_uid=%s, pbe_license=%s, 
                    rank=%s, department=%s, phone_no=%s, email=%s, ghana_card=%s, photo_url=%s, 
                    region=%s, issuance_date=%s, expiry_date=%s WHERE otp_code=%s""",
                   (request.form.get('surname').upper(), request.form.get('firstname').upper(), uid, lic,
                    request.form.get('rank'), request.form.get('department'), request.form.get('phone'),
                    request.form.get('email'), request.form.get('ghana_card'), photo['secure_url'],
                    request.form.get('region'), datetime.date.today(), datetime.date.today() + datetime.timedelta(days=730), otp))
        conn.commit(); cur.close(); conn.close()
        return "SUCCESSFULLY REGISTERED ✅"

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="layer-box" style="max-width:500px; margin:auto;">
            <h3>PBE PERSONNEL REGISTRY FORM</h3>
            <form method="POST" enctype="multipart/form-data">
                <input name="otp" placeholder="Enter OTP from SMS" class="search-input" required style="margin-bottom:10px;">
                <input name="firstname" placeholder="First Name" class="search-input" required style="margin-bottom:10px;">
                <input name="surname" placeholder="Surname" class="search-input" required style="margin-bottom:10px;">
                <select name="region" class="search-input" style="margin-bottom:10px;">
                    {% for r in regions %}<option value="{{r}}">{{r}}</option>{% endfor %}
                </select>
                <select name="department" class="search-input" style="margin-bottom:10px;">
                    {% for g in guilds %}<option value="{{g}}">{{g}}</option>{% endfor %}
                </select>
                <input name="rank" placeholder="Job Rank (e.g. Technician)" class="search-input" required style="margin-bottom:10px;">
                <input name="phone" placeholder="Phone (233...)" class="search-input" required style="margin-bottom:10px;">
                <input name="email" type="email" placeholder="Email Address" class="search-input" required style="margin-bottom:10px;">
                <input name="ghana_card" placeholder="Ghana Card ID" class="search-input" required style="margin-bottom:10px;">
                <p>Upload Passport Photo:</p><input type="file" name="photo" required>
                <button class="btn-6 bg-navy" style="width:100%; padding:15px; margin-top:15px;">SUBMIT MY REGISTRY</button>
            </form>
        </div>
    """), guilds=PBE_GUILDS, regions=GH_REGIONS)

# --- 5. DASHBOARD LAYERS ---
@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('role'): return redirect(url_for('admin_login'))
    
    sms_bal = get_arkesel_balance()

    conn = get_db(); cur = conn.cursor()
    reg_counts = {r: 0 for r in GH_REGIONS}
    for r in GH_REGIONS:
        cur.execute("SELECT COUNT(*) FROM pbe_master_registry WHERE region = %s", (r,))
        reg_counts[r] = cur.fetchone()[0]

    cur.execute("SELECT * FROM pbe_master_registry WHERE surname IS NOT NULL ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <div style="display:flex; gap:10px; margin-bottom:15px;">
            <input type="text" id="gSearch" class="search-input" placeholder="Search Personnel Registry..." onkeyup="runSearch()">
            <div style="background:white; padding:15px; border-radius:10px; border:1px solid #ddd; white-space:nowrap; font-size:13px;">SMS Balance: <b style="color:green;">{sms_bal}</b></div>
        </div>

        <div class="layer-box">
            <div class="layer-title">🌍 GHANA REGIONAL DISTRIBUTION (16 REGIONS)</div>
            <div class="matrix-grid">
                {{% for reg, count in stats.items() %}}
                <div class="matrix-btn" style="text-align:left;">{{{{reg}}}}: <b style="color:red; float:right;">{{{{count}}}}</b></div>
                {{% endfor %}}
            </div>
        </div>
        
        <a href="/admin/invite" class="fab">+</a>
    """), guilds=PBE_GUILDS, workers=workers, stats=reg_counts)

# [Remaining Header/Login Logic]
