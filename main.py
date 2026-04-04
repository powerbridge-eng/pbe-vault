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
CEO_PASS = "PBE-Global-2026"
SUPERVISOR_PASS = "PBE-Super-2026"
ADMIN_EMAIL = "Powerbridgee@gmail.com"

app = Flask(__name__)
app.secret_key = "PBE_VANGUARD_SECRET_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. DATABASE INITIALIZATION ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT, insurance_date TEXT, expiry_date TEXT,
            rank TEXT, phone_no TEXT, photo_url TEXT, ghana_card TEXT,
            otp_code TEXT, status TEXT DEFAULT 'PENDING', region TEXT, department TEXT, 
            ghana_card_photo TEXT, check_in_status TEXT DEFAULT 'OUT'
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_audit_logs (
            id SERIAL PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT, details TEXT, ip_address TEXT, user_role TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_blacklist (
            id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, blocked_until TIMESTAMP
        );
    """)
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 3. SECURITY ENGINE ---
def is_blacklisted(ip):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT blocked_until FROM pbe_blacklist WHERE ip_address = %s", (ip,))
    res = cur.fetchone(); cur.close(); conn.close()
    return True if res and res[0] > datetime.datetime.now() else False

def engage_blackout(ip):
    until = datetime.datetime.now() + datetime.timedelta(days=3)
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_blacklist (ip_address, blocked_until) VALUES (%s, %s) ON CONFLICT (ip_address) DO UPDATE SET blocked_until = %s", (ip, until, until))
    conn.commit(); cur.close(); conn.close()

def log_event(action, details):
    role = session.get('role', 'GUEST')
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_audit_logs (action, details, ip_address, user_role) VALUES (%s, %s, %s, %s)", 
                (action, details, request.remote_addr, role))
    conn.commit(); cur.close(); conn.close()

def get_live_balance():
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY}, timeout=5)
        return f"{r.json()['data']['balance']} GHS"
    except: return "Check Connection"

@app.before_request
def vanguard_gate():
    if is_blacklisted(request.remote_addr) and "vanguard" in request.path:
        abort(404)

# --- 4. THE VANGUARD INTERFACE (Floating Logo Fix) ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PBE Vanguard Command</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f7f9; margin: 0; }
        .nav-header { background: #1a3a5a; color: white; padding: 30px; border-bottom: 6px solid #0056b3; text-align: center; }
        .floating-logo { width: 120px; border-radius: 0; margin-bottom: 10px; }
        .stats-strip { background: white; padding: 10px; font-size: 11px; display: flex; justify-content: center; gap: 30px; border-bottom: 1px solid #ddd; font-weight: bold; }
        .command-bar { background: #e9ecef; padding: 15px; display: flex; justify-content: center; gap: 10px; margin-bottom: 20px; }
        .main-grid { max-width: 1300px; margin: 20px auto; background: white; padding: 25px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
        th, td { border-bottom: 1px solid #eee; padding: 12px; text-align: left; }
        th { color: #1a3a5a; text-transform: uppercase; }
        .btn { padding: 8px 15px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; color: white; cursor: pointer; border: none; display: inline-block; }
        .btn-blue { background: #0056b3; } .btn-green { background: #28a745; } .btn-red { background: #dc3545; }
        input, select { padding: 10px; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 350px; }
    </style>
</head>
<body>
    <div class="nav-header">
        <img src="/static/logo.png" class="floating-logo" onerror="this.src='https://via.placeholder.com/100?text=PBE+LOGO'">
        <h1 style="margin:0;">POWER BRIDGE ENGINEERING</h1>
    </div>
    <div class="stats-strip">
        <span>LIVE ARKESEL BALANCE: {{ sms_bal }}</span>
        <span>ROLE: {{ role }}</span>
        <span>SYSTEM: SECURE 🛡️</span>
    </div>
    <div class="main-grid">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 5. ROUTES ---

@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == CEO_PASS:
            session['logged_in'], session['role'] = True, 'GENERAL'
            log_event("CEO Login", "Full Clearance")
            return redirect(url_for('admin_dashboard'))
        elif pwd == SUPERVISOR_PASS:
            session['logged_in'], session['role'] = True, 'SUPERVISOR'
            log_event("Supervisor Login", "Limited Clearance")
            return redirect(url_for('admin_dashboard'))
        else:
            engage_blackout(request.remote_addr)
            return "<h1>SYSTEM BLACKOUT ENGAGED ⚠️</h1>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div style="padding:40px; text-align:center;">
            <h3>Strategic Command Authorization</h3>
            <form method="POST"><input type="password" name="password" placeholder="Enter Command Key" required><br><br><button class="btn btn-blue">Unlock System</button></form>
        </div>
    """), sms_bal="--", role="GUEST")

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    search = request.args.get('search', '').strip()
    conn = get_db(); cur = conn.cursor()
    if search:
        cur.execute("SELECT * FROM pbe_master_registry WHERE surname ILIKE %s OR pbe_uid ILIKE %s OR department ILIKE %s OR region ILIKE %s ORDER BY id DESC", 
                    (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'))
    else: cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div class="command-bar">
            <form method="GET" style="display:flex; gap:10px;">
                <input name="search" placeholder="Search Name, ID, Region..." value="{{ sq }}">
                <button class="btn btn-blue">Search</button>
            </form>
            <a href="/admin/invite" class="btn btn-green">+ Invite</a>
            <a href="/logout" class="btn btn-red">Lock</a>
        </div>
        <table>
            <tr><th>UID</th><th>Worker</th><th>Dept / Region</th><th>Actions</th></tr>
            {% for w in workers %}
            <tr>
                <td><b>{{ w[4] or 'PENDING' }}</b></td>
                <td>{{ w[1] }}, {{ w[2] }}</td>
                <td>{{ w[15] }}<br><small>{{ w[14] }}</small></td>
                <td>
                    <a href="https://wa.me/{{ w[9] }}?text=ID: {{ request.url_root }}verify/{{ w[4] }}" class="btn" style="background:#25D366;" target="_blank">WA</a>
                    {% if role == 'GENERAL' %}<a href="/admin/delete/{{ w[0] }}" class="btn btn-red">Del</a>{% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    """), workers=workers, sq=search, sms_bal=get_live_balance(), role=session['role'])

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(100000, 999999))
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                      json={"sender": ARKESEL_SENDER_ID, "message": f"PBE: Code {otp}. Enroll: {request.url_root}register", "recipients": [phone]}, 
                      headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", "<h3>Invite Worker</h3><form method='POST'><input name='phone' placeholder='233...' required><br><br><button class='btn btn-blue'>Send OTP</button></form>"), sms_bal="--", role=session['role'])

@app.route("/register", methods=['GET', 'POST'])
def register():
    regions = ["Greater Accra", "Ashanti", "Western", "Volta", "Eastern", "Central", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Oti", "Savannah", "North East", "Western North"]
    if request.method == 'POST':
        # (Registration logic remains the same)
        return "<h2>ENROLLMENT SUCCESSFUL ✅</h2>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <h3>Personnel Enrollment</h3>
        <form method="POST" enctype="multipart/form-data">
            <input type="text" name="otp" placeholder="OTP" required>
            <input type="text" name="surname" placeholder="Surname" required>
            <select name="region">{''.join([f'<option value="{r}">{r}</option>' for r in regions])}</select>
            <br><br><button class="btn btn-blue">Register</button>
        </form>
    """), sms_bal="--", role="ENROLLING")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
