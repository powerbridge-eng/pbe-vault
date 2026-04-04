import os, random, string, re, requests, psycopg2, cloudinary, cloudinary.uploader, datetime
from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session, abort
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION & SECURE IDENTITY ---
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

# --- 2. DATABASE INITIALIZATION (Audit, Blacklist, Documents) ---
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

# --- 3. SECURITY & INTELLIGENCE ENGINE ---
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
    requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                  json={"sender": ARKESEL_SENDER_ID, "message": f"PBE VANGUARD ALERT: IP {ip} blacklisted for 3 days.", "recipients": ["233XXXXXXXXX"]}, 
                  headers={"api-key": ARKESEL_API_KEY})

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

# --- 4. THE VANGUARD INTERFACE (Clean Logo & Command Bar) ---
UI_CSS = """
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #f4f7f9; margin: 0; }
    .nav-header { background: #1a3a5a; color: white; padding: 20px; border-bottom: 6px solid #0056b3; text-align: center; }
    .floating-logo { width: 110px; filter: drop-shadow(0px 0px 0px transparent); margin-bottom: 10px; }
    .stats-strip { background: white; padding: 8px; font-size: 11px; display: flex; justify-content: center; gap: 30px; border-bottom: 1px solid #ddd; font-weight: bold; }
    .command-bar { background: #e9ecef; padding: 15px; display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-bottom: 20px; border-radius: 0 0 15px 15px; }
    .main-grid { max-width: 1300px; margin: 20px auto; background: white; padding: 25px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
    th, td { border-bottom: 1px solid #eee; padding: 12px; text-align: left; }
    th { color: #1a3a5a; text-transform: uppercase; letter-spacing: 1px; }
    .btn { padding: 8px 15px; border-radius: 6px; text-decoration: none; font-size: 12px; font-weight: bold; border: none; color: white; cursor: pointer; }
    .btn-blue { background: #0056b3; } .btn-green { background: #28a745; } .btn-red { background: #dc3545; }
    .expiry-alert { color: #dc3545; font-weight: bold; animation: blink 2s infinite; }
    @keyframes blink { 0% {opacity: 1;} 50% {opacity: 0.5;} 100% {opacity: 1;} }
    input, select { padding: 10px; border: 1px solid #ddd; border-radius: 6px; width: 100%; max-width: 350px; }
</style>
"""

BASE_HTML = f"""
<!DOCTYPE html>
<html>
<head><title>PBE Vanguard Command</title>{UI_CSS}</head>
<body>
    <div class="nav-header">
        <img src="/static/logo.png" class="floating-logo" onerror="this.src='https://via.placeholder.com/100?text=PBE+LOGO'">
        <h1 style="margin:0; font-size: 24px;">POWER BRIDGE ENGINEERING</h1>
    </div>
    <div class="stats-strip">
        <span>LIVE ARKESEL BALANCE: {{ sms_bal }}</span>
        <span>ROLE: {{ role }}</span>
        <span>SECURITY: LOCKED 🛡️</span>
    </div>
    <div class="main-grid">{% block content %}{% endblock %}</div>
</body>
</html>
"""

