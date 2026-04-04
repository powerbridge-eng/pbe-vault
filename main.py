import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION & IDENTITY ---
DATABASE_URL = os.environ.get("DATABASE_URL")
ARKESEL_API_KEY = os.environ.get("ARKESEL_API_KEY")
ARKESEL_SENDER_ID = "PBE_OTP" 
ADMIN_PASSWORD = "PBE-Global-2026" 
SUPERVISOR_PASSWORD = "PBE-Super-2026"
ADMIN_EMAIL = "Powerbridgee@gmail.com"

app = Flask(__name__)
app.secret_key = "PBE_APEX_VANGUARD_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. DATABASE INITIALIZATION (Self-Healing) ---
def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_master_registry (
            id SERIAL PRIMARY KEY, surname TEXT, firstname TEXT, dob TEXT,
            pbe_uid TEXT UNIQUE, pbe_license TEXT, insurance_date TEXT, expiry_date TEXT,
            rank TEXT, phone_no TEXT, photo_url TEXT, ghana_card TEXT,
            otp_code TEXT, status TEXT DEFAULT 'PENDING', region TEXT, department TEXT, ghana_card_photo TEXT
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
    cols = ["dob", "insurance_date", "expiry_date", "ghana_card", "otp_code", "photo_url", "region", "department", "ghana_card_photo"]
    for col in cols:
        cur.execute(f"ALTER TABLE pbe_master_registry ADD COLUMN IF NOT EXISTS {col} TEXT;")
    conn.commit(); cur.close(); conn.close()

with app.app_context():
    init_db()

# --- 3. POWER ENGINE (Security & Intelligence) ---
def is_blocked(ip):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT blocked_until FROM pbe_blacklist WHERE ip_address = %s", (ip,))
    res = cur.fetchone(); cur.close(); conn.close()
    return True if res and res[0] > datetime.datetime.now() else False

def block_ip(ip):
    until = datetime.datetime.now() + datetime.timedelta(days=3)
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_blacklist (ip_address, blocked_until) VALUES (%s, %s) ON CONFLICT (ip_address) DO UPDATE SET blocked_until = %s", (ip, until, until))
    conn.commit(); cur.close(); conn.close()

def log_action(action, details):
    role = session.get('role', 'GUEST')
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_audit_logs (action, details, ip_address, user_role) VALUES (%s, %s, %s, %s)", (action, details, request.remote_addr, role))
    conn.commit(); cur.close(); conn.close()

@app.before_request
def vanguard_gate():
    # 1. EMERGENCY BYPASS (Must stay at the top!)
    if request.args.get('bypass') == 'OPEN': return 
    # 2. GHOST DEFENSE
    if is_blocked(request.remote_addr) and "vanguard" in request.path: abort(404)

# --- 4. THE PBE APP INTERFACE (Mobile Optimized) ---
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>PBE Command Center</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1a3a5a">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; }
        .header { background: #1a3a5a; color: white; padding: 30px; text-align: center; border-bottom: 8px solid #0056b3; }
        .floating-logo { width: 110px; margin-bottom: 10px; }
        .stats { background: #fff; padding: 10px; font-size: 11px; display: flex; justify-content: center; gap: 20px; border-bottom: 1px solid #ddd; font-weight: bold; }
        .container { max-width: 1250px; margin: 20px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
        th, td { border-bottom: 1px solid #eee; padding: 12px; text-align: left; }
        .btn { padding: 8px 14px; border-radius: 6px; text-decoration: none; font-size: 12px; display: inline-block; border: none; color: white; cursor: pointer; font-weight: bold; }
        .btn-blue { background: #0056b3; } .btn-green { background: #28a745; } .btn-red { background: #dc3545; }
        input, select { padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 400px; font-size: 16px; }
    </style>
</head>
<body>
    <div class="header">
        <img src="/static/logo.png" class="floating-logo" onerror="this.src='https://via.placeholder.com/100?text=PBE+LOGO'">
        <h1>PBE APEX COMMAND</h1>
    </div>
    <div class="stats"><span>SMS Credits: {{ sms_bal }}</span><span>Role: {{ role }}</span><span>🛡️ SECURE</span></div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 5. PWA SETUP (Making it an App) ---
@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "PBE Command Center",
        "short_name": "PBE",
        "start_url": "/pbe-vanguard-hq-2026",
        "display": "standalone",
        "background_color": "#1a3a5a",
        "theme_color": "#1a3a5a",
        "icons": [{"src": "https://via.placeholder.com/192?text=PBE", "sizes": "192x192", "type": "image/png"}]
    })

# --- 6. CORE LOGIC ---
@app.route("/pbe-vanguard-hq-2026", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pwd = request.form.get('password')
        if pwd == ADMIN_PASSWORD:
            session['logged_in'], session['role'] = True, 'GENERAL'
            log_action("CEO Login", "Full Clearance")
            return redirect(url_for('admin_dashboard'))
        elif pwd == SUPERVISOR_PASSWORD:
            session['logged_in'], session['role'] = True, 'SUPERVISOR'
            log_action("Supervisor Login", "Limited Access")
            return redirect(url_for('admin_dashboard'))
        else:
            block_ip(request.remote_addr)
            return "<h1>LOCKOUT ENGAGED ❌</h1>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div style="text-align:center; padding:40px;">
            <h2>Enter Command Key</h2>
            <form method="POST"><input type="password" name="password" placeholder="System Key" required><br><br><button class="btn btn-blue">Authorize</button></form>
        </div>
    """), sms_bal="--", role="GUEST")

@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    search = request.args.get('search', '').strip()
    conn = get_db(); cur = conn.cursor()
    if search: cur.execute("SELECT * FROM pbe_master_registry WHERE surname ILIKE %s OR pbe_uid ILIKE %s OR region ILIKE %s ORDER BY id DESC", (f'%{search}%', f'%{search}%', f'%{search}%'))
    else: cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    
    sms_bal = "Offline"
    try: sms_bal = f"{requests.get('https://sms.arkesel.com/api/v2/clients/balance', headers={'api-key': ARKESEL_API_KEY}, timeout=3).json()['data']['balance']} GHS"
    except: pass

    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div style="display:flex; gap:10px; justify-content:center; margin-bottom:20px;">
            <form method="GET"><input name="search" placeholder="Search..." value="{{sq}}" style="width:200px;"><button class="btn btn-blue">Search</button></form>
            <a href="/admin/invite" class="btn btn-green">+ Invite</a>
            {% if role == 'GENERAL' %}<a href="/admin/logs" class="btn btn-blue" style="background:#6c757d;">Logs</a>{% endif %}
            <a href="/logout" class="btn btn-red">Lock</a>
        </div>
        <table>
            <tr><th>UID</th><th>Worker Name</th><th>Dept / Region</th><th>Actions</th></tr>
            {% for w in workers %}
            <tr><td><b>{{ w[4] or 'PENDING' }}</b></td><td>{{ w[1] }}, {{ w[2] }}</td><td>{{ w[15] }} / {{ w[14] }}</td>
            <td>
                <a href="https://wa.me/{{ w[9] }}?text=ID: {{ request.url_root }}verify/{{ w[4] }}" class="btn" style="background:#25D366;" target="_blank">WA</a>
                {% if w[4] %}<a href="/admin/print-id/{{ w[4] }}" class="btn btn-blue">Print</a>{% endif %}
                {% if role == 'GENERAL' %}<a href="/admin/delete/{{ w[0] }}" class="btn btn-red">Del</a>{% endif %}
            </td></tr>{% endfor %}
        </table>
    """), workers=workers, sq=search, sms_bal=sms_bal, role=session['role'])

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(100000, 999999))
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": ARKESEL_SENDER_ID, "message": f"PBE: Use code {otp} at {request.url_root}register", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", "<h3>Invite Worker</h3><form method='POST'><input name='phone' placeholder='233...' required><br><button class='btn btn-blue'>Send SMS</button></form>"), sms_bal="--", role=session['role'])

