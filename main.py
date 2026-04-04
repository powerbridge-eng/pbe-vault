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
ADMIN_EMAIL = "Powerbridgee@gmail.com"

app = Flask(__name__)
app.secret_key = "PBE_SUPER_POWER_KEY_2026"

cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- 2. DATABASE INITIALIZATION (Self-Healing & Hardened) ---
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
            action TEXT, details TEXT, ip_address TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pbe_blacklist (
            id SERIAL PRIMARY KEY, ip_address TEXT UNIQUE, blocked_until TIMESTAMP
        );
    """)
    # Ensure all columns exist for Phase 2 data
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
    requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": ARKESEL_SENDER_ID, "message": f"PBE SECURITY: IP {ip} blocked for 3 days after failed breach attempt.", "recipients": ["23324XXXXXXX"]}, headers={"api-key": ARKESEL_API_KEY})

def log_action(action, details):
    ip = request.remote_addr
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO pbe_audit_logs (action, details, ip_address) VALUES (%s, %s, %s)", (action, details, ip))
    conn.commit(); cur.close(); conn.close()

def get_sms_balance():
    try:
        r = requests.get("https://sms.arkesel.com/api/v2/clients/balance", headers={"api-key": ARKESEL_API_KEY})
        return r.json().get('data', {}).get('balance', '0.00')
    except: return "Offline"

def generate_pbe_code(name):
    clean = re.sub(r'[^a-zA-Z]', '', name).upper()
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))
    return f"{clean}{rand}"[:15]

@app.before_request
def security_gate():
    if is_blocked(request.remote_addr) and "/admin" in request.path:
        abort(404)

# --- 4. UI DESIGN ---
BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>PBE Command Center</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; }
        .header { background: #1a3a5a; color: white; padding: 25px; text-align: center; border-bottom: 8px solid #0056b3; }
        .logo-box { background: white; width: 90px; height: 90px; margin: 0 auto 10px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .logo-box img { width: 70px; }
        .stats { background: #fff; padding: 10px; font-size: 12px; display: flex; justify-content: center; gap: 20px; border-bottom: 1px solid #ddd; }
        .container { max-width: 1200px; margin: 20px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
        th, td { border-bottom: 1px solid #eee; padding: 12px; text-align: left; }
        .btn { padding: 8px 14px; border-radius: 6px; text-decoration: none; font-size: 12px; display: inline-block; border: none; color: white; cursor: pointer; font-weight: bold; }
        .btn-blue { background: #0056b3; } .btn-green { background: #28a745; } .btn-red { background: #dc3545; }
        input, select { padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 450px; font-size: 16px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-box"><img src="/static/logo.png" onerror="this.src='https://via.placeholder.com/80?text=PBE'"></div>
        <h1>POWER BRIDGE ENGINEERING</h1>
    </div>
    <div class="stats"><span><b>SMS Credits:</b> {{ sms_bal }} GHS</span><span><b>System:</b> Secure</span></div>
    <div class="container">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 5. ROUTES ---

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            log_action("Admin Login", "Access Granted")
            return redirect(url_for('admin_dashboard'))
        else:
            log_action("FAILED LOGIN", "Intruder Attempt")
            block_ip(request.remote_addr)
            return "<h1>SYSTEM LOCKOUT ENGAGED ❌</h1>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div style="padding:50px;">
            <h2>Personnel Security Clearance</h2>
            <form method="POST"><input type="password" name="password" placeholder="Enter System Key" required><br><button class="btn btn-blue">Authorize Access</button></form>
        </div>
    """), sms_bal="--")

@app.route("/register", methods=['GET', 'POST'])
def register():
    regions = ["Ahafo", "Ashanti", "Bono", "Bono East", "Central", "Eastern", "Greater Accra", "North East", "Northern", "Oti", "Savannah", "Upper East", "Upper West", "Volta", "Western", "Western North"]
    if request.method == 'POST':
        otp = request.form.get('otp')
        surname, firstname = request.form.get('surname').upper(), request.form.get('firstname').upper()
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            photo = cloudinary.uploader.upload(request.files['photo'])
            g_card = cloudinary.uploader.upload(request.files['gcard_photo'])
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        ghana_card=%s, photo_url=%s, status='ACTIVE', rank=%s, insurance_date=%s, expiry_date=%s,
                        region=%s, department=%s, ghana_card_photo=%s WHERE otp_code=%s""",
                        (surname, firstname, request.form.get('dob'), generate_pbe_code(firstname), generate_pbe_code(surname), 
                        request.form.get('ghana_card'), photo['secure_url'], request.form.get('rank'),
                        request.form.get('insurance'), request.form.get('expiry'), request.form.get('region'),
                        request.form.get('department'), g_card['secure_url'], otp))
            conn.commit(); cur.close(); conn.close()
            return "<h2>REGISTRATION COMPLETE ✅</h2>"
        return "<h1>INVALID CODE ❌</h1>"
    
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <h2>Employee Enrollment</h2>
        <form method="POST" enctype="multipart/form-data">
            <input type="text" name="otp" placeholder="SMS Code" required>
            <input type="text" name="surname" placeholder="Surname" required>
            <input type="text" name="firstname" placeholder="First Name" required>
            <select name="region">{''.join([f'<option value="{r}">{r}</option>' for r in regions])}</select>
            <select name="department">
                <option value="Electrical">Electrical Engineering</option>
                <option value="Civil">Civil Construction</option>
                <option value="Security">Site Security</option>
            </select>
            <input type="date" name="dob" required>
            <input type="text" name="ghana_card" placeholder="Ghana Card Number" required>
            <input type="text" name="rank" placeholder="Current Rank">
            <input type="text" name="insurance" placeholder="Insurance Date">
            <input type="text" name="expiry" placeholder="Expiry Date">
            <p>Passport Photo:</p><input type="file" name="photo" required>
            <p>Ghana Card Front:</p><input type="file" name="gcard_photo" required>
            <br><button class="btn btn-blue" type="submit">Complete Enrollment</button>
        </form>
    """), sms_bal="--")

