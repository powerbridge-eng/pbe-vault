import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime, csv
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO, StringIO

# --- 1. CORE INTEGRATION ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OTP" 
ADMIN_PASSWORD = "PBE-Global-2026"

app = Flask(__name__)
app.secret_key = "PBE_STRATEGIC_VANGUARD_FINAL_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. DATABASE & TERRITORIAL GPS TRACKER ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT, gender TEXT, nationality TEXT, 
            pbe_uid TEXT UNIQUE, pbe_license TEXT UNIQUE, issuance_date DATE, expiry_date DATE, 
            rank TEXT, department TEXT, phone_no TEXT, photo_url TEXT, status TEXT DEFAULT 'PENDING', 
            otp_code TEXT, region TEXT, station TEXT, scans INT DEFAULT 0
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_soul_audit (
            id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            action TEXT, details TEXT, ip_address TEXT, device_info TEXT, geo_location TEXT
        );
    """)
    conn.commit(); cur.close(); conn.close()

def log_soul_action(action, details):
    ip = request.remote_addr
    location = "HQ_SECURE_ZONE"
    try:
        # REAL-TIME GPS TRACKING
        geo = requests.get(f"http://ip-api.com/json/{ip}?fields=status,city,regionName,lat,lon", timeout=3).json()
        if geo['status'] == 'success':
            location = f"{geo['city']}, {geo['regionName']} ({geo['lat']}, {geo['lon']})"
    except: location = "LOC_MASKED"

    device = f"{request.user_agent.platform} | {request.user_agent.browser}"
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_soul_audit (action, details, ip_address, device_info, geo_location) VALUES (%s, %s, %s, %s, %s)",
                (action, details, ip, device, location))
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 3. CLOAKED INTERFACE (STANDALONE LOGO) ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>PBE Command</title>
    <style>
        :root { --navy: #0a192f; --gold: #ffcc00; --red: #e63946; --green: #25D366; --blue: #007bff; --slate: #f1f5f9; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--slate); margin: 0; padding-bottom: 80px; }
        .header { background: var(--navy); color: white; padding: 25px; text-align: center; border-bottom: 5px solid var(--gold); }
        .logo-standalone { height: 75px; margin-bottom: 10px; background: transparent !important; filter: drop-shadow(0 0 0 transparent); }
        .container { max-width: 1200px; margin: auto; padding: 15px; }
        .layer { background: white; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .btn-cmd { padding: 10px 15px; border-radius: 8px; color: white; text-decoration: none; font-size: 11px; font-weight: bold; border: none; cursor: pointer; display: inline-block; }
        .bg-navy { background: var(--navy); } .bg-blue { background: var(--blue); } .bg-red { background: var(--red); }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th, td { padding: 10px; border-bottom: 1px solid #eee; text-align: left; }
        .geo-tag { color: var(--red); font-weight: bold; font-family: monospace; }
    </style>
</head>
<body>
    <div class="header">
        <img src="{{ url_for('static', filename='logo.png') }}" class="logo-standalone">
        <div style="font-size: 22px; font-weight: 900; letter-spacing: 1px;">POWER BRIDGE ENGINEERING</div>
    </div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 4. ROUTES (FIXED ENDPOINTS) ---

@app.route("/")
def home(): 
    return redirect(url_for('personnel_register'))

@app.route("/enroll", methods=['GET', 'POST'])
def personnel_register():
    if request.method == 'POST':
        # Registration logic...
        pass
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<h3>Personnel Enrollment</h3>'))

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            log_soul_action("HQ_ENTRY", "Admin Authenticated")
            return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<div class="layer" style="max-width:350px; margin: 80px auto; text-align:center;"><h3>HQ LOGIN</h3><form method="POST"><input type="password" name="password" style="width:100%; padding:15px; margin-bottom:15px;" required><button class="btn-cmd bg-navy" style="width:100%;">UNLOCK</button></form></div>'))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): abort(404)
    # Fetch balance and workers...
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<h3>Admin Dashboard</h3>'))

@app.route("/admin/audit-logs")
def audit_logs():
    if not session.get('logged_in'): abort(404)
    # Fetch logs with geolocation...
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", '<h3>Territorial Audit Logs</h3>'))

# --- 5. PRINT ENGINE (BACKGROUND REMOVAL) ---
@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('logged_in'): abort(404)
    # Logic to fetch worker and template...
    # Uses mask='auto' to strip passport background and blend with template
    pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