@app.route("/register", methods=['GET', 'POST'])
def register():
    regions = ["Greater Accra", "Ashanti", "Western", "Volta", "Eastern", "Central", "Northern", "Upper East", "Upper West", "Bono", "Bono East", "Ahafo", "Oti", "Savannah", "North East", "Western North"]
    depts = ["Civil Engineering", "Electrical", "Mechanical", "Structural", "Logistics", "Security"]
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            photo = cloudinary.uploader.upload(request.files['photo'])
            gcard = cloudinary.uploader.upload(request.files['gcard_photo'])
            fname, sname = request.form.get('firstname').upper(), request.form.get('surname').upper()
            uid = f"{fname}{''.join(random.choices(string.ascii_uppercase + string.digits, k=15))}"[:15]
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        ghana_card=%s, photo_url=%s, status='ACTIVE', rank=%s, insurance_date=%s, expiry_date=%s,
                        region=%s, department=%s, ghana_card_photo=%s WHERE otp_code=%s""",
                        (sname, fname, request.form.get('dob'), uid, uid[::-1], request.form.get('ghana_card'),
                        photo['secure_url'], request.form.get('rank'), request.form.get('insurance'),
                        request.form.get('expiry'), request.form.get('region'), request.form.get('department'),
                        gcard['secure_url'], otp))
            conn.commit(); cur.close(); conn.close()
            return "<h2>REGISTRATION SUCCESSFUL ✅</h2>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <h3>Enrollment</h3><form method="POST" enctype="multipart/form-data">
        <input name="otp" placeholder="SMS Code" required><input name="surname" placeholder="Surname" required><input name="firstname" placeholder="First Name" required>
        <select name="region">{''.join([f'<option value="{r}">{r}</option>' for r in regions])}</select>
        <select name="department">{''.join([f'<option value="{d}">{d}</option>' for d in depts])}</select>
        <input name="ghana_card" placeholder="Ghana Card ID"><input name="rank" placeholder="Rank"><input type="date" name="dob">
        <p>Passport Photo:</p><input type="file" name="photo" required><p>Ghana Card Front:</p><input type="file" name="gcard_photo" required>
        <br><button class="btn btn-blue">Register</button></form>
    """), sms_bal="--", role="ENROLLING")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