# --- 5. OPERATIONAL ROUTES ---

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
            log_event("INTRUSION ATTEMPT", f"Failed pwd: {pwd}")
            engage_blackout(request.remote_addr)
            return "<h1>SYSTEM BLACKOUT ENGAGED ⚠️</h1>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <div style="padding:40px;">
            <h3>Strategic Command Authorization</h3>
            <form method="POST"><input type="password" name="password" placeholder="Enter Command Key" required><br><br><button class="btn btn-blue" style="width:200px;">Unlock System</button></form>
        </div>
    """), sms_bal="--", role="GUEST")

@app.route("/register", methods=['GET', 'POST'])
def register():
    regions = ["Ahafo", "Ashanti", "Bono", "Bono East", "Central", "Eastern", "Greater Accra", "North East", "Northern", "Oti", "Savannah", "Upper East", "Upper West", "Volta", "Western", "Western North"]
    depts = ["Civil Engineering", "Electrical Systems", "Mechanical Works", "Structural Bridge", "Telecommunications", "Site Logistics", "Safety & Security"]
    if request.method == 'POST':
        otp = request.form.get('otp')
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT id FROM pbe_master_registry WHERE otp_code = %s", (otp,))
        if cur.fetchone():
            photo = cloudinary.uploader.upload(request.files['photo'])
            g_card = cloudinary.uploader.upload(request.files['gcard_photo'])
            fname = request.form.get('firstname').upper()
            sname = request.form.get('surname').upper()
            cur.execute("""UPDATE pbe_master_registry SET surname=%s, firstname=%s, dob=%s, pbe_uid=%s, pbe_license=%s,
                        ghana_card=%s, photo_url=%s, status='ACTIVE', rank=%s, insurance_date=%s, expiry_date=%s,
                        region=%s, department=%s, ghana_card_photo=%s WHERE otp_code=%s""",
                        (sname, fname, request.form.get('dob'), 
                        f"{fname}{''.join(random.choices(string.ascii_uppercase + string.digits, k=15))}"[:15],
                        f"{sname}{''.join(random.choices(string.ascii_uppercase + string.digits, k=15))}"[:15],
                        request.form.get('ghana_card'), photo['secure_url'], request.form.get('rank'),
                        request.form.get('insurance'), request.form.get('expiry'), request.form.get('region'),
                        request.form.get('department'), g_card['secure_url'], otp))
            conn.commit(); cur.close(); conn.close()
            return "<h2>ENROLLMENT COMPLETE ✅</h2>"
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", f"""
        <h3>Personnel Identity Enrollment</h3>
        <form method="POST" enctype="multipart/form-data">
            <input type="text" name="otp" placeholder="Enter SMS OTP Code" required>
            <input type="text" name="surname" placeholder="Surname" required>
            <input type="text" name="firstname" placeholder="First Name" required>
            <label>Ghanaian Region</label><select name="region">{''.join([f'<option value="{r}">{r}</option>' for r in regions])}</select>
            <label>Engineering Department</label><select name="department">{''.join([f'<option value="{d}">{d}</option>' for d in depts])}</select>
            <input type="text" name="ghana_card" placeholder="Ghana Card ID Number" required>
            <input type="text" name="rank" placeholder="Current Role / Rank" required>
            <input type="date" name="dob" required>
            <input type="text" name="insurance" placeholder="Insurance Date (DD/MM/YYYY)">
            <input type="text" name="expiry" placeholder="Expiry Date (DD/MM/YYYY)">
            <p>Upload Passport Photo:</p><input type="file" name="photo" required>
            <p>Upload Ghana Card (Front):</p><input type="file" name="gcard_photo" required>
            <br><br><button class="btn btn-blue">Authorize My Identity</button>
        </form>
    """), sms_bal="HIDDEN", role="ENROLLING")

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
            <form method="GET" style="display:flex; gap:5px;">
                <input name="search" placeholder="Search Name, ID, Region, Dept..." value="{{sq}}" style="width:250px;">
                <button class="btn btn-blue">Execute Search</button>
            </form>
            <a href="/admin/invite" class="btn btn-green">+ Invite Worker</a>
            <a href="/admin/audit-logs" class="btn btn-blue" style="background:#6c757d;">Security Logs</a>
            <a href="/logout" class="btn btn-red">Lock Console</a>
        </div>
        <table>
            <tr><th>UID</th><th>Worker</th><th>Dept / Region</th><th>Communication</th><th>Actions</th></tr>
            {% for w in workers %}
            <tr>
                <td><b>{{ w[4] or 'PENDING' }}</b></td>
                <td>{{ w[1] }}, {{ w[2] }}<br><small>{{ w[8] }}</small></td>
                <td>{{ w[15] }}<br><small>{{ w[14] }}</small></td>
                <td>
                    <a href="https://wa.me/{{ w[9] }}?text=PBE COMMAND: Your ID is ready {{ request.url_root }}verify/{{ w[4] }}" class="btn" style="background:#25D366;" target="_blank">WA</a>
                    <a href="mailto:{{ admin_mail }}?subject=PBE Profile: {{ w[4] }}" class="btn" style="background:#EA4335;">Email</a>
                </td>
                <td>
                    {% if w[4] %}<a href="/admin/print-id/{{ w[4] }}" class="btn btn-blue">Print</a>{% endif %}
                    {% if role == 'GENERAL' %}<a href="/admin/delete/{{ w[0] }}" class="btn btn-red">Delete</a>{% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    """), workers=workers, sq=search, sms_bal=get_live_balance(), role=session['role'], admin_mail=ADMIN_EMAIL)

