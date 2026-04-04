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
ARKESEL_SENDER_ID = "PBE_OTP" 
ADMIN_PASSWORD = "PBE-Global-2026" 
SUPERVISOR_PASSWORD = "PBE-Super-2026"

app = Flask(__name__)
app.secret_key = "PBE_SUPREME_FINAL_FIX_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. THE GROUND ZERO RESET ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS pbe_master_registry, pbe_blacklist, pbe_audit_logs CASCADE;")
    cur.execute("""
        CREATE TABLE pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT, insurance_date TEXT, expiry_date TEXT,
            rank TEXT, phone_no TEXT, photo_url TEXT, ghana_card TEXT,
            otp_code TEXT, status TEXT DEFAULT 'PENDING', region TEXT, department TEXT, 
            ghana_card_photo TEXT
        );
    """)
    cur.execute("CREATE TABLE pbe_blacklist (id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, blocked_until TIMESTAMP);")
    cur.execute("CREATE TABLE pbe_audit_logs (id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, action TEXT, details TEXT, ip_address TEXT, user_role TEXT);")
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 3. SECURITY LOGIC ---
def is_blocked(ip):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT blocked_until FROM pbe_blacklist WHERE ip_address = %s", (ip,))
    res = cur.fetchone(); cur.close(); conn.close()
    return True if res and res[0] > datetime.datetime.now() else False

def engage_lockout(ip):
    until = datetime.datetime.now() + datetime.timedelta(days=3)
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_blacklist (ip_address, blocked_until) VALUES (%s, %s) ON CONFLICT (ip_address) DO UPDATE SET blocked_until = %s", (ip, until, until))
    conn.commit(); cur.close(); conn.close()

# --- 4. GHOST BYPASS & REDIRECT ---
@app.route("/")
def index():
    # Force anyone visiting the base URL to the login page
    return redirect(url_for('login'))

@app.before_request
def vanguard_gate():
    if request.args.get('bypass') == 'OPEN': return 
    if is_blocked(request.remote_addr) and ("vanguard" in request.path or "admin" in request.path):
        abort(404)

# --- 5. UI DESIGN ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head><title>PBE Supreme Command</title><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; text-align: center; }
    .header { background: #1a3a5a; color: white; padding: 30px; border-bottom: 8px solid #0056b3; }
    .container { max-width: 1100px; margin: 20px auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .btn { padding: 12px 24px; border-radius: 6px; color: white; font-weight: bold; border: none; cursor: pointer; text-decoration: none; display: inline-block; }
    .btn-blue { background: #0056b3; }
    input { padding: 15px; border: 1px solid #ddd; width: 100%; max-width: 400px; border-radius: 6px; font-size: 16px; }
</style>
</head>
<body>
    <div class="header"><h1>POWER BRIDGE ENGINEERING</h1><p>SUPREME COMMAND</p></div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == ADMIN_PASSWORD:
            session['logged_in'], session['role'] = True, 'GENERAL'
            return redirect(url_for('admin_dashboard'))
        else:
            engage_lockout(request.remote_addr)
            return "<h1>SECURITY LOCKOUT ENGAGED ❌</h1>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h2>Secure Authorization</h2>
        <form method="POST"><input type="password" name="password" placeholder="Master Key" required><br><br><button class="btn btn-blue">Authorize</button></form>
    """))

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h2>Welcome, General. System is clear.</h2>
        <a href="/logout" class="btn btn-blue" style="background:#333;">Lock</a>
    """))

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for('login'))

if __name__ == "__main__":
    # PORT BINDING FIX FOR RENDER
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