@app.route("/admin")
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    q = request.args.get('search', '').strip()
    conn = get_db(); cur = conn.cursor()
    if q: cur.execute("SELECT * FROM pbe_master_registry WHERE surname ILIKE %s OR pbe_uid ILIKE %s ORDER BY id DESC", (f'%{q}%', f'%{q}%'))
    else: cur.execute("SELECT * FROM pbe_master_registry ORDER BY id DESC")
    workers = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div style="margin-bottom:20px; display: flex; gap: 10px; justify-content: center;">
            <form method="GET"><input name="search" placeholder="Search..." value="{{sq}}" style="width:200px;"><button class="btn btn-blue">Search</button></form>
            <a href="/admin/invite" class="btn btn-green">+ Invite</a>
            <a href="/admin/logs" class="btn btn-blue">Audit Logs</a>
            <a href="/logout" class="btn btn-red">Lock</a>
        </div>
        <table>
            <tr><th>UID</th><th>Name</th><th>Dept</th><th>Status</th><th>Actions</th></tr>
            {% for w in workers %}
            <tr><td><b>{{ w[4] or 'PENDING' }}</b></td><td>{{ w[1] }}, {{ w[2] }}</td><td>{{ w[15] }}</td>
            <td>{{ w[13] }}</td><td>
                <a href="https://wa.me/{{ w[9] }}?text=ID: {{ request.url_root }}verify/{{ w[4] }}" class="btn" style="background:#25D366;">WA</a>
                <a href="/admin/print-id/{{ w[4] }}" class="btn btn-blue">Print</a>
                <a href="/admin/delete/{{ w[0] }}" class="btn btn-red">Del</a>
            </td></tr>{% endfor %}
        </table>
    """), workers=workers, sq=q, sms_bal=get_sms_balance())

@app.route("/admin/logs")
def view_logs():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_audit_logs ORDER BY id DESC LIMIT 50")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h2>Audit Logs</h2>
        <table><tr><th>Time</th><th>Action</th><th>IP</th></tr>
        {% for l in logs %}<tr><td>{{ l[1] }}</td><td>{{ l[2] }}</td><td>{{ l[4] }}</td></tr>{% endfor %}
        </table><br><a href="/admin" class="btn btn-blue">Back</a>
    """), logs=logs, sms_bal="--")

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        phone = request.form.get('phone')
        otp = str(random.randint(100000, 999999))
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", json={"sender": ARKESEL_SENDER_ID, "message": f"PBE: Code {otp}. Register: {request.url_root}register", "recipients": [phone]}, headers={"api-key": ARKESEL_API_KEY})
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", "<h3>Invite Worker</h3><form method='POST'><input name='phone' placeholder='233...' required><br><button class='btn btn-blue'>Send SMS</button></form>"), sms_bal="--")

@app.route("/admin/print-id/<pbe_uid>")
def print_id(pbe_uid):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_master_registry WHERE pbe_uid = %s", (pbe_uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    buffer = BytesIO(); c = canvas.Canvas(buffer, pagesize=(3.375*inch, 2.125*inch))
    template = "POWER BRIDGE ENGINEERING ID CARD TEMPLATE.png"
    if os.path.exists(template): c.drawImage(template, 0, 0, width=3.375*inch, height=2.125*inch)
    if w[10]: 
        try: c.drawImage(w[10], 0.2*inch, 0.65*inch, width=0.9*inch, height=1.1*inch)
        except: pass
    c.setFont("Helvetica-Bold", 7.5); c.setFillColor(colors.black); x_col = 1.35*inch
    c.drawString(x_col, 1.6*inch, f"SURNAME: {w[1]}"); c.drawString(x_col, 1.45*inch, f"FIRSTNAME: {w[2]}")
    c.drawString(x_col, 1.25*inch, f"ID NO: {w[4]}"); c.drawString(x_col, 1.1*inch, f"LICENSE: {w[5]}")
    c.drawString(x_col, 0.95*inch, f"RANK: {w[8]}"); c.drawString(x_col, 0.8*inch, f"INSURED: {w[6]}")
    c.drawString(x_col, 0.65*inch, f"EXPIRY: {w[7]}"); c.drawString(x_col, 0.5*inch, f"DOB: {w[3]}")
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[4]}")
    bounds = qr_code.getBounds(); d = Drawing(45, 45, transform=[45./(bounds[2]-bounds[0]),0,0,45./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.8*inch, 0.15*inch); c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

@app.route("/verify/<uid>")
def verify(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT firstname, surname, rank, pbe_license, status, region, department FROM pbe_master_registry WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if w: return f"<div style='text-align:center; padding:50px;'><h1>✅ VERIFIED: {w[0]} {w[1]}</h1><p>Dept: {w[6]}</p><p>Region: {w[5]}</p></div>"
    return "<h1>❌ INVALID ID</h1>"

@app.route("/admin/delete/<int:id>")
def delete_worker(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db(); cur = conn.cursor(); cur.execute("DELETE FROM pbe_master_registry WHERE id = %s", (id,))
    conn.commit(); cur.close(); conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