@app.route("/admin/audit-logs")
def view_audit():
    if session.get('role') != 'GENERAL': return "UNAUTHORIZED", 403
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT * FROM pbe_audit_logs ORDER BY id DESC LIMIT 100")
    logs = cur.fetchall(); cur.close(); conn.close()
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", """
        <h3>System Audit Trail</h3>
        <table style="font-size: 10px;">
            <tr><th>Time</th><th>Action</th><th>Details</th><th>IP / Role</th></tr>
            {% for l in logs %}<tr><td>{{ l[1] }}</td><td><b>{{ l[2] }}</b></td><td>{{ l[3] }}</td><td>{{ l[4] }} [{{ l[5] }}]</td></tr>{% endfor %}
        </table>
        <br><a href="/admin-dashboard" class="btn btn-blue">Return</a>
    """), logs=logs, sms_bal="--", role="GENERAL")

@app.route("/admin/invite", methods=['GET', 'POST'])
def invite():
    if not session.get('logged_in'): return redirect(url_for('login'))
    if request.method == 'POST':
        phone, otp = request.form.get('phone'), str(random.randint(100000, 999999))
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO pbe_master_registry (phone_no, otp_code) VALUES (%s, %s)", (phone, otp))
        conn.commit(); cur.close(); conn.close()
        requests.post("https://sms.arkesel.com/api/v2/sms/send", 
                      json={"sender": ARKESEL_SENDER_ID, "message": f"PBE: Use code {otp} to enroll at {request.url_root}register", "recipients": [phone]}, 
                      headers={"api-key": ARKESEL_API_KEY})
        log_event("Invite Sent", f"To: {phone}")
        return redirect(url_for('admin_dashboard'))
    return render_template_string(BASE_HTML.replace("{% block content %}{% endblock %}", "<h3>Invite Personnel</h3><form method='POST'><input name='phone' placeholder='233XXXXXXXXX' required><br><br><button class='btn btn-blue'>Send Secret OTP</button></form>"), sms_bal="--", role=session['role'])

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
    c.drawString(x_col, 0.95*inch, f"RANK: {w[8]}"); c.drawString(x_col, 0.8*inch, f"INSURED: {w[6]}"); c.drawString(x_col, 0.65*inch, f"EXPIRY: {w[7]}")
    qr_code = qr.QrCodeWidget(f"{request.url_root}verify/{w[4]}")
    bounds = qr_code.getBounds(); d = Drawing(45, 45, transform=[45./(bounds[2]-bounds[0]),0,0,45./(bounds[3]-bounds[1]),0,0])
    d.add(qr_code); d.drawOn(c, 2.8*inch, 0.15*inch); c.showPage(); c.save(); buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf')

@app.route("/verify/<uid>")
def verify(uid):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT firstname, surname, department, status, photo_url FROM pbe_master_registry WHERE pbe_uid = %s", (uid,))
    w = cur.fetchone(); cur.close(); conn.close()
    if w: return f"<div style='text-align:center; padding:50px; font-family:sans-serif;'><h1 style='color:green;'>✅ VERIFIED PBE EMPLOYEE</h1><img src='{w[4]}' width='150'><p><b>Name:</b> {w[0]} {w[1]}</p><p><b>Dept:</b> {w[2]}</p></div>"
    return "<h1>❌ INVALID ID</h1>"

@app.route("/logout")
def logout():
    log_event("Logout", "Session Terminated")
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
